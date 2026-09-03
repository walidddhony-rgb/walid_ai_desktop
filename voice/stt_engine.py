import tempfile
import wave
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from core.config import WHISPER_MODEL

pyaudio: Any | None = None
HAS_PYAUDIO = False

try:
    import pyaudio as _pyaudio

    pyaudio = _pyaudio
    HAS_PYAUDIO = True
except ImportError:
    pass

try:
    import whisper

    HAS_WHISPER: str | bool = "openai"
except ImportError:
    try:
        from faster_whisper import WhisperModel

        HAS_WHISPER = "faster"
    except ImportError:
        HAS_WHISPER = False


class VoiceRecorder(QThread):
    chunk_recorded = pyqtSignal(bytes)
    error = pyqtSignal(str)

    def __init__(self, rate=16000, chunk=1024):
        super().__init__()
        self.rate = rate
        self.chunk = chunk
        self._stop = False
        self.frames = []

    def stop(self):
        self._stop = True

    def run(self):
        if not HAS_PYAUDIO:
            self.error.emit("PyAudio not installed. Run: pip install pyaudio")
            return
        try:
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk,
            )
            while not self._stop:
                data = stream.read(self.chunk, exception_on_overflow=False)
                self.frames.append(data)
                self.chunk_recorded.emit(data)
            stream.stop_stream()
            stream.close()
            pa.terminate()
        except Exception as e:
            self.error.emit(str(e))


class VoiceSTTWorker(QThread):
    transcribed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, wav_path: str):
        super().__init__()
        self.wav_path = wav_path

    def run(self):
        if not HAS_WHISPER:
            self.error.emit(
                "Whisper not installed. Run: pip install openai-whisper OR faster-whisper"
            )
            return
        try:
            if HAS_WHISPER == "faster":
                model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
                segments, _ = model.transcribe(self.wav_path, language="ar")
                text = " ".join(seg.text for seg in segments)
            else:
                model = whisper.load_model(WHISPER_MODEL)
                result = model.transcribe(self.wav_path, language="ar")
                text = result.get("text", "")
            self.transcribed.emit(text.strip())
        except Exception as e:
            self.error.emit(str(e))


def save_frames_to_wav(frames, rate=16000, channels=1, output_path=None):
    if output_path is None:
        output_path = str(Path(tempfile.gettempdir()) / "walid_voice.wav")
    wf = wave.open(output_path, "wb")
    wf.setnchannels(channels)
    wf.setsampwidth(2)
    wf.setframerate(rate)
    wf.writeframes(b"".join(frames))
    wf.close()
    return output_path
