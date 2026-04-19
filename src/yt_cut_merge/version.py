from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_version() -> str:
    try:
        return (get_project_root() / "VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        return "0.0.0"
