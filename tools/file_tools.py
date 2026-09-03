import threading
import shutil
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

from core.utils import sanitize_path, truncate


class FileChangeBridge(QObject):
    review_needed = pyqtSignal(str, str, str)

    def __init__(self):
        super().__init__()
        self._event = threading.Event()
        self._approved = False
        self._auto_apply = False

    def request(self, filepath, old_content, new_content, auto_apply_files):
        self._event.clear()
        self._approved = False
        self._auto_apply = False
        self.review_needed.emit(filepath, old_content, new_content)
        self._event.wait(timeout=300)
        if self._approved and self._auto_apply:
            auto_apply_files.add(filepath)
        return self._approved

    def set_result(self, approved, auto_apply):
        self._approved = approved
        self._auto_apply = auto_apply
        self._event.set()


_bridge = None
_auto_apply_files = set()


def set_bridge(bridge):
    global _bridge
    _bridge = bridge


def set_parent_widget(widget):
    pass


def get_auto_apply_files():
    return _auto_apply_files


def reset_auto_apply():
    _auto_apply_files.clear()


def list_directory(path):
    p = sanitize_path(path)
    if not p.exists():
        return f"Path not found: {p}"
    items = []
    for item in sorted(p.iterdir()):
        kind = "DIR " if item.is_dir() else "FILE"
        size = item.stat().st_size if item.is_file() else 0
        items.append(f"{kind} {item.name} ({size})")
    return "\n".join(items) or "(empty directory)"


def read_file(path):
    p = sanitize_path(path)
    if not p.exists() or not p.is_file():
        return f"File not found: {p}"
    return truncate(p.read_text(encoding="utf-8", errors="ignore"), 15000)


def apply_file_change(filepath, new_content, auto_apply_files):
    p = Path(filepath)
    old_content = ""
    if p.exists():
        try:
            old_content = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass

    if old_content == new_content:
        return True

    if str(filepath) in auto_apply_files or filepath in auto_apply_files:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(new_content, encoding="utf-8")
        return True

    if _bridge:
        approved = _bridge.request(filepath, old_content, new_content, auto_apply_files)
        if approved:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(new_content, encoding="utf-8")
            return True
        return False

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(new_content, encoding="utf-8")
    return True


def create_file(path, content):
    p = sanitize_path(path)
    success = apply_file_change(str(p), content, _auto_apply_files)
    if success:
        return f"File saved: {p}"
    return f"File change rejected by user: {p}"


def edit_file(path, old_text, new_text):
    p = sanitize_path(path)
    if not p.exists():
        return f"File not found: {p}"
    content = p.read_text(encoding="utf-8", errors="ignore")
    if old_text not in content:
        return f"Text not found in file: {old_text[:80]}"
    new_content = content.replace(old_text, new_text, 1)
    success = apply_file_change(str(p), new_content, _auto_apply_files)
    if success:
        return f"File edited: {p}"
    return f"File edit rejected by user: {p}"


def create_directory(path):
    p = sanitize_path(path)
    p.mkdir(parents=True, exist_ok=True)
    return f"Created directory: {p}"


def move_file(src, dest):
    src_p = sanitize_path(src)
    dest_p = sanitize_path(dest)
    if not src_p.exists():
        return f"Source not found: {src_p}"
    dest_p.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_p), str(dest_p))
    return f"Moved {src_p} -> {dest_p}"
