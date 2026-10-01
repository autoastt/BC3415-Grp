"""The chat pipeline and the ingestion service.

Chat order (cheapest first, so most junk never costs a generation call):
  1. Regex guard        free      prompt-injection / human-handoff phrases
  2. Scope classifier   ~tiny     IN_SCOPE / OUT_OF_SCOPE / GREETING / HUMAN_HANDOFF
  3. Retrieval          embedding top-k chunks
  4. Relevance gate     free      below threshold -> fallback, no LLM
  5. Generation         Claude    streamed, with output leak check
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Iterator

from . import db, guard, llm, settings_store
from .config import config
from .ingestion import IngestionError, chunk_text, clean_text
from .vectorstore import get_store

log = logging.getLogger("rag")

FALLBACK_SIGNATURE = "i don't have that information right now"


def _canned(text: str, classification: str, *, handoff: bool = False) -> Iterator[dict]:
    yield {"type": "token", "text": text}
    yield {"type": "done", "classification": classification, "sources": [], "handoff": handoff}


def _retrieval_query(message: str, history: list[dict[str, str]]) -> str:
    """Short follow-ups ("how much is it?") embed poorly alone, so prepend the
    previous user turn to give retrieval the subject of the conversation."""
    prev = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
    if prev and len(message.split()) < 12:
        return f"{prev[:300]}\n{message}"
    return message


def _source_payload(hits: list[dict]) -> list[dict]:
    return [{"source_id": h["source_id"], "title": h["title"], "type": h["type"],
             "chunk_index": h["chunk_index"], "score": h["score"],
             "snippet": h["text"][:320] + ("…" if len(h["text"]) > 320 else "")} for h in hits]


def handle_chat(message: str, history: list[dict[str, Any]], client_id: str | None) -> Iterator[dict]:
    s = settings_store.get()
    refusal = settings_store.refusal_message(s)
    fallback = settings_store.fallback_message(s)
    msg = guard.normalize(message)
    hist = llm.normalize_history(history[-config.history_messages:])

    def record(classification: str, reason: str | None = None, score: float | None = None) -> None:
        try:
            db.log_question(msg, classification, reason, score, client_id)
        except Exception:
            log.exception("failed to log question")

    # 1. Free deterministic checks
    if guard.looks_like_injection(msg):
        record("out_of_scope", "injection_pattern")
        yield from _canned(refusal, "out_of_scope")
        return
    if guard.wants_human(msg):
        record("handoff", "explicit_request")
        yield from _canned(_handoff_text(s), "handoff", handoff=True)
        return

    # 2. Scope classifier (fails closed)
    try:
        label = llm.classify(msg, hist, s["company_name"], s["allowed_topics"])
    except Exception:
        log.exception("classifier failed")
        record("error", "classifier_failed")
        yield {"type": "error", "message": "The assistant is temporarily unavailable. Please try again in a moment."}
        return

    if label == "OUT_OF_SCOPE":
        record("out_of_scope", "classifier")
        yield from _canned(refusal, "out_of_scope")
        return
    if label == "GREETING":
        record("greeting", "classifier")
        topics = ", ".join(s["allowed_topics"][:4])
        yield from _canned(f"Hi! I'm {s['bot_name']}, {s['company_name']}'s assistant. "
                           f"I can help with things like {topics}. What would you like to know?", "greeting")
        return
    if label == "HUMAN_HANDOFF":
        record("handoff", "classifier")
        yield from _canned(_handoff_text(s), "handoff", handoff=True)
        return

    # 3. Retrieval
    try:
        hits = get_store().query(_retrieval_query(msg, hist), config.top_k)
    except Exception:
        log.exception("retrieval failed")
        record("error", "retrieval_failed")
        yield {"type": "error", "message": "Search is temporarily unavailable. Please try again shortly."}
        return

    threshold = float(s.get("relevance_threshold", config.default_relevance_threshold))
    top = hits[0]["score"] if hits else 0.0

    # 4. Relevance gate: no LLM call when nothing relevant exists
    if top < threshold:
        record("no_answer", "below_threshold", top)
        yield from _canned(fallback, "no_answer", handoff=True)
        return
    relevant = [h for h in hits if h["score"] >= threshold]

    # 5. Generation
    system_prompt = build_system(s, relevant, refusal)
    answer = ""
    try:
        for piece in llm.stream_answer(system_prompt, hist, msg):
            answer += piece
            if guard.leaks_prompt(answer):
                record("out_of_scope", "output_leak_blocked", top)
                yield {"type": "replace", "text": refusal}
                yield {"type": "done", "classification": "out_of_scope", "sources": [], "handoff": False}
                return
            yield {"type": "token", "text": piece}
    except Exception:
        log.exception("generation failed")
        record("error", "generation_failed", top)
        yield {"type": "error", "message": "Something went wrong while answering. Please try again."}
        return

    lowered = answer.lower()
    if FALLBACK_SIGNATURE in lowered:  # model judged the retrieved text insufficient
        record("no_answer", "model_fallback", top)
        yield {"type": "done", "classification": "no_answer", "sources": [], "handoff": True}
    elif refusal.lower()[:60] in lowered:
        record("out_of_scope", "model_refusal", top)
        yield {"type": "done", "classification": "out_of_scope", "sources": [], "handoff": False}
    else:
        record("in_scope", None, top)
        yield {"type": "done", "classification": "in_scope", "sources": _source_payload(relevant), "handoff": False}


def build_system(s: dict, hits: list[dict], refusal: str) -> str:
    from .prompts import build_system_prompt
    return build_system_prompt(s, hits, refusal)


def _handoff_text(s: dict) -> str:
    return (f"I'll get you to a member of our team. You can reach {s['company_name']} support at "
            f"{s['support_contact']}. If it's easier, share your order number and what happened, "
            f"and they'll pick it up from there.")


# ---------- ingestion service ----------

def ingest(title: str, type_: str, raw_text: str, origin: str | None = None) -> dict:
    text = clean_text(raw_text)
    if len(text) < 20:
        raise IngestionError("No usable text was found in this source.")
    chunks = chunk_text(text, config.chunk_tokens, config.chunk_overlap)
    if not chunks:
        raise IngestionError("No usable text was found in this source.")
    source_id = uuid.uuid4().hex
    store = get_store()
    store.add(source_id, title, type_, chunks)
    try:
        return db.insert_source(source_id, title, type_, origin, len(chunks))
    except Exception:
        store.delete_source(source_id)  # keep Chroma and SQLite consistent
        raise


def delete(source_id: str) -> bool:
    if not db.get_source(source_id):
        return False
    get_store().delete_source(source_id)
    db.delete_source(source_id)
    return True
