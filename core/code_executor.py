import os
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


class CodeExecutionWorker(QThread):
    code_started = pyqtSignal(str, str)
    code_output = pyqtSignal(str)
    code_finished = pyqtSignal(int, str)
    approval_needed = pyqtSignal(str, str, str)
    error = pyqtSignal(str)

    def __init__(self, code: str, language: str, workspace_path: str, auto_run: bool = False):
        super().__init__()
        self.code = code
        self.language = language.lower().strip()
        self.workspace_path = workspace_path
        self.auto_run = auto_run
        self._approved = False
        self._rejected = False

    def approve(self):
        self._approved = True

    def reject(self):
        self._rejected = True

    def run(self):
        from core.sandbox import classify_action, is_dangerous

        if is_dangerous(self.code):
            self.error.emit("تم رفض الكود لأنه يحتوي على أنماط خطيرة.")
            return
        action = classify_action(self.code, self.language)
        if not self.auto_run or action in ("dangerous", "destructive"):
            self.approval_needed.emit(self.code, self.language, action)
            while not self._approved and not self._rejected:
                self.msleep(50)
            if self._rejected:
                self.code_output.emit("تم رفض التنفيذ من قبل المستخدم.")
                self.code_finished.emit(1, "rejected")
                return
        self.code_started.emit(self.code, self.language)
        try:
            if self.language in ("python", "py", "python3"):
                return_code, output = self._run_python()
            elif self.language in ("shell", "sh", "bash", "cmd", "powershell", "bat"):
                return_code, output = self._run_shell()
            elif self.language in ("javascript", "js", "node"):
                return_code, output = self._run_javascript()
            else:
                return_code, output = self._run_shell()
            self.code_output.emit(output)
            self.code_finished.emit(return_code, output)
        except Exception as e:
            err = f"{e}\n{traceback.format_exc()[-500:]}"
            self.code_output.emit(err)
            self.code_finished.emit(1, err)

    def _run_python(self) -> tuple:
        tmp = Path(tempfile.gettempdir()) / "walid_exec.py"
        header = "# -*- coding: utf-8 -*-\n"
        tmp.write_text(header + self.code, encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        result = subprocess.run(
            [sys.executable, str(tmp)],
            cwd=self.workspace_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            env=env,
        )
        output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        return result.returncode, output.strip()

    def _run_shell(self) -> tuple:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            self.code,
            cwd=self.workspace_path,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            env=env,
        )
        output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        return result.returncode, output.strip()

    def _run_javascript(self) -> tuple:
        tmp = Path(tempfile.gettempdir()) / "walid_exec.js"
        tmp.write_text(self.code, encoding="utf-8")
        result = subprocess.run(
            ["node", str(tmp)],
            cwd=self.workspace_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        return result.returncode, output.strip()
