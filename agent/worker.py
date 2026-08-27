"""Agent, Stream, Search, and Learn workers (QThread-based)."""
from __future__ import annotations
import json, re, sqlite3, traceback
from datetime import datetime
from typing import Optional

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from core.config import (
    DEFAULT_MODEL, MODE_PROMPTS, NUM_CTX, OLLAMA_URL,
    OLLAMA_RETRY_COUNT, OLLAMA_TIMEOUT, MAX_AGENT_ITERATIONS,
)
from core.utils import truncate
from search.engine import SearchEngine
from tools.registry import AGENT_TOOLS, execute_tool
from agent.prompts import SYSTEM_PROMPT_AGENT, SYSTEM_PROMPT_CHAT


class AgentWorker(QThread):
    """Streaming agent loop with Ollama tool calling.

    Pattern:
    1. Stream model response (content + tool_calls accumulated)
    2. If tool_calls found, execute them locally
    3. Feed results back to model
    4. Repeat until no tool_calls or max iterations
    5. Stream final content to UI
    """
    chunk = pyqtSignal(str)
    tool_action = pyqtSignal(str)
    confirm_tool = pyqtSignal(str, str)
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

    def stop(self):
        self._stop = True

    def _get_db(self) -> sqlite3.Connection:
        from core.config import DB_PATH
        if self._local_db is None:
            self._local_db = sqlite3.connect(DB_PATH)
            self._local_db.row_factory = sqlite3.Row
        return self._local_db

    def run(self):
        try:
            messages = self._build_messages()
            for iteration in range(MAX_AGENT_ITERATIONS):
                if self._stop:
                    self.finished_signal.emit(1)
                    return
                self.tool_action.emit(f"● خطوة {iteration+1}/{MAX_AGENT_ITERATIONS}: تفكير...")
                content, tool_calls = self._stream_response(messages)
                if content:
                    self.chunk.emit(content)
                if not tool_calls:
                    self.finished_signal.emit(0)
                    return
                messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})
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
                        except Exception:
                            args = {}
                    else:
                        args = args_raw
                    self.tool_action.emit(f"● تنفيذ: {name}({json.dumps(args, ensure_ascii=False)[:100]})")
                    result = execute_tool(name, args)
                    summary = str(result)[:200] if result else "(empty)"
                    self.tool_action.emit(f"✓ {name}: {summary}")
                    messages.append({"role": "tool", "content": str(result)})
            self.chunk.emit("\n[تم الوصول للحد الأقصى من الخطوات]")
            self.finished_signal.emit(0)
        except Exception as e:
            self.error.emit(f"Agent: {e}\n{traceback.format_exc()[-200:]}")

    def _stream_response(self, messages: list) -> tuple:
        content = ""
        tool_calls = []
        for attempt in range(OLLAMA_RETRY_COUNT + 1):
            try:
                response = requests.post(OLLAMA_URL, json={
                    "model": DEFAULT_MODEL,
                    "messages": messages,
                    "tools": AGENT_TOOLS,
                    "stream": True,
                    "options": {"num_ctx": NUM_CTX},
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
            except Exception:
                continue
            msg = data.get("message", {})
            c = msg.get("content", "")
            if c:
                content += c
                self.chunk.emit(c)
            tc = msg.get("tool_calls")
            if tc:
                tool_calls.extend(tc)
            if data.get("done", False):
                break
        response.close()
        return content, tool_calls

    def _build_messages(self) -> list:
        mode_parts = [MODE_PROMPTS[m] for m in self.selected_modes if m in MODE_PROMPTS]
        sys_prompt = SYSTEM_PROMPT_AGENT
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


class StreamWorker(QThread):
    """Streaming chat from Ollama without tool calling."""
    chunk = pyqtSignal(str)
    finished_signal = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, msg: str, files: list, selected_modes: list,
                 regenerate: bool = False, memory_text: str = "", search_payload: dict = None):
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
        except Exception:
            pass

    def run(self):
        try:
            ctx = "\n\n".join(
                f"ملف: {f['filename']}\n{truncate(f.get('extracted_text') or '', 7000)}"
                for f in self.files if f.get("extracted_text"))
            mp = [MODE_PROMPTS[m] for m in self.selected_modes if m in MODE_PROMPTS]
            p = SYSTEM_PROMPT_CHAT
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
                        "model": DEFAULT_MODEL,
                        "stream": True,
                        "messages": [{"role": "system", "content": p},
                                      {"role": "user", "content": self.msg}],
                        "options": {"num_ctx": NUM_CTX},
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
                except Exception:
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
            except Exception:
                pass


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
            p = f"حلل ({ms}). JSON: {{\"key\":\"\",\"value\":\"\",\"key\":\"عنوان\",\"value\":\"معلومة\"}}."
            if self.mem:
                p += "\n" + self.mem
            r = requests.post(OLLAMA_URL, json={
                "model": DEFAULT_MODEL,
                "stream": False,
                "messages": [{"role": "system", "content": p},
                              {"role": "user", "content": self.msg}],
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
