import json
import re
import traceback
import requests
from PyQt6.QtCore import QThread, pyqtSignal

from core.config import DEFAULT_MODEL, MODE_PROMPTS, NUM_CTX, OLLAMA_URL, TOP_K_RAG, DB_PATH
from tools.registry import AGENT_TOOLS, execute_tool, set_exec_callback
from db.embeddings import retrieve_relevant_chunks
from db.database import Database
from core.agents_md import read_agents_md
from core.skills import discover_skills, format_skills_index

BANNED_FACTS = {
    "python", "shell", "javascript", "code", "use os", "count files",
    "project evaluation", "code review", "bug checking", "facts",
    "summary", "حقائق قصيرة", "متابعة", "النص بالعربية", "عدد الحقائق",
    "yes continue", "following", "okay continue", "yes", "no",
    "continue", "proceed", "file", "files", "directory",
}

BANNED_PREFIXES = [
    "the user wants", "user wants", "user plans",
    "the script will", "script will", "this script will",
    "this script", "the user is", "user is",
    "the code will", "code will",
    "the agent will", "agent will",
    "this folder", "this directory",
    "the folder", "the directory",
    "this file", "the file",
    "there are", "there is",
    "the user asked", "user asked",
    "the workspace", "the project",
    "a script", "the script",
    "a python", "the python",
    "this code", "the code",
    "this message", "the message",
    "the user is working", "user is working",
    "this indicates", "the message indicates",
    "this user", "the user has",
    "the user's", "user's",
]

MAX_LOOPS = 15


