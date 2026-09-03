import json
from datetime import datetime

from core.config import DATA_DIR

SESSIONS_DIR = DATA_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def save_session(cid: str, messages: list, title: str = "") -> str:
    fname = f"session_{cid}.json"
    path = SESSIONS_DIR / fname
    data = {
        "cid": cid,
        "title": title,
        "messages": messages,
        "saved_at": datetime.now().isoformat(),
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def load_session(cid: str) -> dict:
    path = SESSIONS_DIR / f"session_{cid}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def list_sessions() -> list:
    sessions = []
    for f in sorted(SESSIONS_DIR.glob("session_*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            sessions.append(
                {
                    "cid": data.get("cid", ""),
                    "title": data.get("title", ""),
                    "saved_at": data.get("saved_at", ""),
                    "path": str(f),
                    "message_count": len(data.get("messages", [])),
                }
            )
        except Exception:
            pass
    return sessions


def load_last_session() -> dict:
    sessions = list_sessions()
    if not sessions:
        return {}
    return load_session(sessions[0]["cid"])
