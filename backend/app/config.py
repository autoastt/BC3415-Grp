"""Environment-level configuration. Secrets come from .env, never from code."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "ScopeGuard"))

    # LLMs
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    anthropic_model: str = field(default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"))
    classifier_model: str = field(
        default_factory=lambda: os.getenv("CLASSIFIER_MODEL", "claude-haiku-4-5-20251001")
    )
    max_answer_tokens: int = field(default_factory=lambda: int(os.getenv("MAX_ANSWER_TOKENS", "600")))

    # Embeddings: "openai" | "local" | "fake" (fake = deterministic hashing, for tests only)
    embedding_provider: str = field(default_factory=lambda: os.getenv("EMBEDDING_PROVIDER", "openai").lower())
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_embedding_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    )
    local_embedding_model: str = field(
        default_factory=lambda: os.getenv("LOCAL_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    )

    # Storage
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", "./data")).resolve())

    # RAG
    default_relevance_threshold: float = field(
        default_factory=lambda: float(os.getenv("RELEVANCE_THRESHOLD", "0.35"))
    )
    top_k: int = field(default_factory=lambda: int(os.getenv("TOP_K", "5")))
    chunk_tokens: int = field(default_factory=lambda: int(os.getenv("CHUNK_TOKENS", "500")))
    chunk_overlap: int = field(default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "50")))
    history_messages: int = field(default_factory=lambda: int(os.getenv("HISTORY_MESSAGES", "6")))

    # Limits & security
    max_upload_mb: int = field(default_factory=lambda: int(os.getenv("MAX_UPLOAD_MB", "20")))
    max_scrape_mb: int = field(default_factory=lambda: int(os.getenv("MAX_SCRAPE_MB", "5")))
    max_message_chars: int = field(default_factory=lambda: int(os.getenv("MAX_MESSAGE_CHARS", "1000")))
    rate_limit_per_minute: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "20")))
    admin_token: str = field(default_factory=lambda: os.getenv("ADMIN_TOKEN", ""))
    trust_proxy: bool = field(default_factory=lambda: _bool("TRUST_PROXY", False))
    allow_private_urls: bool = field(default_factory=lambda: _bool("ALLOW_PRIVATE_URLS", False))
    cors_origins: list[str] = field(
        default_factory=lambda: [
            o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()
        ]
    )

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


config = Config()
config.data_dir.mkdir(parents=True, exist_ok=True)
