import os
from pathlib import Path


def get_skills_dirs(workspace_path: str):
    dirs = []
    ws_skills = Path(workspace_path) / ".agents" / "skills"
    home_skills = Path.home() / ".agents" / "skills"
    for d in (ws_skills, home_skills):
        if d.exists() and d.is_dir():
            dirs.append(d)
    return dirs


def discover_skills(workspace_path: str) -> list:
    skills = []
    for d in get_skills_dirs(workspace_path):
        for item in sorted(d.iterdir()):
            if not item.is_dir():
                continue
            skill_md = item / "SKILL.md"
            if not skill_md.exists():
                continue
            try:
                content = skill_md.read_text(encoding="utf-8", errors="ignore")
                name = item.name
                description = ""
                for line in content.splitlines():
                    low = line.lower().strip()
                    if low.startswith("# description:") or low.startswith("description:"):
                        description = line.split(":", 1)[1].strip()
                        break
                    if low.startswith("# name:") or low.startswith("name:"):
                        name = line.split(":", 1)[1].strip() or name
                skills.append({
                    "name": name,
                    "description": description,
                    "path": str(skill_md),
                    "folder": str(item),
                })
            except Exception:
                pass
    return skills


def load_skill_content(skill_path: str) -> str:
    p = Path(skill_path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="ignore").strip()


def format_skills_index(skills: list) -> str:
    if not skills:
        return ""
    lines = ["المهارات المتاحة:"]
    for s in skills:
        desc = s["description"] or "لا يوجد وصف"
        lines.append(f"- {s['name']}: {desc}")
    return "\n".join(lines)
