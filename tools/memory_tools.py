"""Memory tool implementations."""
from __future__ import annotations
import json, sqlite3, uuid
from datetime import datetime
from core.config import DB_PATH


def save_memory(key: str, value: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().isoformat()
    ex = conn.execute("SELECT id FROM memory WHERE key=?", (key,)).fetchone()
    if ex:
        conn.execute("UPDATE memory SET value=?,created_at=? WHERE id=?", (value, now, ex[0]))
    else:
        conn.execute("INSERT INTO memory(key,value,created_at) VALUES(?,?,?)", (key, value, now))
    conn.commit()
    conn.close()
    return "Saved to memory successfully"


def get_memory() -> str:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT key,value FROM memory ORDER BY id DESC").fetchall()
    conn.close()
    return json.dumps({r[0]: r[1] for r in rows}, ensure_ascii=False)
