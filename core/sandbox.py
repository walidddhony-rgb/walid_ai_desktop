import re
from enum import Enum


class PermissionLevel(Enum):
    ASK = "ask"
    AUTO_RUN = "auto_run"
    READ_ONLY = "read_only"


DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"del\s+/[sS]\s+/[qQ]",
    r"format\s+[A-Z]:",
    r"shutdown",
    r"reboot",
    r":\(\)\{.*\};:",
    r"mkfs",
    r"dd\s+if=",
]

DANGEROUS_RE = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]


def is_dangerous(code: str) -> bool:
    return any(p.search(code) for p in DANGEROUS_RE)


def classify_action(code: str, language: str) -> str:
    if is_dangerous(code):
        return "dangerous"
    destructive_keywords = [
        "rm ",
        "del ",
        "rmdir",
        "remove",
        "drop",
        "truncate",
        "overwrite",
        ">",
        "mv ",
    ]
    lower = code.lower()
    if any(kw in lower for kw in destructive_keywords):
        return "destructive"
    return "safe"
