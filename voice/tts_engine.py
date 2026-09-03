import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

pyttsx3: Any | None = None
HAS_PYTTSX = False

try:
    import pyttsx3 as _pyttsx3

    pyttsx3 = _pyttsx3
    HAS_PYTTSX = True
except ImportError:
    pass


class TTSSpeakWorker(QThread):
    started_speaking = pyqtSignal()
    finished_speaking = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, text: str, use_edge: bool = False):
        super().__init__()
        self.text = text
        self.use_edge = use_edge

    def run(self):
        if not self.text.strip():
            return

        self.started_speaking.emit()
        try:
            if self.use_edge:
                self._speak_edge(self.text)
            elif HAS_PYTTSX and pyttsx3 is not None:
                engine = pyttsx3.init()
                engine.setProperty("rate", 160)
                engine.say(self.text)
                engine.runAndWait()
            else:
                self._speak_edge(self.text)
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            self.finished_speaking.emit()

    def _speak_edge(self, text: str):
        try:
            import edge_tts
        except ImportError as exc:
            raise RuntimeError("Neither pyttsx3 nor edge-tts is installed") from exc

        async def _run():
            tmp = Path(tempfile.gettempdir()) / "walid_tts.mp3"
            communicate = edge_tts.Communicate(text, "ar-EG-SalmaNeural")
            await communicate.save(str(tmp))

            if sys.platform == "win32":
                os.startfile(str(tmp))
            else:
                subprocess.run(["mpg123", str(tmp)], check=False)

        asyncio.run(_run())
