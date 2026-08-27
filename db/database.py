import sqlite3
import uuid
from datetime import datetime

from core.config import DB_PATH


class Database:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.init()

    def init(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations(
                id TEXT PRIMARY KEY, title TEXT, created_at TEXT, updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY, conversation_id TEXT, role TEXT, content TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS uploaded_files(
                id INTEGER PRIMARY KEY, conversation_id TEXT, filename TEXT, path TEXT,
                file_type TEXT, size INTEGER, extracted_text TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS feedback(
                id INTEGER PRIMARY KEY, message_id INTEGER, rating TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS memory(
                id INTEGER PRIMARY KEY, key TEXT, value TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS search_cache(
                id INTEGER PRIMARY KEY, query TEXT, scope TEXT, results_json TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS knowledge_chunks(
                id INTEGER PRIMARY KEY, source_file TEXT, chunk_index INTEGER,
                chunk_text TEXT, embedding TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS learned_facts(
                id INTEGER PRIMARY KEY, conversation_id TEXT, fact TEXT, category TEXT, created_at TEXT
            );
            """
        )
        self.conn.commit()

    def add_conv(self, title, cid=None):
        cid = cid or str(uuid.uuid4())
        now = datetime.now().isoformat()
        self.conn.execute("INSERT INTO conversations VALUES(?,?,?,?)", (cid, title, now, now))
        self.conn.commit()
        return cid

    def add_msg(self, cid, role, content):
        now = datetime.now().isoformat()
        cur = self.conn.execute(
            "INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)",
            (cid, role, content, now),
        )
        self.conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, cid))
        self.conn.commit()
        return cur.lastrowid

    def add_memory(self, key, value):
        now = datetime.now().isoformat()
        ex = self.conn.execute("SELECT id FROM memory WHERE key=?", (key,)).fetchone()
        if ex:
            self.conn.execute("UPDATE memory SET value=?,created_at=? WHERE id=?", (value, now, ex['id']))
        else:
            self.conn.execute("INSERT INTO memory(key,value,created_at) VALUES(?,?,?)", (key, value, now))
        self.conn.commit()

    def get_all_memory(self):
        rows = self.conn.execute("SELECT key,value FROM memory ORDER BY id DESC").fetchall()
        return {r['key']: r['value'] for r in rows}

    def add_knowledge_chunk(self, source_file, chunk_index, chunk_text, embedding=""):
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT INTO knowledge_chunks(source_file,chunk_index,chunk_text,embedding,created_at) VALUES(?,?,?,?,?)",
            (source_file, chunk_index, chunk_text, embedding, now),
        )
        self.conn.commit()

    def add_learned_fact(self, cid, fact, category="general"):
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT INTO learned_facts(conversation_id,fact,category,created_at) VALUES(?,?,?,?)",
            (cid, fact, category, now),
        )
        self.conn.commit()

    def get_learned_facts(self, limit=50):
        rows = self.conn.execute("SELECT fact FROM learned_facts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [r['fact'] for r in rows]
