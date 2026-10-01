"""Load the sample Blaze Burger knowledge base. Usage: python -m scripts.seed [--reset]"""
from __future__ import annotations

import sys
from pathlib import Path

from app import db, rag
from app.ingestion import extract_file

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample_data"
if not SAMPLE_DIR.exists():
    SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample_data"


def main() -> None:
    db.init()
    existing = {s["origin"]: s for s in db.list_sources()}
    reset = "--reset" in sys.argv
    for path in sorted(SAMPLE_DIR.iterdir()):
        if path.suffix.lower() not in {".md", ".txt", ".csv", ".pdf", ".docx"}:
            continue
        if path.name in existing:
            if not reset:
                print(f"skip  {path.name} (already loaded)")
                continue
            rag.delete(existing[path.name]["id"])
        text, type_ = extract_file(path.name, path.read_bytes())
        row = rag.ingest(path.stem.replace("_", " ").title(), type_, text, origin=path.name)
        print(f"added {path.name}: {row['chunk_count']} chunk(s)")


if __name__ == "__main__":
    main()
