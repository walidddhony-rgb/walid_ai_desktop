from typing import Any

from core.config import DATA_DIR

PROFILES_DIR = DATA_DIR / "profiles"
PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def _parse_yaml(text: str) -> dict:
    result: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip("\"'")
            if val.lower() in ("true", "false"):
                result[key] = val.lower() == "true"
            elif val.isdigit():
                result[key] = int(val)
            else:
                result[key] = val
    return result


def list_profiles() -> list:
    profiles = []
    for f in sorted(PROFILES_DIR.glob("*.yaml")):
        profiles.append(f.stem)
    for f in sorted(PROFILES_DIR.glob("*.yml")):
        profiles.append(f.stem)
    return list(dict.fromkeys(profiles))


def load_profile(name: str) -> dict:
    for ext in (".yaml", ".yml"):
        p = PROFILES_DIR / f"{name}{ext}"
        if p.exists():
            return _parse_yaml(p.read_text(encoding="utf-8"))
    return {}


def save_profile(name: str, data: dict) -> str:
    p = PROFILES_DIR / f"{name}.yaml"
    lines = []
    for k, v in data.items():
        if isinstance(v, bool):
            lines.append(f"{k}: {str(v).lower()}")
        elif isinstance(v, int | float):
            lines.append(f"{k}: {v}")
        else:
            lines.append(f'{k}: "{v}"')
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


def ensure_default_profile():
    default = PROFILES_DIR / "default.yaml"
    if not default.exists():
        save_profile(
            "default",
            {
                "model": "qwen2.5:7b",
                "auto_run": False,
                "auto_learn": True,
                "dark_mode": True,
            },
        )
