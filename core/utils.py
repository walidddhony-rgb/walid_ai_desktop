from pathlib import Path
import re
import uuid


def safe_filename(name: str) -> str:
    name = re.sub(r'[^\w\-\.\u0600-\u06FF ]+', '_', name).strip()
    return name or uuid.uuid4().hex


def truncate(text, n=12000):
    text = text or ""
    return text if len(text) <= n else text[:n] + "\n...[مقتطع]"


def sanitize_path(path_str: str) -> Path:
    return Path(path_str).resolve()


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list:
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
        if start < 0:
            start = 0
        if end >= len(text):
            break
    return chunks