class AgentWorker(QThread):
    chunk = pyqtSignal(str)
    tool_action = pyqtSignal(str, str)
    code_execution = pyqtSignal(str, str)
    step_started = pyqtSignal(int)
    learned_fact = pyqtSignal(str)
    finished_signal = pyqtSignal(int)
    cancelled = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, msg, selected_modes, memory_text, files=None, cid="", auto_learn=True, workspace_path="", exec_callback=None):
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
        if exec_callback:
            set_exec_callback(exec_callback)

    def stop(self):
        self._stop = True

    def run(self):
        try:
            conversation = self._build_initial_messages()
            for step in range(1, MAX_LOOPS + 1):
                if self._stop:
                    self.cancelled.emit("تم إلغاء الرد الجاري.")
                    return
                self.step_started.emit(step)
                response_data = self._call_ollama(conversation)
                if not response_data:
                    break
                assistant_content = response_data.get("content", "")
                tool_calls = response_data.get("tool_calls", [])
                if assistant_content:
                    self.chunk.emit(assistant_content)
                    conversation.append({"role": "assistant", "content": assistant_content})
                if tool_calls:
                    conversation.append({"role": "assistant", "content": assistant_content, "tool_calls": tool_calls})
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
                    if name == "exec":
                        code = args.get("code", "")
                        if code == self._prev_code:
                            self.tool_action.emit("exec", "Duplicate code detected, stopping loop.")
                            conversation.append({"role": "tool", "name": name, "content": "Duplicate code. Task already done."})
                            break
                        self._prev_code = code
                        self.code_execution.emit(args.get("language", "python"), code)
                    result = execute_tool(name, args)
                    self.tool_action.emit(name, str(result)[:500])
                    conversation.append({"role": "tool", "name": name, "content": str(result)[:2000]})
                else:
                    continue
                break
            if self.auto_learn and not self._stop:
                self._extract_facts()
            self.finished_signal.emit(0)
        except Exception as e:
            self.error.emit(f"Agent: {e}\n{traceback.format_exc()[-500:]}")

    def _call_ollama(self, conversation) -> dict:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": DEFAULT_MODEL,
                "messages": conversation,
                "tools": AGENT_TOOLS,
                "stream": False,
                "options": {"num_ctx": NUM_CTX},
            },
            timeout=(10, 300),
        )
        response.raise_for_status()
        data = response.json()
        msg = data.get("message", {})
        return {
            "content": msg.get("content", ""),
            "tool_calls": msg.get("tool_calls", []),
        }

    def _build_initial_messages(self):
        sys_prompt = self._build_system_prompt()
        return [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": self.msg},
        ]

    def _build_system_prompt(self) -> str:
        parts = []

        parts.append(
            "You are Walid AI Desktop, an elite autonomous coding agent that runs code on the user's machine."
        )
        parts.append(
            "You have an exec() function. You MUST use it to write and run Python, Shell, or JavaScript code to accomplish tasks."
        )
        parts.append(
            "NEVER just describe what you would do. ALWAYS write and execute actual code via exec()."
        )
        parts.append(
            "When the user asks for something, write Python code that accomplishes it and call exec() to run it."
        )
        parts.append(
            "Do NOT use list_directory or read_file when you can write Python code to do the same thing more powerfully."
        )
        parts.append(
            "MANDATORY: Every Python script you write MUST end with a print() statement showing the result."
        )
        parts.append(
            "If you compute a value, you MUST print it. Never leave a value unprinted."
        )
        parts.append(
            "IMPORTANT: In print() statements, use English text for labels to avoid encoding issues on Windows."
        )
        parts.append(
            "MULTI-STEP: You can call exec() multiple times. After each execution, read the output "
            "and decide if you need to run more code. Continue until the task is fully complete."
        )
        parts.append(
            "STOP CONDITION: If the code already ran successfully and the output shows the task is done, "
            "do NOT repeat the same code. Instead, give a final summary in Arabic."
        )
        parts.append(
            "NEVER repeat the exact same code twice. If you already executed code and got results, "
            "move on to the next step or give your final summary."
        )
        parts.append(
            "After all code execution is done, ALWAYS give a final text summary of what you accomplished in Arabic."
        )
        parts.append(
            f"Your working directory is already set to: {self.workspace_path}"
        )
        parts.append(
            "CRITICAL: Do NOT hardcode Windows paths with backslashes. "
            "Use '.' or os.getcwd(). The working directory is already set for you. "
            "If you must use a path, use forward slashes like 'C:/Users/folder'."
        )
        parts.append(
            "Respond in Arabic for explanations, but write code and print statements in English."
        )

        mode_parts = [MODE_PROMPTS[m] for m in self.selected_modes if m in MODE_PROMPTS]
        if mode_parts:
            parts.append("Additional modes: " + " | ".join(mode_parts))

        if self.memory_text:
            parts.append("Saved memory:\n" + self.memory_text)

        if "rag" in self.selected_modes:
            chunks = retrieve_relevant_chunks(self.msg, DB_PATH, top_k=TOP_K_RAG)
            if chunks:
                parts.append("Knowledge base excerpts:\n" + "\n---\n".join(chunks))

        facts = Database().get_learned_facts(limit=20)
        if facts:
            parts.append("Previously learned facts:\n- " + "\n- ".join(facts))

        agents_md = read_agents_md(self.workspace_path)
        if agents_md:
            parts.append("AGENTS.md instructions:\n" + agents_md)

        skills = discover_skills(self.workspace_path)
        if skills:
            parts.append(format_skills_index(skills))

        return "\n\n".join(parts)

    def _extract_facts(self):
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "Extract at most 3 useful, specific facts about the user or their environment "
                        "from the user's message only. "
                        "Allowed languages: Arabic or English only. "
                        "Do NOT output: code snippets, language names, single words, "
                        "generic phrases, acknowledgments, or meta-commentary. "
                        "Do NOT describe what the user wants, what a script does, "
                        "what a folder contains, what the code will do, "
                        "what the message indicates, or what the user is working with. "
                        "Only extract concrete personal or environmental facts like: "
                        "the user's name, their OS, their project name, their tech stack, "
                        "their preferences, or their specific data. "
                        "Each fact must be a complete meaningful sentence, minimum 20 characters. "
                        "Reject any fact shorter than 20 characters or containing fewer than 5 words."
                    ),
                },
                {
                    "role": "user",
                    "content": f"User message:\n{self.msg}"
                },
            ]
            resp = requests.post(
                OLLAMA_URL,
                json={
                    "model": DEFAULT_MODEL,
                    "messages": messages,
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

    def _is_allowed_fact(self, fact: str) -> bool:
        if not fact or len(fact) < 20:
            return False

        word_count = len(fact.split())
        if word_count < 5:
            return False

        lowered = fact.strip().lower()

        if lowered in BANNED_FACTS:
            return False

        for banned in BANNED_FACTS:
            if lowered == banned or lowered.startswith(banned):
                return False

        for prefix in BANNED_PREFIXES:
            if lowered.startswith(prefix):
                return False

        allowed_pattern = re.compile(
            r"^[A-Za-z0-9\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\s.,:;!?_\-\'()\[\]/]+$"
        )
        if not allowed_pattern.match(fact):
            return False

        return re.search(r"[A-Za-z\u0600-\u06FF]", fact) is not None
