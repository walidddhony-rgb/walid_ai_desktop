"""File system tool implementations with path validation."""
from __future__ import annotations
import shutil
from pathlib import Path
from core.utils import sanitize_path, truncate


def list_directory(path: str) -> str:
    p = sanitize_path(path)
    if not p.exists():
        return f"Path not found: {p}"
    items = []
    for item in sorted(p.iterdir()):
        t = "DIR " if item.is_dir() else "FILE"
        s = item.stat().st_size if item.is_file() else 0
        items.append(f"{t} {item.name} ({s})")
    return "\n".join(items) or "(empty directory)"


def read_file(path: str) -> str:
    p = sanitize_path(path)
    if not p.exists():
        return f"File not found: {p}"
    if not p.is_file():
        return f"Not a file: {p}"
    return truncate(p.read_text(encoding="utf-8", errors="ignore"), 15000)


def read_project_files(path: str, extensions=None) -> str:
    p = sanitize_path(path)
    if not p.exists():
        return f"Path not found: {p}"
    exts = extensions or ["py", "js", "html", "css", "json", "txt", "md",
                          "sql", "yaml", "yml", "toml", "cfg", "ini", "cpp", "h", "java"]
    results = []
    for ext in exts:
        for f in p.rglob(f"*.{ext}"):
            sp = str(f)
            if any(x in sp for x in ["__pycache__", ".git", "node_modules", ".venv"]):
                continue
            try:
                c = f.read_text(encoding="utf-8", errors="ignore")[:8000]
                results.append(f"=== {f.relative_to(p)} ===\n{c}")
            except Exception:
                pass
    return truncate("\n\n".join(results), 50000)


def create_file(path: str, content: str) -> str:
    p = sanitize_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Created: {p}"


def create_directory(path: str) -> str:
    p = sanitize_path(path)
    p.mkdir(parents=True, exist_ok=True)
    return f"Created directory: {p}"


def move_file(src: str, dest: str) -> str:
    src_p = sanitize_path(src)
    dest_p = sanitize_path(dest)
    if not src_p.exists():
        return f"Source not found: {src_p}"
    dest_p.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_p), str(dest_p))
    return f"Moved {src_p} -> {dest_p}"


def archive_folder(src: str, dest: str) -> str:
    src_p = sanitize_path(src)
    dest_p = sanitize_path(dest)
    if not src_p.exists():
        return f"Source not found: {src_p}"
    dest_p.mkdir(parents=True, exist_ok=True)
    base_name = dest_p / src_p.name
    shutil.make_archive(str(base_name), "zip", src_p)
    return f"Archived to {base_name}.zip"
