"""Shared utility functions."""
from __future__ import annotations
from pathlib import Path
import re, uuid


def safe_filename(name: str) -> str:
    name = re.sub(r'[^\w\-.\u0600-\u06FF ]+', '_', name).strip()
    return name or uuid.uuid4().hex


def truncate(text: str | None, n: int = 12000) -> str:
    text = text or ""
    return text if len(text) <= n else text[:n] + "\n...[مقتطع]"


def sanitize_path(path_str: str) -> Path:
    return Path(path_str).resolve()


def validate_path_safe(path_str: str) -> tuple:
    try:
        p = Path(path_str).resolve()
        system_dirs = ["C:\\Windows", "C:\\Program Files", "C:\\ProgramData"]
        for sd in system_dirs:
            if str(p).lower().startswith(sd.lower()):
                return (False, p, f"Blocked system path: {sd}")
        return (True, p, "OK")
    except Exception as e:
        return (False, None, str(e))
