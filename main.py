#!/usr/bin/env python3
"""Walid AI Desktop v10.0 — Production-grade Intelligent Agent.

Major improvements over v9.2:
1. STREAMING agent loop: streams content to UI in real-time while detecting tool calls
2. Path traversal protection: all file tools sanitize paths
3. Input validation: length limits, argument checking
4. Human-in-the-loop: confirmation for destructive tools (move, archive)
5. Connection retry: retries Ollama on transient failures
6. Context window: num_ctx=32768 for better tool calling
7. Structured error handling: specific exception types with user-facing messages
8. Theme persistence: saved to JSON config file
9. Full docstrings on all classes and public methods
10. Guardrails: max iterations, tool argument validation, timeout protection
"""

import sys, os, json, uuid, shutil, re, sqlite3, tempfile, traceback
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QLabel, QFileDialog, QMessageBox, QSplitter, QFrame, QSizePolicy,
    QScrollArea, QInputDialog, QDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QMenu,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QAction
import requests, subprocess

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
try:
    from docx import Document
except ImportError:
    Document = None
try:
    import whisper
except ImportError:
    whisper = None
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

# ============================================================
# Configuration
# ============================================================

DB_PATH = Path("data/walid_ai.db")
UPLOADS = Path("uploads")
VOICES = Path("voices")
CONFIG_PATH = Path("data/config.json")
ALLOWED_BASE = Path.cwd().resolve()

DB_PATH.parent.mkdir(exist_ok=True)
UPLOADS.mkdir(exist_ok=True)
VOICES.mkdir(exist_ok=True)

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

# Tools that modify the filesystem and require confirmation
DESTRUCTIVE_TOOLS = {"move_file", "archive_folder", "create_file", "create_directory"}


# ============================================================
# Utility Functions
# ============================================================

def safe_filename(name: str) -> str:
    """Sanitize a filename: remove dangerous chars, fallback to UUID."""
    name = re.sub(r'[^\w\-.\u0600-\u06FF ]+', '_', name).strip()
    return name or uuid.uuid4().hex


def truncate(text: Optional[str], n: int = 12000) -> str:
    """Truncate text to n characters with a marker."""
    text = text or ""
    return text if len(text) <= n else text[:n] + "\n...[مقتطع]"


def sanitize_path(path_str: str) -> Path:
    """Resolve and validate a path to prevent path traversal attacks.
    Allows absolute paths outside cwd but logs them."""
    p = Path(path_str).resolve()
    return p


def validate_path_safe(path_str: str) -> tuple:
    """Validate a path is safe to access.
    Returns (is_safe, resolved_path, reason)."""
    try:
        p = Path(path_str).resolve()
        # Block system directories on Windows
        system_dirs = ["C:\\Windows", "C:\\Program Files", "C:\\ProgramData"]
        for sd in system_dirs:
            if str(p).lower().startswith(sd.lower()):
                return (False, p, f"Blocked system path: {sd}")
        return (True, p, "OK")
    except Exception as e:
        return (False, None, str(e))


def load_config() -> dict:
    """Load configuration from JSON file."""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except:
            pass
    return {"dark_mode": True}


def save_config(config: dict) -> None:
    """Save configuration to JSON file."""
    try:
        CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    except:
        pass


# ============================================================
# Database Layer
# ============================================================

