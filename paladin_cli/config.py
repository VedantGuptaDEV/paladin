"""
config.py — Read/write helpers for ~/.paladin/config.json
"""

import json
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".paladin"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS: dict[str, Any] = {
    "api_url": "http://localhost:8000",
    "ws_url": "ws://localhost:8000",
    "timeout": 30,
    "current_session": None,
}


def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return dict(DEFAULTS)
    try:
        with open(CONFIG_FILE) as f:
            return {**DEFAULTS, **json.load(f)}
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)


def save(cfg: dict[str, Any]) -> None:
    _ensure_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def get(key: str, default: Any = None) -> Any:
    return load().get(key, default)


def set_value(key: str, value: Any) -> None:
    cfg = load()
    cfg[key] = value
    save(cfg)


def reset() -> None:
    save(dict(DEFAULTS))
