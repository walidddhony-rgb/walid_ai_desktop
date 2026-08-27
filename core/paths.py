from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
VOICES_DIR = BASE_DIR / "voices"
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
LEGACY_DIR = BASE_DIR / "legacy"

for path in (DATA_DIR, UPLOADS_DIR, VOICES_DIR, KNOWLEDGE_DIR, LEGACY_DIR):
    path.mkdir(parents=True, exist_ok=True)