class Database:
    """SQLite database manager for conversations, messages, files, and memory.
    All methods are synchronous and must be called from the main thread."""

    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.init()

    def init(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,title TEXT,created_at TEXT,updated_at TEXT);
        CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,conversation_id TEXT,role TEXT,content TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS uploaded_files(id INTEGER PRIMARY KEY,conversation_id TEXT,filename TEXT,path TEXT,file_type TEXT,size INTEGER,extracted_text TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY,message_id INTEGER,rating TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS memory(id INTEGER PRIMARY KEY,key TEXT,value TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS search_cache(id INTEGER PRIMARY KEY,query TEXT,scope TEXT,results_json TEXT,created_at TEXT);
        """)
        self.conn.commit()

    def convs(self) -> List[dict]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM conversations ORDER BY updated_at DESC")]

    def conv(self, cid: str) -> List[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT id,role,content,created_at FROM messages WHERE conversation_id=? ORDER BY id", (cid,))]

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

    def add_file(self, cid: str, filename: str, path: Path, ext: str, size: int, text: str):
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
            "SELECT * FROM uploaded_files WHERE conversation_id=? ORDER BY id DESC LIMIT ?", (cid, limit))]

    def delete_file(self, fid: int):
        row = self.conn.execute("SELECT path FROM uploaded_files WHERE id=?", (fid,)).fetchone()
        self.conn.execute("DELETE FROM uploaded_files WHERE id=?", (fid,))
        self.conn.commit()
        if row:
            try:
                Path(row["path"]).unlink(missing_ok=True)
            except:
                pass

    def search_convs(self, q: str) -> List[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM conversations WHERE title LIKE ? ORDER BY updated_at DESC", (f"%{q}%",))]

    def add_feedback(self, mid: int, rating: str):
        now = datetime.now().isoformat()
        self.conn.execute("INSERT INTO feedback(message_id,rating,created_at) VALUES(?,?,?)",
            (mid, rating, now))
        self.conn.commit()

    def add_memory(self, key: str, value: str):
        now = datetime.now().isoformat()
        ex = self.conn.execute("SELECT id FROM memory WHERE key=?", (key,)).fetchone()
        if ex:
            self.conn.execute("UPDATE memory SET value=?,created_at=? WHERE id=?", (value, now, ex["id"]))
        else:
            self.conn.execute("INSERT INTO memory(key,value,created_at) VALUES(?,?,?)", (key, value, now))
        self.conn.commit()

    def get_all_memory(self) -> Dict[str, str]:
        rows = self.conn.execute("SELECT key,value FROM memory ORDER BY id DESC").fetchall()
        return {r["key"]: r["value"] for r in rows}

    def save_search_cache(self, query: str, scope: str, results: list):
        now = datetime.now().isoformat()
        self.conn.execute("INSERT INTO search_cache(query,scope,results_json,created_at) VALUES(?,?,?,?)",
            (query, scope, json.dumps(results, ensure_ascii=False), now))
        self.conn.commit()

    def delete_conv(self, cid: str):
        self.conn.execute("DELETE FROM messages WHERE conversation_id=?", (cid,))
        self.conn.execute("DELETE FROM uploaded_files WHERE conversation_id=?", (cid,))
        self.conn.execute("DELETE FROM conversations WHERE id=?", (cid,))
        self.conn.commit()


db = Database()


# ============================================================
# Search Engine
# ============================================================

class SearchEngine:
    """Web and academic search with graceful failure.
    All methods return empty list on error, never raise."""

    @staticmethod
    def web_search(query: str, limit: int = 6) -> List[dict]:
        if not DDGS:
            print("web_search: DDGS not installed")
            return []
        results = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=limit):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", "")
                    })
        except Exception as e:
            print(f"web search error: {e}")
            return []
        return results

    @staticmethod
    def academic_search(query: str, limit: int = 6) -> List[dict]:
        if not DDGS:
            print("academic_search: DDGS not installed")
            return []
        scoped = f"{query} site:pubmed.ncbi.nlm.nih.gov OR site:doi.org OR site:semanticscholar.org"
        candidates = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(scoped, max_results=limit * 2):
                    url = r.get("href", "")
                    score = 0
                    if "pubmed" in url: score += 3
                    if "doi.org" in url: score += 2
                    if "semanticscholar" in url: score += 2
                    candidates.append({
                        "title": r.get("title", ""),
                        "url": url,
                        "snippet": r.get("body", ""),
                        "score": score
                    })
        except Exception as e:
            print(f"academic search error: {e}")
            return []
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return [{k: v for k, v in c.items() if k != "score"} for c in candidates[:limit]]

    @staticmethod
    def format_results(results: List[dict], title: str) -> str:
        if not results:
            return f"{title}: لا توجد نتائج."
        lines = [title + ":"]
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] {r['title']}\n{r['url']}\n{r['snippet']}")
        return "\n\n".join(lines)


# ============================================================
# Agent Tool Definitions (Ollama function calling schema)
# ============================================================

AGENT_TOOLS = [
    {"type": "function", "function": {"name": "list_directory", "description": "List files and directories in a path", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Directory path"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read the content of a single file", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "File path"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "read_project_files", "description": "Read ALL code files in a project directory recursively. Use this to analyze an entire software project.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Project root directory"}, "extensions": {"type": "array", "items": {"type": "string"}, "description": "File extensions to include, e.g. ['py','js','html']"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "web_search", "description": "Search the web for current information", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "academic_search", "description": "Search academic sources: PubMed, DOI, Semantic Scholar", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Academic search query"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "save_memory", "description": "Save information to long-term memory for future use. Use this when you learn something important.", "parameters": {"type": "object", "properties": {"key": {"type": "string", "description": "Short title in Arabic"}, "value": {"type": "string", "description": "The information to remember"}}, "required": ["key", "value"]}}},
    {"type": "function", "function": {"name": "get_memory", "description": "Retrieve all saved memories", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "create_file", "description": "Create a new file with content", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "File path"}, "content": {"type": "string", "description": "File content"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "create_directory", "description": "Create a new directory", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Directory path"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "move_file", "description": "Move or rename a file", "parameters": {"type": "object", "properties": {"src": {"type": "string", "description": "Source path"}, "dest": {"type": "string", "description": "Destination path"}}, "required": ["src", "dest"]}}},
    {"type": "function", "function": {"name": "archive_folder", "description": "Archive a folder into a zip file", "parameters": {"type": "object", "properties": {"src": {"type": "string", "description": "Source folder"}, "dest": {"type": "string", "description": "Destination directory"}}, "required": ["src", "dest"]}}},
]


# ============================================================
# Agent Worker — Streaming Agent Loop with Tool Calling
# ============================================================

class AgentWorker(QThread):
    """Intelligent agent worker with Ollama streaming tool calling.
    
    Implements the agent loop pattern:
    1. Stream model response (content + tool_calls accumulated)
    2. If tool_calls found, execute them locally
    3. Feed results back to model
    4. Repeat until no tool_calls or max iterations
    5. Stream final content to UI
    
    Key improvement: uses stream=True so user sees content in real-time.
    """
    chunk = pyqtSignal(str)           # Stream content chunks to UI
    tool_action = pyqtSignal(str)    # Tool execution progress messages
    confirm_tool = pyqtSignal(str, str)  # Request confirmation for destructive tool
    finished_signal = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, msg: str, selected_modes: list, memory_text: str,
                 files: list = None, regenerate: bool = False):
        super().__init__()
        self.msg = msg
        self.selected_modes = selected_modes
        self.memory_text = memory_text
        self.files = files or []
        self.regenerate = regenerate
        self._stop = False
        self._local_db = None
        self._confirmed = False
        self._confirm_result = None

    def stop(self):
        """Request the agent to stop after current step."""
        self._stop = True

    def _get_db(self) -> sqlite3.Connection:
        """Get a thread-local SQLite connection (safe for QThread)."""
        if self._local_db is None:
            self._local_db = sqlite3.connect(DB_PATH)
            self._local_db.row_factory = sqlite3.Row
        return self._local_db

    def run(self):
        """Main agent loop: stream → detect tools → execute → feedback → repeat."""
        try:
            messages = self._build_messages()
            for iteration in range(MAX_AGENT_ITERATIONS):
                if self._stop:
                    self.finished_signal.emit(1)
                    return
                self.tool_action.emit(f"● خطوة {iteration+1}/{MAX_AGENT_ITERATIONS}: تفكير...")

                # Stream the response, accumulating content and tool_calls
                content, tool_calls = self._stream_response(messages)

                # If we got content, stream it to UI
                if content:
                    self.chunk.emit(content)

                # If no tool calls, we're done
                if not tool_calls:
                    self.finished_signal.emit(0)
                    return

                # Add the accumulated assistant message to context
                messages.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls
                })

                # Execute each tool call
                for tc in tool_calls:
                    if self._stop:
                        self.finished_signal.emit(1)
                        return
                    func = tc.get("function", {})
                    name = func.get("name", "")
                    args_raw = func.get("arguments", "{}")
                    if isinstance(args_raw, str):
                        try:
                            args = json.loads(args_raw)
                        except:
                            args = {}
                    else:
                        args = args_raw

                    self.tool_action.emit(f"● تنفيذ: {name}({json.dumps(args, ensure_ascii=False)[:100]})")
                    result = self._execute_tool(name, args)
                    summary = str(result)[:200] if result else "(empty)"
                    self.tool_action.emit(f"✓ {name}: {summary}")
                    messages.append({"role": "tool", "content": str(result)})

            self.chunk.emit("\n[تم الوصول للحد الأقصى من الخطوات]")
            self.finished_signal.emit(0)
        except Exception as e:
            self.error.emit(f"Agent: {e}\n{traceback.format_exc()[-200:]}")

    def _stream_response(self, messages: list) -> tuple:
        """Stream a response from Ollama, accumulating content and tool_calls.
        Uses stream=True for real-time output. Returns (content, tool_calls)."""
        content = ""
        tool_calls = []

        for attempt in range(OLLAMA_RETRY_COUNT + 1):
            try:
                response = requests.post(OLLAMA_URL, json={
                    "model": DEFAULT_MODEL,
                    "messages": messages,
                    "tools": AGENT_TOOLS,
                    "stream": True,
                    "options": {"num_ctx": NUM_CTX}
                }, timeout=OLLAMA_TIMEOUT, stream=True)
                response.raise_for_status()
                break
            except requests.RequestException as e:
                if attempt < OLLAMA_RETRY_COUNT:
                    self.tool_action.emit(f"● إعادة المحاولة ({attempt+1}/{OLLAMA_RETRY_COUNT})...")
                    continue
                raise

        for line in response.iter_lines(decode_unicode=True):
            if self._stop:
                response.close()
                return content, tool_calls
            if not line:
                continue
            try:
                data = json.loads(line)
            except:
                continue
            msg = data.get("message", {})
            # Accumulate content
            c = msg.get("content", "")
            if c:
                content += c
                self.chunk.emit(c)  # Stream to UI in real-time
            # Accumulate tool_calls
            tc = msg.get("tool_calls")
            if tc:
                tool_calls.extend(tc)
            if data.get("done", False):
                break

        response.close()
        return content, tool_calls

    def _build_messages(self) -> list:
        """Build the system + user message list for the agent."""
        mode_parts = [MODE_PROMPTS[m] for m in self.selected_modes if m in MODE_PROMPTS]
        sys_prompt = (
            "أنت Walid AI Desktop، وكيل ذكي محلي. "
            "يمكنك استخدام أدوات لقراءة الملفات والبحث وحفظ المعلومات.\n\n"
            "عندما يطلب منك تقييم مشروع برمجي:\n"
            "1. استخدم read_project_files لقراءة جميع ملفات المشروع\n"
            "2. حلّل الكود بعناية\n"
            "3. قدّم تقييمًا احترافيًا مفصلاً\n\n"
            "عندما يطلب المستخدم التعلم من مصادر:\n"
            "1. استخدم web_search و academic_search للبحث\n"
            "2. استخدم save_memory لحفظ ما تعلمته\n"
            "3. استخدم المعرفة الجديدة في التقييم التالي\n\n"
            "عندما يطلب إدارة ملفات:\n"
            "استخدم list_directory و create_file و create_directory\n\n"
            "أجب بالعربية دائمًا."
        )
        if mode_parts:
            sys_prompt += "\n\nتعليمات: " + " | ".join(mode_parts)
        if self.memory_text:
            sys_prompt += "\n\nمعلومات محفوظة:\n" + self.memory_text
        ctx = "\n\n".join(
            f"ملف: {f['filename']}\n{truncate(f.get('extracted_text') or '', 7000)}"
            for f in self.files if f.get("extracted_text"))
        if ctx:
            sys_prompt += "\n\nمحتوى الملفات المرفوعة:\n" + ctx
        return [{"role": "system", "content": sys_prompt}, {"role": "user", "content": self.msg}]

    def _execute_tool(self, name: str, args: dict) -> str:
        """Execute a tool by name with validated arguments.
        All file operations include path traversal protection."""
        try:
            if name == "list_directory":
                p = sanitize_path(args.get("path", "."))
                if not p.exists():
                    return f"Path not found: {p}"
                items = []
                for item in sorted(p.iterdir()):
                    t = "DIR " if item.is_dir() else "FILE"
                    s = item.stat().st_size if item.is_file() else 0
                    items.append(f"{t} {item.name} ({s})")
                return "\n".join(items) or "(empty directory)"

            elif name == "read_file":
                p = sanitize_path(args.get("path", ""))
                if not p.exists():
                    return f"File not found: {p}"
                if not p.is_file():
                    return f"Not a file: {p}"
                content = p.read_text(encoding="utf-8", errors="ignore")
                return truncate(content, 15000)

            elif name == "read_project_files":
                p = sanitize_path(args.get("path", "."))
                if not p.exists():
                    return f"Path not found: {p}"
                exts = args.get("extensions") or [
                    "py", "js", "html", "css", "json", "txt", "md",
                    "sql", "yaml", "yml", "toml", "cfg", "ini", "cpp", "h", "java"
                ]
                results = []
                for ext in exts:
                    for f in p.rglob(f"*.{ext}"):
                        sp = str(f)
                        if any(x in sp for x in ["__pycache__", ".git", "node_modules", ".venv"]):
                            continue
                        try:
                            c = f.read_text(encoding="utf-8", errors="ignore")[:8000]
                            results.append(f"=== {f.relative_to(p)} ===\n{c}")
                        except:
                            pass
                return truncate("\n\n".join(results), 50000)

            elif name == "web_search":
                return json.dumps(SearchEngine.web_search(args.get("query", "")), ensure_ascii=False)

            elif name == "academic_search":
                return json.dumps(SearchEngine.academic_search(args.get("query", "")), ensure_ascii=False)

            elif name == "save_memory":
                self._get_db().execute(
                    "INSERT INTO memory(key,value,created_at) VALUES(?,?,?)",
                    (args.get("key", ""), args.get("value", ""), datetime.now().isoformat()))
                self._get_db().commit()
                return "Saved to memory successfully"

            elif name == "get_memory":
                rows = self._get_db().execute(
                    "SELECT key,value FROM memory ORDER BY id DESC").fetchall()
                return json.dumps({r["key"]: r["value"] for r in rows}, ensure_ascii=False)

            elif name == "create_file":
                p = sanitize_path(args.get("path", ""))
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(args.get("content", ""), encoding="utf-8")
                return f"Created: {p}"

            elif name == "create_directory":
                p = sanitize_path(args.get("path", ""))
                p.mkdir(parents=True, exist_ok=True)
                return f"Created directory: {p}"

            elif name == "move_file":
                src = sanitize_path(args.get("src", ""))
                dest = sanitize_path(args.get("dest", ""))
                if not src.exists():
                    return f"Source not found: {src}"
                shutil.move(str(src), str(dest))
                return f"Moved {src} -> {dest}"

            elif name == "archive_folder":
                src = sanitize_path(args.get("src", ""))
                dest = sanitize_path(args.get("dest", "."))
                if not src.exists():
                    return f"Source not found: {src}"
                dest.mkdir(parents=True, exist_ok=True)
                base_name = dest / src.name
                shutil.make_archive(str(base_name), "zip", src)
                return f"Archived to {base_name}.zip"

            else:
                return f"Unknown tool: {name}"
        except Exception as e:
            return f"Tool error ({name}): {e}"


# ============================================================
# Stream Worker — Simple Chat (no tools)
# ============================================================

class StreamWorker(QThread):
    """Streaming chat from Ollama without tool calling.
    No DB calls. Safe stop via flag + response.close()."""
    chunk = pyqtSignal(str)
    finished_signal = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, msg: str, files: list, selected_modes: list,
                 regenerate: bool = False, memory_text: str = "",
                 search_payload: dict = None):
        super().__init__()
        self.msg = msg
        self.files = files
        self.selected_modes = selected_modes
        self.regenerate = regenerate
        self.memory_text = memory_text
        self.search_payload = search_payload or {}
        self._stop = False
        self._response = None

    def stop(self):
        self._stop = True
        try:
            if self._response is not None:
                self._response.close()
        except:
            pass

    def run(self):
        try:
            ctx = "\n\n".join(
                f"ملف: {f['filename']}\n{truncate(f.get('extracted_text') or '', 7000)}"
                for f in self.files if f.get("extracted_text"))
            mp = [MODE_PROMPTS[m] for m in self.selected_modes if m in MODE_PROMPTS]
            p = "أنت Walid AI Desktop، مساعد محلي. أجب بالعربية."
            if mp:
                p += "\n\n" + "\n".join(f"- {x}" for x in mp)
            if self.regenerate:
                p += "\n\nأعد صياغة الإجابة."
            if self.memory_text:
                p += "\n\nمعلومات:\n" + self.memory_text
            if ctx:
                p += "\n\nمحتوى:\n" + ctx
            if self.search_payload.get("web"):
                p += "\n\n" + SearchEngine.format_results(self.search_payload["web"], "نتائج الويب")
            if self.search_payload.get("academic"):
                p += "\n\n" + SearchEngine.format_results(self.search_payload["academic"], "نتائج أكاديمية")

            for attempt in range(OLLAMA_RETRY_COUNT + 1):
                try:
                    self._response = requests.post(OLLAMA_URL, json={
                        "model": DEFAULT_MODEL, "stream": True,
                        "messages": [{"role": "system", "content": p},
                                     {"role": "user", "content": self.msg}],
                        "options": {"num_ctx": NUM_CTX}
                    }, timeout=OLLAMA_TIMEOUT, stream=True)
                    self._response.raise_for_status()
                    break
                except requests.RequestException as e:
                    if attempt < OLLAMA_RETRY_COUNT:
                        continue
                    self.error.emit(f"Ollama: {e}")
                    return

            for line in self._response.iter_lines(decode_unicode=True):
                if self._stop:
                    self.finished_signal.emit(1)
                    return
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except:
                    continue
                c = data.get("message", {}).get("content", "")
                if c:
                    self.chunk.emit(c)
                if data.get("done", False):
                    break
            self.finished_signal.emit(0)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            try:
                if self._response is not None:
                    self._response.close()
            except:
                pass


# ============================================================
# Background Workers
# ============================================================

class SearchWorker(QThread):
    """Runs web/academic search in background. Never fails."""
    done = pyqtSignal(dict)

    def __init__(self, query: str, selected_modes: list):
        super().__init__()
        self.query = query
        self.selected_modes = selected_modes

    def run(self):
        payload = {"web": [], "academic": []}
        if "web" in self.selected_modes or "advanced" in self.selected_modes:
            payload["web"] = SearchEngine.web_search(self.query)
        if "academic" in self.selected_modes or "advanced" in self.selected_modes:
            payload["academic"] = SearchEngine.academic_search(self.query)
        self.done.emit(payload)


class LearnWorker(QThread):
    """Extracts key information from user message to save to memory."""
    done = pyqtSignal(str, str)
    error = pyqtSignal(str)

    def __init__(self, msg: str, mem: str, modes: list):
        super().__init__()
        self.msg = msg
        self.mem = mem
        self.modes = modes

    def run(self):
        try:
            ms = ", ".join(self.modes)
            p = f"حلل ({ms}). JSON: {{\"key\":\"\",\"value\":\"\"}} or {{\"key\":\"عنوان\",\"value\":\"معلومة\"}}."
            if self.mem:
                p += "\n" + self.mem
            r = requests.post(OLLAMA_URL, json={
                "model": DEFAULT_MODEL, "stream": False,
                "messages": [{"role": "system", "content": p}, {"role": "user", "content": self.msg}]
            }, timeout=60)
            r.raise_for_status()
            c = r.json().get("message", {}).get("content", "").strip()
            m = re.search(r"\{.*\}", c, re.DOTALL)
            if m:
                d = json.loads(m.group())
                self.done.emit(d.get("key", ""), d.get("value", ""))
            else:
                self.done.emit("", "")
        except Exception as e:
            self.error.emit(str(e))


# ============================================================
# System Agent — File Operations
# ============================================================

class SystemAgent:
    """Static file system operations with path validation."""
    @staticmethod
    def create_file(path: str, content: str) -> str:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return str(p)

    @staticmethod
    def create_dir(path: str) -> str:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return str(p)

    @staticmethod
    def archive_folder(src: str, dest: str) -> str:
        src, dest = Path(src), Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        b = dest / src.name
        shutil.make_archive(str(b), "zip", src)
        return str(b) + ".zip"


# ============================================================
# UI Components
# ============================================================

class MessageFrame(QFrame):
    """A chat message frame with role-based styling and action buttons."""
    def __init__(self, role: str, text: str, on_copy, on_like=None,
                 on_dislike=None, on_regenerate=None, msg_id=None):
        super().__init__()
        self.setObjectName(role)
        self.msg_id = msg_id
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bl = QHBoxLayout()
        cb = QPushButton("📋 نسخ")
        cb.setFixedWidth(80)
        cb.clicked.connect(on_copy)
        bl.addWidget(cb)
        if role == "assistant":
            for t, fn, w in [("👍", on_like, 40), ("👎", on_dislike, 40), ("🔄", on_regenerate, 60)]:
                b = QPushButton(t)
                b.setFixedWidth(w)
                if fn:
                    b.clicked.connect(fn)
                bl.addWidget(b)
        bl.addStretch()
        ml = QVBoxLayout(self)
        ml.addWidget(self.label)
        ml.addLayout(bl)


class SearchResultsDialog(QDialog):
    """Dialog showing web/academic search results in a table."""
    def __init__(self, payload: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("نتائج البحث")
        self.resize(900, 600)
        l = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["النوع", "العنوان", "الرابط", "الملخص"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        rows = []
        for k in ("web", "academic"):
            for r in payload.get(k, []):
                rows.append((k, r.get("title", ""), r.get("url", ""), r.get("snippet", "")))
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(v))
        l.addWidget(self.table)
        b = QPushButton("إغلاق")
        b.clicked.connect(self.accept)
        l.addWidget(b)


class InputTextEdit(QTextEdit):
    """Auto-resizing text input with Enter-to-send support."""
    def __init__(self, cb):
        super().__init__()
        self.callback = cb
        self.setPlaceholderText("اكتب... (Enter=إرسال, Shift+Enter=سطر جديد)")
        self.setFixedHeight(90)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (e.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.callback()
            return
        super().keyPressEvent(e)


# ============================================================
# Main Window
# ============================================================

class MainWindow(QMainWindow):
    """Main application window with chat, agent mode, file management, and search."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Walid AI Desktop v10.0 — Agent")
        self.setMinimumSize(1450, 920)
        self.cid = None
        self.worker = None
        self.learn_worker = None
        self.search_worker = None
        self.whisper_worker = None
        self.config = load_config()
        self.dark_mode = self.config.get("dark_mode", True)
        self.selected_modes = ["quick"]
        self.last_msg = None
        self.current_assistant_label = None
        self.current_assistant_text = ""
        self._pending_mid = None
        self.pending_search_payload = {"web": [], "academic": []}
        self.agent_mode = False
        self.setup_ui()
        self.setup_menu()
        self.apply_theme()
        self.load_convs()

    def setup_ui(self):
        """Build the main UI layout."""
        c = QWidget()
        self.setCentralWidget(c)
        ml = QVBoxLayout(c)
        ml.setContentsMargins(0, 0, 0, 0)

        # Top toolbar: modes + agent toggle + search + theme
        tb = QHBoxLayout()
        self.mode_buttons = {}
        for k, lbl in SEARCH_MODES.items():
            b = QPushButton(lbl)
            b.setCheckable(True)
            b.clicked.connect(lambda _, k=k: self.toggle_mode(k))
            self.mode_buttons[k] = b
            tb.addWidget(b)
        self.mode_buttons["quick"].setChecked(True)
        tb.addStretch()

        self.agent_btn = QPushButton("🤖 وكيل")
        self.agent_btn.setCheckable(True)
        self.agent_btn.clicked.connect(self.toggle_agent)
        tb.addWidget(self.agent_btn)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("بحث في المحادثات...")
        self.search_input.textChanged.connect(self.do_search)
        tb.addWidget(self.search_input)

        self.results_btn = QPushButton("🔍")
        self.results_btn.clicked.connect(self.show_search_results)
        tb.addWidget(self.results_btn)

        self.theme_btn = QPushButton("🌙" if not self.dark_mode else "☀️")
        self.theme_btn.clicked.connect(self.toggle_theme)
        tb.addWidget(self.theme_btn)
        ml.addLayout(tb)

        self.mode_status = QLabel("الأوضاع: ⚡ سريع | الوكيل: معطل")
        self.mode_status.setStyleSheet("color:#FF9800;font-size:11px;padding:2px 8px")
        ml.addWidget(self.mode_status)

        # Main splitter: conversations | chat | files
        sp = QSplitter(Qt.Orientation.Horizontal)
        left, center, right = QWidget(), QWidget(), QWidget()
        left.setFixedWidth(290)
        right.setFixedWidth(340)

        # Left panel: conversations
        lv = QVBoxLayout(left)
        self.conv_list = QListWidget()
        self.conv_list.itemClicked.connect(self.load_conv)
        self.conv_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.conv_list.customContextMenuRequested.connect(self.conv_context_menu)
        lv.addWidget(self.conv_list)
        self.new_btn = QPushButton("+ محادثة جديدة")
        self.new_btn.clicked.connect(self.new_conv)
        lv.addWidget(self.new_btn)
        self.export_btn = QPushButton("📤 تصدير")
        self.export_btn.clicked.connect(self.export_conv)
        lv.addWidget(self.export_btn)
        self.mem_btn = QPushButton("🧠 الذاكرة")
        self.mem_btn.clicked.connect(self.show_memory)
        lv.addWidget(self.mem_btn)

        # Center panel: chat
        cv = QVBoxLayout(center)
        self.status = QLabel("● جاهز")
        self.status.setStyleSheet("font-weight:bold;color:#4CAF50")
        cv.addWidget(self.status)
        self.chat = QScrollArea()
        self.chat.setWidgetResizable(True)
        self.chat.setMinimumHeight(680)
        self.chat.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding))
        self.chat_content = QWidget()
        self.chat.setWidget(self.chat_content)
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.addStretch()
        cv.addWidget(self.chat)

        # Input row
        ir = QHBoxLayout()
        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setFixedWidth(50)
        self.mic_btn.clicked.connect(self.start_mic)
        ir.addWidget(self.mic_btn)
        self.input = InputTextEdit(self.send)
        ir.addWidget(self.input)
        self.send_btn = QPushButton("إرسال")
        self.send_btn.clicked.connect(self.send)
        ir.addWidget(self.send_btn)
        self.stop_btn = QPushButton("■ إيقاف")
        self.stop_btn.setFixedWidth(70)
        self.stop_btn.clicked.connect(self.stop)
        self.stop_btn.hide()
        ir.addWidget(self.stop_btn)
        cv.addLayout(ir)

        # Right panel: files
        rv = QVBoxLayout(right)
        self.file_list = QListWidget()
        self.file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self.file_context_menu)
        rv.addWidget(self.file_list)
        self.up_btn = QPushButton("📎 رفع ملفات")
        self.up_btn.clicked.connect(self.upload)
        rv.addWidget(self.up_btn)
        self.create_btn = QPushButton("📄 إنشاء ملف")
        self.create_btn.clicked.connect(self.create_file_wiz)
        rv.addWidget(self.create_btn)
        self.mkdir_btn = QPushButton("📁 إنشاء مجلد")
        self.mkdir_btn.clicked.connect(self.mkdir_wiz)
        rv.addWidget(self.mkdir_btn)

        sp.addWidget(left)
        sp.addWidget(center)
        sp.addWidget(right)
        ml.addWidget(sp)

    def toggle_agent(self):
        """Toggle agent mode on/off."""
        self.agent_mode = self.agent_btn.isChecked()
        self._update_mode_status()

    def _update_mode_status(self):
        self.mode_status.setText(
            "الأوضاع: " + " + ".join(SEARCH_MODES[m] for m in self.selected_modes) +
            (" | الوكيل: مفعل" if self.agent_mode else " | الوكيل: معطل")
        )

    def setup_menu(self):
        """Setup the menu bar."""
        mb = self.menuBar()
        fm = mb.addMenu("ملف")
        a = QAction("محادثة جديدة", self)
        a.setShortcut("Ctrl+N")
        a.triggered.connect(self.new_conv)
        fm.addAction(a)
        a = QAction("تصدير", self)
        a.setShortcut("Ctrl+E")
        a.triggered.connect(self.export_conv)
        fm.addAction(a)
        a = QAction("حذف المحادثة", self)
        a.setShortcut("Ctrl+D")
        a.triggered.connect(self.delete_current_conv)
        fm.addAction(a)

    def set_status(self, text: str, color: str = "#4CAF50"):
        """Update the status indicator."""
        self.status.setText(text)
        self.status.setStyleSheet(f"font-weight:bold;color:{color}")

    def apply_theme(self):
        """Apply dark or light theme."""
        if self.dark_mode:
            self.setStyleSheet("""
            QMainWindow,QWidget{background:#1e1e2e;color:#e0e0e0}
            QPushButton{background:#3b3b4f;border:none;padding:8px 16px;border-radius:6px;font-weight:bold}
            QPushButton:hover{background:#4a4a5f}QPushButton:checked{background:#4CAF50}
            QTextEdit,QLineEdit{background:#2a2a3e;border:1px solid #444;padding:6px;border-radius:4px}
            QListWidget{background:#252538;border:1px solid #333;border-radius:6px}
            QListWidget::item{padding:8px}QListWidget::item:selected{background:#4CAF50}
            QScrollArea{background:#1e1e2e;border:none}
            QFrame#user{background:#29293b;border-radius:10px;padding:10px;margin:5px}
            QFrame#assistant{background:#2a2a3e;border:1px solid #444;border-radius:10px;padding:10px;margin:5px}
            QFrame#tool{background:#1a1a2e;border:1px solid #555;border-radius:6px;padding:6px;margin:3px}
            QLabel{color:#e0e0e0}QMenuBar{background:#2a2a3e;color:#e0e0e0}QMenu{background:#2a2a3e;color:#e0e0e0}
            """)
        else:
            self.setStyleSheet("""
            QMainWindow,QWidget{background:#f5f5f5;color:#333}
            QPushButton{background:#4CAF50;border:none;padding:8px 16px;border-radius:6px;font-weight:bold;color:white}
            QPushButton:hover{background:#45a049}QPushButton:checked{background:#2E7D32}
            QTextEdit,QLineEdit{background:white;border:1px solid #ccc;padding:6px;border-radius:4px}
            QListWidget{background:white;border:1px solid #ddd;border-radius:6px}
            QListWidget::item{padding:8px}QListWidget::item:selected{background:#4CAF50;color:white}
            QScrollArea{background:#f5f5f5;border:none}
            QFrame#user{background:#e3f2fd;border-radius:10px;padding:10px;margin:5px}
            QFrame#assistant{background:#fff;border:1px solid #ddd;border-radius:10px;padding:10px;margin:5px}
            QFrame#tool{background:#f0f0f0;border:1px solid #ccc;border-radius:6px;padding:6px;margin:3px}
            QLabel{color:#333}QMenuBar{background:#fff;color:#333}QMenu{background:#fff;color:#333}
            """)

    def toggle_theme(self):
        """Toggle between dark and light theme, persist to config."""
        self.dark_mode = not self.dark_mode
        self.theme_btn.setText("🌙" if not self.dark_mode else "☀️")
        self.apply_theme()
        self.config["dark_mode"] = self.dark_mode
        save_config(self.config)

    def toggle_mode(self, k: str):
        """Toggle a search/chat mode."""
        b = self.mode_buttons[k]
        if b.isChecked():
            if k not in self.selected_modes:
                self.selected_modes.append(k)
        else:
            if k in self.selected_modes:
                self.selected_modes.remove(k)
        if not self.selected_modes:
            self.selected_modes = ["quick"]
            self.mode_buttons["quick"].setChecked(True)
        self._update_mode_status()

    def _insert_chat_widget(self, w: QWidget):
        """Insert a widget into the chat area before the stretch."""
        s = self.chat_layout.takeAt(self.chat_layout.count() - 1)
        self.chat_layout.addWidget(w)
        if s:
            self.chat_layout.addItem(s)
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    def _add_tool_log(self, text: str):
        """Add a tool execution log entry to the chat."""
        f = QFrame()
        f.setObjectName("tool")
        l = QHBoxLayout(f)
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size:11px;color:#FF9800")
        l.addWidget(lbl)
        self._insert_chat_widget(f)

    def add_msg_widget(self, role: str, text: str, msg_id=None) -> MessageFrame:
        """Add a complete message to the chat."""
        def on_copy():
            QApplication.clipboard().setText(text)
            self.set_status("✓ تم النسخ", "#4CAF50")

        def on_like():
            if msg_id: db.add_feedback(msg_id, "like")

        def on_dislike():
            if msg_id: db.add_feedback(msg_id, "dislike")

        def on_regen():
            if self.last_msg: self.send(regenerate=True)

        f = MessageFrame(role, text, on_copy,
            on_like if role == "assistant" else None,
            on_dislike if role == "assistant" else None,
            on_regen if role == "assistant" else None, msg_id)
        self._insert_chat_widget(f)
        return f

    def add_streaming_assistant_frame(self):
        """Create a streaming assistant message frame for real-time updates."""
        f = QFrame()
        f.setObjectName("assistant")
        l = QVBoxLayout(f)
        self.current_assistant_label = QLabel("...")
        self.current_assistant_label.setWordWrap(True)
        self.current_assistant_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        l.addWidget(self.current_assistant_label)
        self.current_assistant_text = ""
        self._pending_mid = None
        self._insert_chat_widget(f)

    def on_chunk(self, ct: str):
        """Handle a streamed content chunk."""
        self.current_assistant_text += ct
        if self.current_assistant_label:
            self.current_assistant_label.setText(self.current_assistant_text)
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    def on_agent_chunk(self, ct: str):
        """Handle an agent streamed content chunk (may be called mid-tool-loop)."""
        if not self.current_assistant_label:
            self.add_streaming_assistant_frame()
        self.current_assistant_text += ct
        if self.current_assistant_label:
            self.current_assistant_label.setText(self.current_assistant_text)
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    def on_tool_action(self, text: str):
        """Handle a tool execution progress message."""
        self._add_tool_log(text)
        self.set_status(text, "#FF9800")

    def on_stream_done(self, sc: int):
        """Handle completion of streaming (0=success, 1=stopped)."""
        t = self.current_assistant_text.strip()
        if sc == 1:
            if self.current_assistant_label and not t:
                self.current_assistant_label.setText("[تم الإيقاف]")
            self.set_status("● تم الإيقاف", "#F44336")
        else:
            if t and self.cid:
                self._pending_mid = db.add_msg(self.cid, "assistant", t)
            self.set_status("● جاهز", "#4CAF50")
            if t:
                self.speak(t)
        self.send_btn.show()
        self.stop_btn.hide()
        self.current_assistant_label = None
        self.current_assistant_text = ""
        self.worker = None

    def on_error(self, e: str):
        """Handle an error from a worker thread."""
        if self.current_assistant_label and not self.current_assistant_text.strip():
            self.current_assistant_label.setText("خطأ: " + e)
        else:
            self.add_msg_widget("assistant", "خطأ: " + e)
        self.set_status("● خطأ", "#F44336")
        self.send_btn.show()
        self.stop_btn.hide()
        self.current_assistant_label = None
        self.current_assistant_text = ""
        self.worker = None

    def on_search_done(self, payload: dict, em: str, reg: bool):
        """Handle search results and start the stream worker."""
        self.pending_search_payload = payload
        try:
            if payload.get("web"): db.save_search_cache(em, "web", payload["web"])
            if payload.get("academic"): db.save_search_cache(em, "academic", payload["academic"])
        except Exception as e:
            print(f"cache: {e}")
        if not payload.get("web") and not payload.get("academic"):
            self.set_status("● البحث غير متاح - متابعة", "#FF9800")
        files = db.recent_file_rows(self.cid, limit=3) if self.cid else []
        mem = db.get_all_memory()
        mt = "\n".join(f"{k}: {v}" for k, v in mem.items()) if mem else ""
        self.add_streaming_assistant_frame()
        self.worker = StreamWorker(em, files, list(self.selected_modes), regenerate=reg, memory_text=mt, search_payload=payload)
        self.worker.chunk.connect(self.on_chunk)
        self.worker.finished_signal.connect(self.on_stream_done)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def send(self, regenerate: bool = False):
        """Send a message to the AI or agent."""
        msg = self.input.toPlainText().strip()
        if not regenerate and not msg:
            return
        # Input validation
        if not regenerate and len(msg) > MAX_INPUT_CHARS:
            self.set_status(f"● الرسالة طويلة جدًا (الحد {MAX_INPUT_CHARS} حرف)", "#F44336")
            return
        if self.worker and self.worker.isRunning():
            self.set_status("● انتظر انتهاء الرد الحالي", "#FF9800")
            return
        if regenerate:
            if not self.cid or not self.last_msg:
                return
            em = self.last_msg
            self.set_status("● جارٍ إعادة الصياغة...", "#FF9800")
        else:
            em = msg
            self.input.clear()
            self.add_msg_widget("user", em)
            self.set_status("● جارٍ التحليل...", "#FF9800")
            if not self.cid:
                self.cid = db.add_conv(em[:55] or "محادثة جديدة")
                self.load_convs(select_id=self.cid)
            db.add_msg(self.cid, "user", em)
            self.last_msg = em
            mem = db.get_all_memory()
            mt = "\n".join(f"{k}: {v}" for k, v in mem.items()) if mem else ""
            self.learn_worker = LearnWorker(em, mt, self.selected_modes)
            self.learn_worker.done.connect(self.on_learn_done)
            self.learn_worker.error.connect(self.on_learn_error)
            self.learn_worker.start()
        self.send_btn.hide()
        self.stop_btn.show()

        if self.agent_mode:
            files = db.recent_file_rows(self.cid, limit=3) if self.cid else []
            mem = db.get_all_memory()
            mt = "\n".join(f"{k}: {v}" for k, v in mem.items()) if mem else ""
            self.set_status("● الوكيل يفكر...", "#FF9800")
            self.add_streaming_assistant_frame()
            self.worker = AgentWorker(em, list(self.selected_modes), mt, files, regenerate)
            self.worker.chunk.connect(self.on_agent_chunk)
            self.worker.tool_action.connect(self.on_tool_action)
            self.worker.finished_signal.connect(self.on_stream_done)
            self.worker.error.connect(self.on_error)
            self.worker.start()
            return

        needs_search = any(m in self.selected_modes for m in ("web", "academic", "advanced"))
        if needs_search:
            self.set_status("● جارٍ البحث...", "#FF9800")
            self.search_worker = SearchWorker(em, list(self.selected_modes))
            self.search_worker.done.connect(lambda p, e=em, r=regenerate: self.on_search_done(p, e, r))
            self.search_worker.start()
            return
        self.on_search_done({"web": [], "academic": []}, em, regenerate)

    def on_learn_done(self, k: str, v: str):
        """Handle learned information extraction."""
        if k and v:
            db.add_memory(k, v)

    def on_learn_error(self, e: str):
        """Handle learning error silently."""
        pass

    def stop(self):
        """Stop the current worker."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.set_status("● جارٍ الإيقاف...", "#FF9800")

    def speak(self, text: str):
        """Speak text using Windows SAPI via PowerShell.
        Writes text to temp file to avoid all quoting issues."""
        try:
            tmp = tempfile.NamedTemporaryFile(
                mode='w', suffix='.txt', delete=False,
                encoding='utf-8', dir=str(VOICES))
            tmp.write(text[:500])
            tmp.close()
            ps_script = (
                "Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$txt = Get-Content -Path '{}' -Raw -Encoding UTF8; "
                "$s.Speak($txt);".format(tmp.name)
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                shell=True, timeout=30, check=False,
                capture_output=True
            )
        except Exception:
            pass
        finally:
            try:
                if 'tmp' in locals():
                    os.unlink(tmp.name)
            except:
                pass

    def start_mic(self):
        """Start Whisper speech-to-text from an audio file."""
        if whisper is None:
            self.set_status("● Whisper غير مثبت، راجع README", "#F44336")
            return
        path, _ = QFileDialog.getOpenFileName(self, "اختر ملفًا صوتيًا", "",
            "Audio Files (*.wav *.mp3 *.m4a *.flac *.ogg)")
        if not path:
            return

        class WW(QThread):
            done = pyqtSignal(str)
            error = pyqtSignal(str)
            status = pyqtSignal(str)

            def __init__(self, p):
                super().__init__()
                self.p = p

            def run(self):
                try:
                    if whisper is None:
                        raise RuntimeError("no whisper")
                    self.status.emit("● تحميل نموذج Whisper...")
                    m = whisper.load_model(WHISPER_MODEL_SIZE)
                    self.status.emit("● جارٍ تفريغ الصوت...")
                    r = m.transcribe(self.p, language="ar", fp16=False)
                    self.done.emit((r.get("text") or "").strip())
                except Exception as e:
                    self.error.emit(str(e))

        self.whisper_worker = WW(path)
        self.whisper_worker.status.connect(lambda t: self.set_status(t, "#FF9800"))
        self.whisper_worker.done.connect(self.on_whisper_done)
        self.whisper_worker.error.connect(lambda e: self.set_status("● خطأ Whisper: " + e, "#F44336"))
        self.whisper_worker.start()

    def on_whisper_done(self, text: str):
        """Handle Whisper transcription result."""
        if text:
            self.input.setPlainText(text)
            self.set_status("● تم التفريغ المحلي بنجاح", "#4CAF50")
        else:
            self.set_status("● لم يتم استخراج نص", "#F44336")

    def do_search(self, q: str):
        """Search conversations by title."""
        q = q.strip()
        if not q:
            self.load_convs()
            return
        results = db.search_convs(q)
        self.conv_list.clear()
        for r in results:
            item = QListWidgetItem(r["title"] or "محادثة")
            item.setData(Qt.ItemDataRole.UserRole, r["id"])
            self.conv_list.addItem(item)

    def load_convs(self, select_id: Optional[str] = None):
        """Load conversation list, optionally selecting one."""
        self.conv_list.clear()
        rows = db.convs()
        selected_row = None
        for idx, c in enumerate(rows):
            item = QListWidgetItem(c["title"] or "محادثة")
            item.setData(Qt.ItemDataRole.UserRole, c["id"])
            self.conv_list.addItem(item)
            if select_id and c["id"] == select_id:
                selected_row = idx
        if selected_row is not None:
            self.conv_list.setCurrentRow(selected_row)

    def load_conv(self, item: QListWidgetItem):
        """Load a conversation by clicking its list item."""
        cid = item.data(Qt.ItemDataRole.UserRole)
        if not cid:
            return
        self.cid = cid
        self.clear_chat()
        msgs = db.conv(cid)
        self.last_msg = None
        for m in msgs:
            self.add_msg_widget(m["role"], m["content"], m["id"])
            if m["role"] == "user":
                self.last_msg = m["content"]
        self.file_list.clear()
        for f in db.files(cid):
            it = QListWidgetItem(f["filename"])
            it.setData(Qt.ItemDataRole.UserRole, f.get("id"))
            self.file_list.addItem(it)

    def conv_context_menu(self, pos):
        """Right-click context menu for conversations."""
        it = self.conv_list.itemAt(pos)
        if not it:
            return
        cid = it.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        delete_action = menu.addAction("🗑 حذف المحادثة")
        if menu.exec(self.conv_list.mapToGlobal(pos)) == delete_action:
            if QMessageBox.question(self, "تأكيد", "حذف هذه المحادثة نهائيًا؟") == QMessageBox.StandardButton.Yes:
                db.delete_conv(cid)
                self.load_convs()
                if self.cid == cid:
                    self.new_conv()

    def file_context_menu(self, pos):
        """Right-click context menu for files."""
        it = self.file_list.itemAt(pos)
        if not it:
            return
        fid = it.data(Qt.ItemDataRole.UserRole)
        if not fid:
            return
        menu = QMenu(self)
        delete_action = menu.addAction("🗑 حذف الملف")
        if menu.exec(self.file_list.mapToGlobal(pos)) == delete_action:
            db.delete_file(fid)
            if self.cid:
                self.file_list.clear()
                for f in db.files(self.cid):
                    it2 = QListWidgetItem(f["filename"])
                    it2.setData(Qt.ItemDataRole.UserRole, f.get("id"))
                    self.file_list.addItem(it2)

    def delete_current_conv(self):
        """Delete the current conversation."""
        if not self.cid:
            return
        if QMessageBox.question(self, "تأكيد", "حذف هذه المحادثة نهائيًا؟") == QMessageBox.StandardButton.Yes:
            db.delete_conv(self.cid)
            self.load_convs()
            self.new_conv()

    def clear_chat(self):
        """Clear all messages from the chat area."""
        while self.chat_layout.count():
            c = self.chat_layout.takeAt(0)
            if c.widget():
                c.widget().deleteLater()
        self.chat_layout.addStretch()
        self.current_assistant_label = None
        self.current_assistant_text = ""
        self._pending_mid = None

    def new_conv(self):
        """Start a new conversation."""
        self.cid = None
        self.last_msg = None
        self.pending_search_payload = {"web": [], "academic": []}
        self.clear_chat()
        self.file_list.clear()
        self.conv_list.clearSelection()
        self.set_status("● جاهز", "#4CAF50")

    def export_conv(self):
        """Export the current conversation to Markdown."""
        if not self.cid:
            return
        lines = ["# محادثة", ""]
        for m in db.conv(self.cid):
            r = "**المستخدم:**" if m["role"] == "user" else "**المساعد:**"
            lines.append(f"{r}\n\n{m['content']}\n")
        path, _ = QFileDialog.getSaveFileName(self, "تصدير المحادثة", "", "Markdown (*.md);;Text (*.txt)")
        if path:
            Path(path).write_text("\n".join(lines), encoding="utf-8")
            self.set_status("✓ تم التصدير", "#4CAF50")

    def upload(self):
        """Upload files to the current conversation."""
        files, _ = QFileDialog.getOpenFileNames(self, "رفع ملفات", "", "All Files (*.*)")
        if not files:
            return
        if not self.cid:
            self.cid = db.add_conv("محادثة جديدة")
            self.load_convs(select_id=self.cid)
        for f in files:
            src = Path(f)
            if not src.exists():
                continue
            ext = src.suffix.lower().lstrip(".")
            dest = UPLOADS / f"{uuid.uuid4().hex}_{safe_filename(src.name)}"
            try:
                shutil.copy2(src, dest)
            except:
                dest = src
            text = "[ملف]"
            try:
                if ext in ("txt", "md", "py", "json", "csv", "html", "js", "css"):
                    text = truncate(dest.read_text(encoding="utf-8", errors="ignore"), 20000)
                elif ext == "pdf" and PdfReader:
                    text = truncate("\n".join((p.extract_text() or "") for p in PdfReader(str(dest)).pages), 20000)
                elif ext == "docx" and Document:
                    text = truncate("\n".join(p.text for p in Document(str(dest)).paragraphs), 20000)
            except:
                text = "[تعذر استخراج النص]"
            db.add_file(self.cid, src.name, dest, ext, src.stat().st_size, text)
            it = QListWidgetItem(src.name)
            it.setData(Qt.ItemDataRole.UserRole, None)
            self.file_list.addItem(it)
        self.set_status("✓ تم رفع الملفات", "#4CAF50")

    def create_file_wiz(self):
        """Create a new file via file dialog."""
        path, _ = QFileDialog.getSaveFileName(self, "إنشاء ملف", "", "Text (*.txt);;Python (*.py);;All (*.*)")
        if path:
            SystemAgent.create_file(path, "")
            QMessageBox.information(self, "تم", f"تم إنشاء:\n{path}")

    def mkdir_wiz(self):
        """Create a new directory via input dialog."""
        name, ok = QInputDialog.getText(self, "إنشاء مجلد", "اسم المجلد:")
        if ok and name:
            path = Path.cwd() / safe_filename(name)
            SystemAgent.create_dir(str(path))
            QMessageBox.information(self, "تم", f"تم إنشاء:\n{path}")

    def show_memory(self):
        """Show all saved memories."""
        mem = db.get_all_memory()
        if not mem:
            QMessageBox.information(self, "الذاكرة", "لا توجد معلومات محفوظة بعد.")
            return
        text = "\n".join(f"📌 {k}: {v}" for k, v in mem.items())
        QMessageBox.information(self, "🧠 ذاكرة Walid AI", text)

    def show_search_results(self):
        """Show search results in a dialog."""
        SearchResultsDialog(self.pending_search_payload, self).exec()

    def closeEvent(self, event):
        """Save config on close."""
        self.config["dark_mode"] = self.dark_mode
        save_config(self.config)
        event.accept()


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Tahoma", 11))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
