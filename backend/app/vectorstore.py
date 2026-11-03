"""ChromaDB wrapper. Uses cosine space so score = 1 - distance = cosine similarity."""
from __future__ import annotations

import logging
import os
import re
from functools import lru_cache

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)

from .config import config
from .embeddings import Embedder, get_embedder


class VectorStore:
    def __init__(self, embedder: Embedder) -> None:
        import chromadb
        from chromadb.config import Settings

        self.embedder = embedder
        self._client = chromadb.PersistentClient(
            path=str(config.data_dir / "chroma"), settings=Settings(anonymized_telemetry=False)
        )
        slug = re.sub(r"[^a-zA-Z0-9_-]", "_", embedder.name)[-50:]
        self._col = self._client.get_or_create_collection(
            name=f"kb_{slug}", metadata={"hnsw:space": "cosine", "embedding_model": embedder.name}
        )

    def add(self, source_id: str, title: str, type_: str, chunks: list[str],
            vectors: list | None = None) -> None:
        if vectors is None:
            vectors = self.embedder.embed(chunks)
        ids = [f"{source_id}:{i}" for i in range(len(chunks))]
        metas = [{"source_id": source_id, "title": title, "type": type_, "chunk_index": i}
                 for i in range(len(chunks))]
        for i in range(0, len(chunks), 500):
            self._col.add(ids=ids[i:i + 500], embeddings=vectors[i:i + 500],
                          documents=chunks[i:i + 500], metadatas=metas[i:i + 500])

    def replace(self, source_id: str, title: str, type_: str, chunks: list[str]) -> None:
        """Swap a source's chunks. Embedding runs first, so if it fails the old chunks stay."""
        vectors = self.embedder.embed(chunks)
        self.delete_source(source_id)
        self.add(source_id, title, type_, chunks, vectors)

    def delete_source(self, source_id: str) -> None:
        self._col.delete(where={"source_id": source_id})

    def count(self) -> int:
        return self._col.count()

    def query(self, text: str, k: int) -> list[dict]:
        if self._col.count() == 0:
            return []
        [vec] = self.embedder.embed([text])
        res = self._col.query(query_embeddings=[vec], n_results=min(k, self._col.count()),
                              include=["documents", "metadatas", "distances"])
        hits = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            hits.append({**meta, "text": doc, "score": round(1.0 - float(dist), 4)})
        return sorted(hits, key=lambda h: h["score"], reverse=True)


@lru_cache(maxsize=1)
def get_store() -> VectorStore:
    return VectorStore(get_embedder())
