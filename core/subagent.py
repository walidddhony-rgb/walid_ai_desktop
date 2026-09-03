import json
import re
import time
import traceback
import requests
from PyQt6.QtCore import QThread, pyqtSignal

from core.config import DEFAULT_MODEL, OLLAMA_URL
from tools.registry import AGENT_TOOLS, execute_tool

MAX_SUBAGENTS = 4
SUBAGENT_TIMEOUT = 600


def has_chinese(text):
    if not text:
        return False
    chinese_range = range(0x4E00, 0x9FFF + 1)
    return any(ord(c) in chinese_range for c in text)


def clean_result(text):
    if not text:
        return text
    lines = text.strip().split("\n")
    cleaned = []
    in_code = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if stripped.startswith("def ") or stripped.startswith("import ") or stripped.startswith("from "):
            continue
        if stripped.startswith("#"):
            continue
        cleaned.append(line)
    result = "\n".join(cleaned).strip()
    if has_chinese(result):
        result = re.sub(r"[\u4e00-\u9fff]+", "", result)
        result = re.sub(r"\n{3,}", "\n\n", result)
        result = result.strip()
    return result if result else "No clean result produced."


class SubagentWorker(QThread):
    result_ready = pyqtSignal(str, str)
    step_log = pyqtSignal(str, str)
    error = pyqtSignal(str, str)

    def __init__(self, agent_id, task, workspace_path, mode="worker", max_steps=8):
        super().__init__()
        self.agent_id = agent_id
        self.task = task
        self.workspace_path = workspace_path
        self.mode = mode
        self.max_steps = max_steps
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            self.step_log.emit(self.agent_id, "started: " + self.task[:100])
            messages = self._build_messages()
            last_error = None
            retry_count = 0
            for step in range(1, self.max_steps + 1):
                if self._stop:
                    self.step_log.emit(self.agent_id, "cancelled.")
                    return
                self.step_log.emit(self.agent_id, "step " + str(step))

                if step >= 4:
                    messages.append({
                        "role": "user",
                        "content": (
                            "STOP calling tools. Give your FINAL ANSWER as plain text only. "
                            "Write it in English or Arabic. "
                            "NEVER write in Chinese. "
                            "Do NOT include code blocks. "
                            "Just state the result in 1-2 sentences."
                        )
                    })

                try:
                    use_tools = AGENT_TOOLS if (self.mode == "worker" and step < 4) else []
                    response = requests.post(
                        OLLAMA_URL,
                        json={"model": DEFAULT_MODEL, "messages": messages, "tools": use_tools, "stream": False, "options": {"num_ctx": 8192 if step < 4 else 4096}},
                        timeout=(10, SUBAGENT_TIMEOUT),
                    )
                    response.raise_for_status()
                except requests.exceptions.ReadTimeout:
                    self.step_log.emit(self.agent_id, "timeout, retrying...")
                    retry_count += 1
                    if retry_count >= 2:
                        self.result_ready.emit(self.agent_id, "Task failed after multiple timeouts.")
                        return
                    try:
                        response = requests.post(
                            OLLAMA_URL,
                            json={"model": DEFAULT_MODEL, "messages": messages, "tools": [], "stream": False, "options": {"num_ctx": 4096}},
                            timeout=(10, SUBAGENT_TIMEOUT),
                        )
                        response.raise_for_status()
                    except Exception as e2:
                        self.result_ready.emit(self.agent_id, "Error: " + str(e2)[:200])
                        return
                except Exception as e:
                    self.result_ready.emit(self.agent_id, "Error: " + str(e)[:200])
                    return

                data = response.json()
                msg = data.get("message", {})
                content = msg.get("content", "")
                tool_calls = msg.get("tool_calls", [])

                if content:
                    if has_chinese(content):
                        self.step_log.emit(self.agent_id, "WARNING: Chinese detected, forcing retry without tools...")
                        messages.append({"role": "assistant", "content": content})
                        messages.append({
                            "role": "user",
                            "content": (
                                "Your previous response contained Chinese text which is NOT allowed. "
                                "Rewrite your response in English or Arabic only. "
                                "Do NOT use Chinese characters. "
                                "Give a clean text answer without code blocks."
                            )
                        })
                        continue
                    messages.append({"role": "assistant", "content": content})

                if tool_calls and self.mode == "worker" and step < 4:
                    messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})
                    for tc in tool_calls:
                        if self._stop:
                            return
                        func = tc.get("function", {})
                        name = func.get("name", "")
                        args_raw = func.get("arguments", "{}")
                        args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                        try:
                            result = execute_tool(name, args)
                            self.step_log.emit(self.agent_id, name + ": " + str(result)[:200])
                            messages.append({"role": "tool", "name": name, "content": str(result)[:1000]})
                            last_error = None
                        except Exception as e:
                            last_error = str(e)
                            self.step_log.emit(self.agent_id, "Error in " + name + ": " + str(e)[:200])
                            messages.append({"role": "tool", "name": name, "content": "Error: " + str(e)[:500]})
                else:
                    if content.strip():
                        final = clean_result(content)
                        if final == "No clean result produced.":
                            if last_error:
                                final = "Task failed: " + last_error
                            elif retry_count > 0:
                                final = "Task failed after retry."
                            else:
                                final = "Task failed: no output and no error recorded."
                        self.result_ready.emit(self.agent_id, final)
                        return
                    else:
                        if last_error:
                            self.result_ready.emit(self.agent_id, "Task failed: " + last_error)
                        else:
                            self.result_ready.emit(self.agent_id, "No output produced.")
                        return

            self.result_ready.emit(self.agent_id, "Max steps reached without final answer.")
        except Exception as e:
            self.error.emit(self.agent_id, str(e))

    def _build_messages(self):
        if self.mode == "explorer":
            sys_prompt = (
                "You are a read-only explorer agent. Investigate the task and report findings.\n"
                "CRITICAL: Use os.walk() to traverse ALL subdirectories RECURSIVELY. Do NOT use os.listdir().\n"
                "CRITICAL: You MUST respond in English or Arabic only. NEVER use Chinese.\n"
                "You have a MAXIMUM of 3 tool calls. After that, give your FINAL ANSWER as plain text.\n"
                "Your final answer must be a clean 1-2 sentence summary, NOT code.\n"
                "Working directory: " + self.workspace_path
            )
        else:
            sys_prompt = (
                "You are a worker subagent. Execute the task efficiently.\n"
                "CRITICAL: When counting or searching files, you MUST use os.walk() to search RECURSIVELY through ALL subdirectories. NEVER use os.listdir() — it is NOT recursive.\n"
                "CRITICAL: Put ALL your code in a SINGLE exec() call. Do NOT define functions in one exec() and call them in another — variables do NOT persist between calls.\n"
                "CRITICAL: You MUST respond in English or Arabic only. NEVER use Chinese or any other language.\n"
                "CRITICAL: Do NOT use Chinese comments in your code. Use English comments only.\n"
                "You have a MAXIMUM of 3 tool calls. After that, you MUST give your FINAL ANSWER as plain text only.\n"
                "Always print results in your code with print(). Use English variable names.\n"
                "Your final answer must be a clean 1-2 sentence summary WITHOUT code blocks.\n"
                "If your code fails, report the error clearly in your final answer.\n"
                "Working directory: " + self.workspace_path
            )
        return [{"role": "system", "content": sys_prompt}, {"role": "user", "content": self.task}]


