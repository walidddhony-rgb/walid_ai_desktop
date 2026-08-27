"""SQLite database manager for conversations, messages, files, and memory."""
from __future__ import annotations
import sqlite3, uuid, json
from datetime import datetime
from typing import Dict, List, Optional
from core.config import DB_PATH
from db.schema import SCHEMA_SQL


class Database:
    def __init__(self, db_path=None):
        self.db_path = str(db_path) if db_path else str(DB_PATH)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.init()

    def init(self):
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def convs(self) -> List[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC")]

    def conv(self, cid: str) -> List[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT id,role,content,created_at FROM messages WHERE conversation_id=? ORDER BY id",
            (cid,))]

    def add_conv(self, title: str, cid: Optional[str] = None) -> str:
        cid = cid or str(uuid.uuid4())
        now = datetime.now().isoformat()
        self.conn.execute("INSERT INTO conversations VALUES(?,?,?,?)", (cid, title, now, now))
        self.conn.commit()
        return cid

    def add_msg(self, cid: str, role: str, content: str) -> int:
        now = datetime.now().isoformat()
        cur = self.conn.execute(
            "INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)",
            (cid, role, content, now))
        if role == 'user':
            self.conn.execute("UPDATE conversations SET updated_at=?,title=? WHERE id=?",
                              (now, content[:55], cid))
        else:
            self.conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, cid))
        self.conn.commit()
        return cur.lastrowid

    def add_file(self, cid: str, filename: str, path, ext: str, size: int, text: str):
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT INTO uploaded_files(conversation_id,filename,path,file_type,size,extracted_text,created_at) VALUES(?,?,?,?,?,?,?)",
            (cid, filename, str(path), ext, size, text, now))
        self.conn.commit()

    def files(self, cid: str) -> List[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT id,filename,file_type,size,created_at,path FROM uploaded_files WHERE conversation_id=? ORDER BY id DESC",
            (cid,))]

    def recent_file_rows(self, cid: str, limit: int = 3) -> List[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM uploaded_files WHERE conversation_id=? ORDER BY id DESC LIMIT ?",
            (cid, limit))]

    def delete_file(self, fid: int):
        row = self.conn.execute("SELECT path FROM uploaded_files WHERE id=?", (fid,)).fetchone()
        self.conn.execute("DELETE FROM uploaded_files WHERE id=?", (fid,))
        self.conn.commit()
        if row:
            try:
                from pathlib import Path
                Path(row["path"]).unlink(missing_ok=True)
            except Exception:
                pass

    def search_convs(self, q: str) -> List[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM conversations WHERE title LIKE ? ORDER BY updated_at DESC",
            (f"%{q}%",))]

    def add_feedback(self, mid: int, rating: str):
        now = datetime.now().isoformat()
        self.conn.execute("INSERT INTO feedback(message_id,rating,created_at) VALUES(?,?,?)",
                          (mid, rating, now))
        self.conn.commit()

    def add_memory(self, key: str, value: str):
        now = datetime.now().isoformat()
        ex = self.conn.execute("SELECT id FROM memory WHERE key=?", (key,)).fetchone()
        if ex:
            self.conn.execute("UPDATE memory SET value=?,created_at=? WHERE id=?",
                              (value, now, ex["id"]))
        else:
            self.conn.execute("INSERT INTO memory(key,value,created_at) VALUES(?,?,?)",
                              (key, value, now))
        self.conn.commit()

    def get_all_memory(self) -> Dict[str, str]:
        rows = self.conn.execute("SELECT key,value FROM memory ORDER BY id DESC").fetchall()
        return {r["key"]: r["value"] for r in rows}

    def save_search_cache(self, query: str, scope: str, results: list):
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT INTO search_cache(query,scope,results_json,created_at) VALUES(?,?,?,?)",
            (query, scope, json.dumps(results, ensure_ascii=False), now))
        self.conn.commit()

    def delete_conv(self, cid: str):
        self.conn.execute("DELETE FROM messages WHERE conversation_id=?", (cid,))
        self.conn.execute("DELETE FROM uploaded_files WHERE conversation_id=?", (cid,))
        self.conn.execute("DELETE FROM conversations WHERE id=?", (cid,))
        self.conn.commit()

    def close(self):
        self.conn.close()
