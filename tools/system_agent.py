"""Static file system operations with path validation."""

from __future__ import annotations

import shutil
from pathlib import Path


class SystemAgent:
    @staticmethod
    def create_file(path: str, content: str) -> str:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return str(p)

    @staticmethod
    def create_dir(path: str) -> str:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return str(p)

    @staticmethod
    def archive_folder(src: str, dest: str) -> str:
        src_p, dest_p = Path(src), Path(dest)
        dest_p.mkdir(parents=True, exist_ok=True)
        b = dest_p / src_p.name
        shutil.make_archive(str(b), "zip", src_p)
        return str(b) + ".zip"
