from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

# Cross-platform config dir: ~/.config/dmt/config.json (Linux), %APPDATA%/dmt/config.json (Windows)
CONFIG_DIR = Path.home() / ("AppData/Roaming" if (Path.home() / "AppData/Roaming").exists() else ".config") / "dmt"
CONFIG_PATH = CONFIG_DIR / "config.json"


class Hotkeys(BaseModel):
    enabled: bool = False
    fade: str = "F"
    open: str = "O"


class UIState(BaseModel):
    geometry: dict = Field(default_factory=dict)
    splitterSizes: dict = Field(default_factory=dict)


class Config(BaseModel):
    imageRoots: List[str] = Field(default_factory=list)
    playerDisplay: int = 0
    fitMode: str = "fit"  # "fit" | "fill" | "actual"
    watchFolders: bool = False
    hotkeys: Hotkeys = Field(default_factory=Hotkeys)
    ui: UIState = Field(default_factory=UIState)
    playerWindowed: bool = True


def load_config() -> Config:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return Config.model_validate(data)
        except Exception:
            # Fallback to defaults if config corrupt
            return Config()
    else:
        return Config()


def save_config(cfg: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(cfg.model_dump_json(indent=2), encoding="utf-8")
