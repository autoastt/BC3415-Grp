"""Text extraction, cleaning and token-based chunking."""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

ALLOWED_EXTENSIONS = {".pdf": "pdf", ".docx": "docx", ".txt": "txt", ".md": "md", ".csv": "csv"}


class IngestionError(ValueError):
    """Raised for user-fixable problems (bad file, empty text...). Mapped to HTTP 400."""


# ---------- extraction ----------

def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def _check_magic(ext: str, data: bytes) -> None:
    """Don't trust the extension alone: verify the file really is what it claims."""
    if ext == ".pdf" and not data.startswith(b"%PDF"):
        raise IngestionError("This file has a .pdf name but isn't a valid PDF.")
    if ext == ".docx" and not data.startswith(b"PK\x03\x04"):
        raise IngestionError("This file has a .docx name but isn't a valid Word document.")
    if ext in {".txt", ".md", ".csv"} and b"\x00" in data[:8192] and not data.startswith((b"\xff\xfe", b"\xfe\xff")):
        raise IngestionError("This file looks binary, not text.")


def extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise IngestionError("Password-protected PDFs aren't supported.")
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)
    except IngestionError:
        raise
    except Exception as e:  # pypdf raises many types
        raise IngestionError(f"Couldn't read this PDF ({type(e).__name__}).") from e


def extract_docx(data: bytes) -> str:
    import docx
    try:
        d = docx.Document(io.BytesIO(data))
    except Exception as e:
        raise IngestionError("Couldn't read this Word document.") from e
    parts = [p.text for p in d.paragraphs]
    for table in d.tables:  # menus and price lists often live in tables
        for row in table.rows:
            parts.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n".join(parts)


def extract_csv(data: bytes) -> str:
    """Turn each row into a self-describing line ("Item: Classic; Price: 8.90")
    so a chunk still makes sense when retrieved without its header row."""
    text = _decode(data)
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    lines = []
    for row in reader:
        pairs = [f"{(k or '').strip()}: {(v or '').strip()}" for k, v in row.items() if k and (v or "").strip()]
        if pairs:
            lines.append("; ".join(pairs))
    return "\n".join(lines)


def extract_file(filename: str, data: bytes) -> tuple[str, str]:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise IngestionError(f"Unsupported file type '{ext or 'none'}'. Use PDF, DOCX, TXT, MD or CSV.")
    _check_magic(ext, data)
    if ext == ".pdf":
        text = extract_pdf(data)
    elif ext == ".docx":
        text = extract_docx(data)
    elif ext == ".csv":
        text = extract_csv(data)
    else:
        text = _decode(data)
    return text, ALLOWED_EXTENSIONS[ext]


# ---------- cleaning ----------

_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = _ZERO_WIDTH.sub("", text)  # hidden characters are a common injection trick
    text = _CONTROL.sub(" ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------- chunking ----------

class _Tokenizer:
    def __init__(self) -> None:
        try:
            import tiktoken
            self._enc = tiktoken.get_encoding("cl100k_base")
        except Exception:
            # Offline fallback: ~1 token per word-ish piece. Close enough for chunk sizing.
            self._enc = None

    def encode(self, text: str) -> list:
        if self._enc:
            return self._enc.encode(text)
        return re.findall(r"\S+\s*", text)

    def decode(self, tokens: list) -> str:
        if self._enc:
            return self._enc.decode(tokens)
        return "".join(tokens)


@lru_cache(maxsize=1)
def tokenizer() -> _Tokenizer:
    return _Tokenizer()


def chunk_text(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    """Paragraph-aware chunking: pack whole paragraphs up to `size` tokens, carry the
    last `overlap` tokens into the next chunk, and hard-split paragraphs that are
    themselves longer than `size`."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    tok = tokenizer()
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[str] = []
    current: list = []

    def flush() -> list:
        if current:
            chunk = tok.decode(current).strip()
            if chunk:
                chunks.append(chunk)
            return current[-overlap:] if overlap else []
        return []

    for para in paragraphs:
        ptoks = tok.encode(para + "\n\n")
        if len(ptoks) > size:  # oversized paragraph: sliding window
            carry = flush()
            current = list(carry)
            step = size - overlap
            for start in range(0, len(ptoks), step):
                window = ptoks[start:start + size]
                current = window
                carry = flush()
                if start + size >= len(ptoks):
                    break
            current = list(carry)
            continue
        if len(current) + len(ptoks) > size:
            current = flush()
        current = current + ptoks
    # Last chunk: only emit if it adds content beyond the overlap tail
    if current and (not chunks or len(current) > overlap):
        flush()
    return chunks
