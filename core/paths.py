"""Centralised path constants."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
VOICES_DIR = BASE_DIR / "voices"
LEGACY_DIR = BASE_DIR / "legacy"

for _d in (DATA_DIR, UPLOADS_DIR, VOICES_DIR, LEGACY_DIR):
    _d.mkdir(parents=True, exist_ok=True)
