import json
import os
from pathlib import Path
from core.paths import DATA_DIR

DB_PATH = Path(os.getenv("WALID_DB_PATH", str(DATA_DIR / "walid_ai.db")))
CONFIG_PATH = Path(os.getenv("WALID_CONFIG_PATH", str(DATA_DIR / "config.json")))
OLLAMA_URL = os.getenv("WALID_OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_EMBED_URL = os.getenv("WALID_OLLAMA_EMBED_URL", "http://127.0.0.1:11434/api/embeddings")
DEFAULT_MODEL = os.getenv("WALID_MODEL", "qwen2.5:7b")
EMBED_MODEL = os.getenv("WALID_EMBED_MODEL", "nomic-embed-text")
WHISPER_MODEL = os.getenv("WALID_WHISPER_MODEL", "base")
TTS_VOICE = os.getenv("WALID_TTS_VOICE", "ar")
MAX_INPUT_CHARS = 10000
NUM_CTX = 32768
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
TOP_K_RAG = 5
SEARCH_MODES = {
    "quick": "⚡ سريع",
    "advanced": "🔎 متقدم",
    "code": "💻 كود",
    "deep": "🧠 عميق",
    "web": "🌐 ويب",
    "academic": "🎓 أكاديمي",
    "rag": "📚 قاعدة المعرفة",
}
MODE_PROMPTS = {
    "quick": "أعطِ إجابة سريعة ومباشرة وموجزة.",
    "advanced": "نفّذ بحثًا متعدد المصادر ثم قدّم تحليلًا منظمًا.",
    "code": "ركّز على الكود: اكتب، حلّل، صحّح، اشرح.",
    "deep": "حلّل الموضوع بعمق في عدة خطوات.",
    "web": "استخدم نتائج ويب حقيقية.",
    "academic": "استخدم نتائج أكاديمية فعلية.",
    "rag": "ابحث في قاعدة المعرفة المحلية المرفوعة واستشهد منها.",
}

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "dark_mode": True,
        "workspace_path": str(Path.cwd()),
        "voice_enabled": True,
        "auto_learn": True,
    }


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
