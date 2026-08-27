import json
from pathlib import Path

from core.config import CHUNK_OVERLAP, CHUNK_SIZE
from core.utils import chunk_text, truncate
from db.database import Database
from db.embeddings import get_embedding

SUPPORTED_EXTS = {'.txt', '.md', '.py', '.js', '.json', '.csv', '.pdf', '.docx', '.doc'}


def extract_text_from_file(filepath: str) -> str:
    p = Path(filepath)
    suffix = p.suffix.lower()
    if suffix in ('.txt', '.md', '.py', '.js', '.json', '.csv'):
        return p.read_text(encoding='utf-8', errors='ignore')
    if suffix == '.pdf':
        try:
            import fitz
            doc = fitz.open(str(p))
            return '\n'.join(page.get_text() for page in doc)
        except Exception:
            return ''
    if suffix in ('.docx', '.doc'):
        try:
            import docx
            doc = docx.Document(str(p))
            return '\n'.join(para.text for para in doc.paragraphs)
        except Exception:
            return ''
    return ''


def preview_file_content(filepath: str, max_chars: int = 4000) -> str:
    text = extract_text_from_file(filepath)
    if not text:
        return 'تعذر استخراج معاينة من هذا الملف أو أن الملف فارغ.'
    return truncate(text, max_chars)


def ingest_file(filepath: str, db=None) -> int:
    db = db or Database()
    text = extract_text_from_file(filepath)
    if not text:
        return 0
    chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
    source = Path(filepath).name
    for i, chunk in enumerate(chunks):
        emb = get_embedding(chunk)
        db.add_knowledge_chunk(source, i, chunk, json.dumps(emb) if emb else '')
    return len(chunks)


def ingest_directory(dirpath: str) -> int:
    p = Path(dirpath)
    if not p.exists():
        return 0
    total = 0
    for f in p.rglob('*'):
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS:
            total += ingest_file(str(f))
    return total
