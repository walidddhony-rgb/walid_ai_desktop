from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from knowledge.ingestor import SUPPORTED_EXTS, ingest_file


class IndexWorker(QThread):
    progress_changed = pyqtSignal(int)
    log_message = pyqtSignal(str)
    finished_indexing = pyqtSignal(int)
    cancelled = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, file_paths=None, directory_path=None):
        super().__init__()
        self.file_paths = file_paths or []
        self.directory_path = directory_path
        self._cancel = False

    def stop(self):
        self._cancel = True

    def run(self):
        try:
            targets = []
            if self.directory_path:
                root = Path(self.directory_path)
                for f in root.rglob("*"):
                    if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS:
                        targets.append(str(f))
            else:
                targets = list(self.file_paths)
            if not targets:
                self.log_message.emit("لا توجد ملفات قابلة للفهرسة.")
                self.finished_indexing.emit(0)
                return
            total = len(targets)
            indexed_chunks = 0
            for idx, path in enumerate(targets, start=1):
                if self._cancel:
                    self.cancelled.emit("تم إلغاء الفهرسة.")
                    return
                self.log_message.emit(f"فهرسة: {Path(path).name}")
                indexed_chunks += ingest_file(path)
                self.progress_changed.emit(int((idx / total) * 100))
            self.finished_indexing.emit(indexed_chunks)
        except Exception as e:
            self.error.emit(str(e))
