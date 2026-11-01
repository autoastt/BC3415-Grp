from __future__ import annotations

import hmac
import re
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Iterator, Literal, Optional

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from . import db, links, log_crypto, rag, settings_store
from .config import config
from .ingestion import ALLOWED_EXTENSIONS, IngestionError, extract_file
from .rate_limit import RateLimiter
from .scraper import scrape

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    yield


app = FastAPI(title=config.app_name, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.cors_origins, allow_methods=["*"],
                   allow_headers=["*"])
chat_limiter = RateLimiter(config.rate_limit_per_minute, 60)


@app.exception_handler(IngestionError)
async def _ingestion_error(_: Request, exc: IngestionError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# ---------- helpers ----------

def client_ip(request: Request) -> str:
    if config.trust_proxy:
        real = request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for", "").split(",")[0]
        if real.strip():
            return real.strip()
    return request.client.host if request.client else "unknown"


def require_admin(x_admin_token: Optional[str] = Header(default=None)) -> None:
    """Knowledge-base and settings writes are admin-only when ADMIN_TOKEN is set.
    Otherwise any visitor could inject documents the bot will repeat as fact."""
    if not config.admin_token:
        return
    if not x_admin_token or not hmac.compare_digest(x_admin_token, config.admin_token):
        raise HTTPException(status_code=401, detail="Admin token required.")


# ---------- models ----------

class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=config.max_message_chars)
    history: list[HistoryItem] = Field(default_factory=list, max_length=20)


class TextSource(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=2_000_000)


class UrlSource(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


def _check_url(url: str) -> str:
    url = url.strip()
    if not links.is_safe_url(url):
        raise ValueError("Links must start with https://, http:// or / (a page on this site).")
    return url


class QuickLink(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    url: str = Field(min_length=1, max_length=500)
    keywords: list[str] = Field(min_length=1, max_length=30)

    @field_validator("url")
    @classmethod
    def _check_link_url(cls, v: str) -> str:
        return _check_url(v)

    @field_validator("keywords")
    @classmethod
    def _clean_keywords(cls, v: list[str]) -> list[str]:
        words = [k.strip().lower()[:40] for k in v if k and k.strip()]
        if not words:
            raise ValueError("Each link needs at least one keyword.")
        return list(dict.fromkeys(words))


class SettingsModel(BaseModel):
    company_name: str = Field(min_length=1, max_length=120)
    bot_name: str = Field(min_length=1, max_length=60)
    allowed_topics: list[str] = Field(min_length=1, max_length=40)
    support_contact: str = Field(min_length=3, max_length=200)
    refusal_message: str = Field(min_length=5, max_length=600)
    relevance_threshold: float = Field(ge=0.0, le=1.0)
    # Optional so a client that doesn't send them keeps the saved links (None = unchanged)
    order_url: Optional[str] = Field(default=None, max_length=500)
    quick_links: Optional[list[QuickLink]] = Field(default=None, max_length=20)

    @field_validator("allowed_topics")
    @classmethod
    def _clean_topics(cls, v: list[str]) -> list[str]:
        topics = [t.strip()[:60] for t in v if t and t.strip()]
        if not topics:
            raise ValueError("Add at least one topic.")
        return list(dict.fromkeys(topics))

    @field_validator("order_url")
    @classmethod
    def _check_order_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _check_url(v) if v.strip() else ""  # empty turns the order link off


# ---------- chat ----------

def _ndjson(events: Iterator[dict]) -> Iterator[bytes]:
    for e in events:
        yield (json.dumps(e, ensure_ascii=False) + "\n").encode("utf-8")


@app.post("/api/chat")
def chat(body: ChatRequest, request: Request):
    ip = client_ip(request)
    allowed, retry = chat_limiter.check(ip)
    if not allowed:
        return JSONResponse(status_code=429, headers={"Retry-After": str(retry)},
                            content={"detail": f"Too many messages. Try again in {retry} seconds."})
    events = rag.handle_chat(body.message, [h.model_dump() for h in body.history], ip)
    return StreamingResponse(_ndjson(events), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------- sources ----------

@app.get("/api/sources", dependencies=[Depends(require_admin)])
def list_sources():
    return db.list_sources()


@app.post("/api/sources/text", dependencies=[Depends(require_admin)])
def add_text(body: TextSource):
    return rag.ingest(body.title.strip(), "text", body.content, origin=None)


@app.post("/api/sources/file", dependencies=[Depends(require_admin)])
def add_file(file: UploadFile = File(...)):
    name = Path(file.filename or "").name
    if Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise IngestionError("Unsupported file type. Use PDF, DOCX, TXT, MD or CSV.")
    data = bytearray()
    while chunk := file.file.read(1024 * 1024):  # stream so a huge upload can't fill memory
        data.extend(chunk)
        if len(data) > config.max_upload_bytes:
            raise HTTPException(status_code=413, detail=f"Files must be {config.max_upload_mb} MB or smaller.")
    if not data:
        raise IngestionError("The file is empty.")
    text, type_ = extract_file(name, bytes(data))
    title = re.sub(r"[_-]+", " ", Path(name).stem).strip() or name
    return rag.ingest(title[:200], type_, text, origin=name)


@app.post("/api/sources/url", dependencies=[Depends(require_admin)])
def add_url(body: UrlSource):
    final_url, title, text = scrape(body.url)
    return rag.ingest(title[:200], "url", text, origin=final_url)


@app.delete("/api/sources/{source_id}", dependencies=[Depends(require_admin)])
def delete_source(source_id: str):
    if not rag.delete(source_id):
        raise HTTPException(status_code=404, detail="Source not found.")
    return {"deleted": source_id}


# ---------- settings, logs, meta ----------

@app.get("/api/settings")
def get_settings():
    return settings_store.get()


@app.put("/api/settings", dependencies=[Depends(require_admin)])
def put_settings(body: SettingsModel):
    return settings_store.update(body.model_dump(exclude_none=True))


@app.get("/api/logs", dependencies=[Depends(require_admin)])
def get_logs(limit: int = Query(100, ge=1, le=1000),
             classification: Optional[str] = Query(None, max_length=30)):
    return {"summary": db.log_summary(), "items": db.list_logs(limit, classification),
            "encryption": {"key_source": log_crypto.key_source()}}


@app.get("/api/meta")
def meta():
    return {"app_name": config.app_name, "admin_required": bool(config.admin_token),
            "max_upload_mb": config.max_upload_mb, "max_message_chars": config.max_message_chars}


@app.get("/api/health")
def health():
    return {"status": "ok"}
