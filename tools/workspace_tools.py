import subprocess
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal


class WorkspaceCommandWorker(QThread):
    log_message = pyqtSignal(str)
    finished_run = pyqtSignal(int, str)
    cancelled = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, workspace_path: str, command: str):
        super().__init__()
        self.workspace_path = workspace_path
        self.command = command
        self.process = None
        self._cancel = False

    def stop(self):
        self._cancel = True
        try:
            if self.process and self.process.poll() is None:
                self.process.terminate()
        except Exception:
            pass

    def run(self):
        try:
            cwd = Path(self.workspace_path)
            self.log_message.emit(f'Executing in workspace: {self.command}')
            self.process = subprocess.Popen(
                self.command,
                cwd=str(cwd),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
            )
            stdout, stderr = self.process.communicate()
            if self._cancel:
                self.cancelled.emit('تم إلغاء تنفيذ الأمر داخل مساحة العمل.')
                return
            output = (stdout or '') + ('\\n' + stderr if stderr else '')
            self.finished_run.emit(self.process.returncode or 0, output.strip())
        except Exception as e:
            self.error.emit(str(e))