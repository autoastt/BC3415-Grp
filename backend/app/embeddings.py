"""Pluggable embedders. The collection name includes the model, because vectors
from different models are not comparable."""
from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache
from typing import Protocol

from .config import config


class Embedder(Protocol):
    name: str
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbedder:
    def __init__(self) -> None:
        from openai import OpenAI
        if not config.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set (or set EMBEDDING_PROVIDER=local).")
        self._client = OpenAI(api_key=config.openai_api_key)
        self.name = config.openai_embedding_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), 96):
            resp = self._client.embeddings.create(model=self.name, input=texts[i:i + 96])
            out.extend(d.embedding for d in resp.data)
        return out


class LocalEmbedder:
    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer
        self.name = config.local_embedding_model
        self._model = SentenceTransformer(self.name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True, batch_size=32).tolist()


class FakeEmbedder:
    """Deterministic hashed bag-of-words. No network, no model download.
    Good enough for automated tests; NOT for production."""
    name = "fake-hash-256"
    _dim = 256

    def embed(self, texts: list[str]) -> list[list[float]]:
        vecs = []
        for t in texts:
            v = [0.0] * self._dim
            for w in re.findall(r"[a-z0-9]+", t.lower()):
                if len(w) < 3:
                    continue
                h = int(hashlib.md5(w.encode()).hexdigest(), 16)
                v[h % self._dim] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            vecs.append([x / n for x in v])
        return vecs


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    provider = config.embedding_provider
    if provider == "openai":
        return OpenAIEmbedder()
    if provider == "local":
        return LocalEmbedder()
    if provider == "fake":
        return FakeEmbedder()
    raise RuntimeError(f"Unknown EMBEDDING_PROVIDER '{provider}'")
