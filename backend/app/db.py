"""SQLite for source metadata and the question log. Chunks live in ChromaDB.
Questions in the log are encrypted and client IPs hashed (see log_crypto.py)."""
from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from . import log_crypto
from .config import config

log = logging.getLogger("db")
_DB = config.data_dir / "app.db"


@contextmanager
def conn() -> Iterator[sqlite3.Connection]:
    c = sqlite3.connect(_DB, timeout=10)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init() -> None:
    with conn() as c:
        c.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                type TEXT NOT NULL,
                origin TEXT,
                chunk_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS question_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                question TEXT NOT NULL,
                classification TEXT NOT NULL,
                reason TEXT,
                top_score REAL,
                client TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_log_class ON question_log(classification);
            """
        )
    log_crypto.check()
    _encrypt_plaintext_rows()


def _encrypt_plaintext_rows() -> None:
    """Rows logged before encryption was added are encrypted in place at startup."""
    prefix = log_crypto.PREFIX
    with conn() as c:
        rows = c.execute("SELECT id, question, client FROM question_log WHERE substr(question, 1, ?) != ?",
                         (len(prefix), prefix)).fetchall()
        for r in rows:
            c.execute("UPDATE question_log SET question=?, client=? WHERE id=?",
                      (log_crypto.encrypt(r["question"]), log_crypto.pseudonymize(r["client"]), r["id"]))
    if rows:
        log.info("Encrypted %d question log row(s) written before log encryption was enabled.", len(rows))


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def insert_source(source_id: str, title: str, type_: str, origin: str | None, chunk_count: int) -> dict:
    row = {"id": source_id, "title": title, "type": type_, "origin": origin,
           "chunk_count": chunk_count, "created_at": now()}
    with conn() as c:
        c.execute(
            "INSERT INTO sources (id,title,type,origin,chunk_count,created_at) "
            "VALUES (:id,:title,:type,:origin,:chunk_count,:created_at)", row)
    return row


def list_sources() -> list[dict]:
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM sources ORDER BY created_at DESC")]


def get_source(source_id: str) -> dict | None:
    with conn() as c:
        r = c.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
        return dict(r) if r else None


def delete_source(source_id: str) -> None:
    with conn() as c:
        c.execute("DELETE FROM sources WHERE id=?", (source_id,))


def log_question(question: str, classification: str, reason: str | None,
                 top_score: float | None, client: str | None) -> None:
    with conn() as c:
        c.execute(
            "INSERT INTO question_log (ts,question,classification,reason,top_score,client) "
            "VALUES (?,?,?,?,?,?)",
            (now(), log_crypto.encrypt(question[:2000]), classification, reason, top_score,
             log_crypto.pseudonymize(client)))


def list_logs(limit: int = 100, classification: str | None = None) -> list[dict]:
    """Decrypts questions for the admin view (the endpoint is admin-only)."""
    q = "SELECT * FROM question_log"
    args: list = []
    if classification:
        q += " WHERE classification=?"
        args.append(classification)
    q += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with conn() as c:
        rows = [dict(r) for r in c.execute(q, args)]
    for r in rows:
        r["question"] = log_crypto.decrypt(r["question"])
    return rows


def log_summary() -> dict[str, int]:
    with conn() as c:
        return {r["classification"]: r["n"] for r in
                c.execute("SELECT classification, COUNT(*) n FROM question_log GROUP BY classification")}
