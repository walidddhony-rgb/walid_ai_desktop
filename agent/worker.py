import json
import re
import traceback

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from core.agents_md import read_agents_md
from core.config import DB_PATH, DEFAULT_MODEL, MODE_PROMPTS, NUM_CTX, OLLAMA_URL, TOP_K_RAG
from core.context_compaction import auto_compact_if_needed, estimate_tokens
from core.hooks import run_event_hooks
from core.skills import discover_skills, format_skills_index
from db.database import Database
from db.embeddings import retrieve_relevant_chunks
from tools.registry import AGENT_TOOLS, execute_tool, set_exec_callback, set_subagent_callbacks


def has_chinese(text):
    if not text:
        return False
    chinese_range = range(0x4E00, 0x9FFF + 1)
    return any(ord(c) in chinese_range for c in text)


def has_chinese_in_code(code):
    if not code:
        return False
    for line in code.split("\n"):
        if line.strip().startswith("#"):
            if has_chinese(line):
                return True
    return False


BANNED_FACTS = {
    "python",
    "shell",
    "javascript",
    "code",
    "use os",
    "count files",
    "project evaluation",
    "code review",
    "bug checking",
    "facts",
    "summary",
    "حقائق قصيرة",
    "متابعة",
    "النص بالعربية",
    "عدد الحقائق",
    "yes continue",
    "following",
    "okay continue",
    "yes",
    "no",
    "continue",
    "proceed",
    "file",
    "files",
    "directory",
    "looking for results",
    "seeking",
    "searching",
    "has not searched",
    "problem-solving skills",
    "precise searching",
    "folders",
    "results",
    "user uses",
    "user prefers",
    "user aims",
    "user has",
    "user wants",
    "user is",
    "prefers python",
    "python files counting",
    "space folder",
    "aims for",
    "two subordinates",
}
BANNED_PREFIXES = [
    "the user wants",
    "user wants",
    "user plans",
    "the script will",
    "script will",
    "this script will",
    "this script",
    "the user is",
    "user is",
    "the code will",
    "code will",
    "the agent will",
    "agent will",
    "this folder",
    "this directory",
    "the folder",
    "the directory",
    "this file",
    "the file",
    "there are",
    "there is",
    "the user asked",
    "user asked",
    "the workspace",
    "the project",
    "a script",
    "the script",
    "a python",
    "the python",
    "this code",
    "the code",
    "this message",
    "the message",
    "the user is working",
    "user is working",
    "this indicates",
    "the message indicates",
    "this user",
    "the user has",
    "the user's",
    "user's",
    "uses two",
    "the user uses",
    "looking for",
    "seeking",
    "has not",
    "searching for",
    "user needs",
    "needs problem",
    "needs to",
    "is looking",
    "is searching",
    "is trying",
    "is working",
    "is counting",
    "is using",
    "wants to",
    "is attempting",
    "user prefers",
    "user aims",
    "user has space",
    "prefers python",
    "python files",
    "space folder",
    "two subordinates",
    "one for counting",
    "another for",
    "user uses two",
]
MAX_LOOPS = 15
COMPACTION_THRESHOLD = 24000
MAIN_AGENT_TIMEOUT = 600


