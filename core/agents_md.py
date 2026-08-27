from pathlib import Path


def read_agents_md(workspace_path: str) -> str:
    ws = Path(workspace_path)
    candidates = [
        ws / "AGENTS.md",
        ws / "agents.md",
        ws / ".agents" / "AGENTS.md",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            try:
                return c.read_text(encoding="utf-8", errors="ignore").strip()
            except Exception:
                pass
    return ""


def write_agents_md(workspace_path: str, content: str) -> str:
    ws = Path(workspace_path)
    p = ws / "AGENTS.md"
    p.write_text(content, encoding="utf-8")
    return str(p)