class SubagentManager:
    def __init__(self):
        self.agents = {}
        self.counter = 0

    def spawn(self, task, workspace_path, mode="worker", max_steps=8):
        if len(self.agents) >= MAX_SUBAGENTS:
            return None, "Maximum subagents reached"
        self.counter += 1
        agent_id = "agent_" + str(self.counter)
        worker = SubagentWorker(agent_id, task, workspace_path, mode, max_steps)
        self.agents[agent_id] = {"worker": worker, "task": task, "mode": mode, "result": None, "active": True}
        return agent_id, worker

    def set_result(self, agent_id, result):
        if agent_id in self.agents:
            self.agents[agent_id]["result"] = result
            self.agents[agent_id]["active"] = False

    def get_all_results(self):
        return {aid: {"task": i["task"], "mode": i["mode"], "result": i["result"]} for aid, i in self.agents.items()}

    def active_count(self):
        return sum(1 for i in self.agents.values() if i["active"])

    def clear(self):
        self.agents.clear()
        self.counter = 0

    def stop_all(self):
        for info in self.agents.values():
            if info["active"] and info["worker"]:
                info["worker"].stop()

    def wait_for_all(self, timeout=120):
        start = time.time()
        while self.active_count() > 0:
            if time.time() - start > timeout:
                break
            time.sleep(0.5)
