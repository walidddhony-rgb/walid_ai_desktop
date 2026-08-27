"""Application configuration and constants."""
import json, os
from pathlib import Path
from core.paths import DATA_DIR

DB_PATH = Path(os.getenv("WALID_DB_PATH", str(DATA_DIR / "walid_ai.db")))
CONFIG_PATH = Path(os.getenv("WALID_CONFIG_PATH", str(DATA_DIR / "config.json")))
OLLAMA_URL = os.getenv("WALID_OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
DEFAULT_MODEL = os.getenv("WALID_MODEL", "qwen2.5:7b")
WHISPER_MODEL_SIZE = os.getenv("WALID_WHISPER_MODEL", "base")

MAX_INPUT_CHARS = 10000
MAX_AGENT_ITERATIONS = 15
OLLAMA_TIMEOUT = (10, 300)
OLLAMA_RETRY_COUNT = 2
NUM_CTX = 32768

SEARCH_MODES = {
    "quick": "⚡ سريع",
    "advanced": "🔎 متقدم",
    "code": "💻 كود",
    "deep": "🧠 عميق",
    "web": "🌐 ويب",
    "academic": "🎓 أكاديمي",
}

MODE_PROMPTS = {
    "quick": "أعطِ إجابة سريعة ومباشرة وموجزة.",
    "advanced": "نفّذ بحثًا متعدد المصادر ثم قدّم تحليلًا منظمًا.",
    "code": "ركّز على الكود: اكتب، حلّل، صحّح، اشرح.",
    "deep": "حلّل الموضوع بعمق في عدة خطوات.",
    "web": "استخدم نتائج ويب حقيقية.",
    "academic": "استخدم نتائج أكاديمية فعلية.",
}

DESTRUCTIVE_TOOLS = {"move_file", "archive_folder", "create_file", "create_directory"}

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"dark_mode": True}


def save_config(config: dict) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