class AgentWorker(QThread):
    chunk = pyqtSignal(str)
    tool_action = pyqtSignal(str, str)
    code_execution = pyqtSignal(str, str)
    step_started = pyqtSignal(int)
    compaction_triggered = pyqtSignal(str)
    hook_triggered = pyqtSignal(str, str)
    learned_fact = pyqtSignal(str)
    subagent_waiting = pyqtSignal(str)
    finished_signal = pyqtSignal(int)
    cancelled = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        msg,
        selected_modes,
        memory_text,
        files=None,
        cid="",
        auto_learn=True,
        workspace_path="",
        exec_callback=None,
        spawn_callback=None,
        results_callback=None,
        wait_callback=None,
    ):
        super().__init__()
        self.msg = msg
        self.selected_modes = selected_modes
        self.memory_text = memory_text
        self.files = files or []
        self.cid = cid
        self.auto_learn = auto_learn
        self.workspace_path = workspace_path
        self._stop = False
        self._prev_code = ""
        self._got_subagent_results = False
        if exec_callback:
            set_exec_callback(exec_callback)
        if spawn_callback and results_callback:
            set_subagent_callbacks(spawn_callback, results_callback)
        self.wait_callback = wait_callback

    def stop(self):
        self._stop = True

    def run(self):
        try:
            for hr in run_event_hooks(
                "SessionStart", {"workspace_path": self.workspace_path}, self.workspace_path
            ):
                if hr["message"]:
                    self.hook_triggered.emit("SessionStart", hr["message"])
            for hr in run_event_hooks(
                "UserPromptSubmit",
                {"user_message": self.msg, "workspace_path": self.workspace_path},
                self.workspace_path,
            ):
                if not hr["approved"]:
                    self.chunk.emit("تم حظر الرسالة بواسطة خطاف: " + hr["message"])
                    self.finished_signal.emit(1)
                    return
                if hr["message"]:
                    self.hook_triggered.emit("UserPromptSubmit", hr["message"])

            conversation = self._build_initial_messages()
            for step in range(1, MAX_LOOPS + 1):
                if self._stop:
                    self.cancelled.emit("تم إلغاء الرد الجاري.")
                    return
                self.step_started.emit(step)
                compacted, did_compact = auto_compact_if_needed(conversation, COMPACTION_THRESHOLD)
                if did_compact:
                    self.compaction_triggered.emit(
                        "ضغط السياق: "
                        + str(estimate_tokens(conversation))
                        + " -> "
                        + str(estimate_tokens(compacted))
                        + " رمز"
                    )
                    conversation = compacted

                if self.wait_callback:
                    should_wait = self.wait_callback()
                    if should_wait:
                        self.subagent_waiting.emit("في انتظار اكتمال الوكلاء الفرعيين...")
                        self.wait_callback_blocking()
                        self.subagent_waiting.emit("اكتمل جميع الوكلاء الفرعيين.")

                response_data = self._call_ollama(conversation)
                if not response_data:
                    break
                assistant_content = response_data.get("content", "")
                tool_calls = response_data.get("tool_calls", [])

                if assistant_content and has_chinese(assistant_content):
                    conversation.append({"role": "assistant", "content": assistant_content})
                    conversation.append(
                        {
                            "role": "user",
                            "content": (
                                "Your previous response contained Chinese text which is NOT allowed. "
                                "Rewrite your response in Arabic or English only. "
                                "NEVER use Chinese characters. Give your answer again."
                            ),
                        }
                    )
                    continue

                if assistant_content:
                    self.chunk.emit(assistant_content)
                    conversation.append({"role": "assistant", "content": assistant_content})
                if tool_calls:
                    conversation.append(
                        {
                            "role": "assistant",
                            "content": assistant_content,
                            "tool_calls": tool_calls,
                        }
                    )
                if not tool_calls:
                    break
                for tc in tool_calls:
                    if self._stop:
                        self.cancelled.emit("تم إلغاء الرد الجاري.")
                        return
                    func = tc.get("function", {})
                    name = func.get("name", "")
                    args_raw = func.get("arguments", "{}")
                    args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw

                    if name == "get_subagent_results":
                        self._got_subagent_results = True

                    if self._got_subagent_results and name == "exec":
                        self.tool_action.emit(
                            "exec", "Blocked: already have subagent results. Summarize instead."
                        )
                        conversation.append(
                            {
                                "role": "tool",
                                "name": name,
                                "content": "BLOCKED: You already received subagent results. Do NOT run more code. Give your final summary in Arabic now.",
                            }
                        )
                        continue

                    hook_ctx = {
                        "tool_name": name,
                        "tool_args": args,
                        "workspace_path": self.workspace_path,
                    }
                    blocked = False
                    for hr in run_event_hooks("PreToolUse", hook_ctx, self.workspace_path):
                        if not hr["approved"]:
                            blocked = True
                            self.hook_triggered.emit(
                                "PreToolUse", "Blocked " + name + ": " + hr["message"]
                            )
                            conversation.append(
                                {"role": "tool", "name": name, "content": "Blocked by hook"}
                            )
                            break
                        if hr["message"]:
                            self.hook_triggered.emit("PreToolUse", hr["message"])
                    if blocked:
                        continue
                    if name == "exec":
                        code = args.get("code", "")
                        if code == self._prev_code:
                            self.tool_action.emit("exec", "Duplicate code, stopping.")
                            conversation.append(
                                {"role": "tool", "name": name, "content": "Duplicate code."}
                            )
                            break
                        if has_chinese_in_code(code):
                            self.tool_action.emit("exec", "Blocked: Chinese comments detected.")
                            conversation.append(
                                {
                                    "role": "tool",
                                    "name": name,
                                    "content": "BLOCKED: Your code contains Chinese comments. Rewrite with English comments only.",
                                }
                            )
                            continue
                        self._prev_code = code
                        self.code_execution.emit(args.get("language", "python"), code)
                    result = execute_tool(name, args)
                    self.tool_action.emit(name, str(result)[:500])
                    conversation.append(
                        {"role": "tool", "name": name, "content": str(result)[:2000]}
                    )
                    post_ctx = {
                        "tool_name": name,
                        "tool_args": args,
                        "tool_result": result,
                        "workspace_path": self.workspace_path,
                    }
                    for hr in run_event_hooks("PostToolUse", post_ctx, self.workspace_path):
                        if hr["message"]:
                            self.hook_triggered.emit("PostToolUse", hr["message"])
                else:
                    continue
                break
            if self.auto_learn and not self._stop:
                self._extract_facts()
            run_event_hooks(
                "SessionStop", {"workspace_path": self.workspace_path}, self.workspace_path
            )
            self.finished_signal.emit(0)
        except Exception as e:
            self.error.emit("Agent: " + str(e) + "\n" + traceback.format_exc()[-500:])

    def wait_callback_blocking(self):
        import time as _time

        start = _time.time()
        while self.wait_callback():
            if self._stop:
                break
            if _time.time() - start > 120:
                break
            _time.sleep(1)

    def _call_ollama(self, conversation):
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": DEFAULT_MODEL,
                "messages": conversation,
                "tools": AGENT_TOOLS,
                "stream": False,
                "options": {"num_ctx": NUM_CTX},
            },
            timeout=(10, MAIN_AGENT_TIMEOUT),
        )
        response.raise_for_status()
        msg = response.json().get("message", {})
        return {"content": msg.get("content", ""), "tool_calls": msg.get("tool_calls", [])}

    def _build_initial_messages(self):
        return [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": self.msg},
        ]

    def _build_system_prompt(self):
        parts = []
        parts.append(
            "You are Walid AI Desktop, an elite autonomous coding agent that runs code on the user's machine."
        )
        parts.append(
            "You have exec(). You MUST use it to write and run Python, Shell, or JavaScript code."
        )
        parts.append("NEVER just describe. ALWAYS write and execute actual code via exec().")
        parts.append("MANDATORY: Every Python script MUST end with print() showing the result.")
        parts.append(
            "Use English in print() statements, variable names, AND comments. NEVER use Chinese comments."
        )
        parts.append("MULTI-STEP: Call exec() multiple times until the task is complete.")
        parts.append("STOP: If code already ran successfully, give a final summary in Arabic.")
        parts.append("NEVER repeat the same code twice.")
        parts.append(
            "FILE SEARCHING: When counting or searching files, ALWAYS use os.walk() to search RECURSIVELY through ALL subdirectories. NEVER use os.listdir() — it only searches the top directory."
        )
        parts.append(
            "SINGLE EXEC: Put ALL your code in ONE exec() call. Do NOT define functions in one exec() and call them in another — variables do NOT persist between calls. Each exec() is a completely separate process."
        )
        parts.append(
            "FILE EDITING: Use create_file or edit_file. User sees diff review before changes."
        )
        parts.append(
            "SUBAGENTS: Use spawn_subagent for parallel tasks. Use get_subagent_results to collect results."
        )
        parts.append(
            "CRITICAL: After get_subagent_results returns status 'done', SUMMARIZE the results immediately in Arabic. Do NOT call exec() or any other tool to repeat the same task. The subagents already did the work. Just present their findings."
        )
        parts.append(
            "CRITICAL LANGUAGE RULE: You MUST respond in Arabic or English only. NEVER use Chinese or any other language. This includes code comments — use English only."
        )
        parts.append("Your working directory: " + self.workspace_path)
        parts.append("CRITICAL: Do NOT hardcode Windows paths. Use '.' or os.getcwd().")
        mode_parts = [MODE_PROMPTS[m] for m in self.selected_modes if m in MODE_PROMPTS]
        if mode_parts:
            parts.append("Modes: " + " | ".join(mode_parts))
        if self.memory_text:
            parts.append("Saved memory:\n" + self.memory_text)
        if "rag" in self.selected_modes:
            chunks = retrieve_relevant_chunks(self.msg, DB_PATH, top_k=TOP_K_RAG)
            if chunks:
                parts.append("Knowledge:\n" + "\n---\n".join(chunks))
        facts = Database().get_learned_facts(limit=20)
        if facts:
            parts.append("Facts:\n- " + "\n- ".join(facts))
        agents_md = read_agents_md(self.workspace_path)
        if agents_md:
            parts.append("AGENTS.md:\n" + agents_md)
        skills = discover_skills(self.workspace_path)
        if skills:
            parts.append(format_skills_index(skills))
        return "\n\n".join(parts)

    def _extract_facts(self):
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={
                    "model": DEFAULT_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Extract at most 3 useful facts about the USER (not about the task). Focus on: user preferences (e.g. 'prefers dark mode'), user background (e.g. 'is a student'), user goals (e.g. 'learning Python'), user tools (e.g. 'uses VS Code'). Arabic or English only. NEVER Chinese. Minimum 20 chars, 5 words. Do NOT extract facts about file counts, searches, task progress, or what the user did in this session.",
                        },
                        {"role": "user", "content": "User:\n" + self.msg},
                    ],
                    "stream": False,
                    "options": {"num_ctx": 2048, "temperature": 0.2},
                },
                timeout=60,
            )
            resp.raise_for_status()
            facts_text = resp.json().get("message", {}).get("content", "")
            db = Database()
            for line in facts_text.strip().split("\n"):
                fact = line.strip().lstrip("-*1234567890. ").strip()
                if self._is_allowed_fact(fact):
                    db.add_learned_fact(self.cid, fact)
                    self.learned_fact.emit(fact)
        except Exception:
            pass

    def _is_allowed_fact(self, fact):
        if not fact or len(fact) < 20:
            return False
        if len(fact.split()) < 5:
            return False
        if has_chinese(fact):
            return False
        lowered = fact.strip().lower()
        if lowered in BANNED_FACTS:
            return False
        for b in BANNED_FACTS:
            if lowered == b or lowered.startswith(b):
                return False
        for p in BANNED_PREFIXES:
            if lowered.startswith(p):
                return False
        pattern = re.compile(
            r"^[A-Za-z0-9\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\s.,:;!?_\-\'()\[\]/]+$"
        )
        if not pattern.match(fact):
            return False
        return re.search(r"[A-Za-z\u0600-\u06FF]", fact) is not None
