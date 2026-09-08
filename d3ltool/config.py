# -*- coding: utf-8 -*-
"""User settings persisted as JSON in ~/.d3ltool/config.json."""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".d3ltool"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "language": "zh",
    "download_dir": str(Path.home() / "Downloads"),
    "max_workers": 3,
    "proxy_url": "",
    "username": "",
}


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    try:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            cfg.update({k: v for k, v in raw.items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {k: cfg.get(k, DEFAULTS[k]) for k in DEFAULTS}
    CONFIG_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def update_config(**kw) -> dict:
    cfg = load_config()
    cfg.update({k: v for k, v in kw.items() if k in DEFAULTS})
    save_config(cfg)
    return cfg
