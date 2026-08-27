import shutil
from core.utils import sanitize_path, truncate


def list_directory(path):
    p = sanitize_path(path)
    if not p.exists():
        return f"Path not found: {p}"
    items = []
    for item in sorted(p.iterdir()):
        kind = 'DIR ' if item.is_dir() else 'FILE'
        size = item.stat().st_size if item.is_file() else 0
        items.append(f"{kind} {item.name} ({size})")
    return '\n'.join(items) or '(empty directory)'


def read_file(path):
    p = sanitize_path(path)
    if not p.exists() or not p.is_file():
        return f"File not found: {p}"
    return truncate(p.read_text(encoding='utf-8', errors='ignore'), 15000)


def create_file(path, content):
    p = sanitize_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')
    return f"Created: {p}"


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


def archive_folder(src, dest):
    src_p = sanitize_path(src)
    dest_p = sanitize_path(dest)
    if not src_p.exists():
        return f"Source not found: {src_p}"
    dest_p.mkdir(parents=True, exist_ok=True)
    base_name = dest_p / src_p.name
    shutil.make_archive(str(base_name), 'zip', src_p)
    return f"Archived to {base_name}.zip"
