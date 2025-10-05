from __future__ import annotations

import json
from dataclasses import field
from pathlib import Path
from typing import List, Any
from pydantic import BaseModel, Field
from PySide6.QtCore import QSettings

# QSettings scope
ORG = "PersonalApps"
APP = "GM Assistant"


class UIState(BaseModel):
    geometry: dict = Field(default_factory=dict)
    splitterSizes: dict = Field(default_factory=dict)


class Config(BaseModel):
    ui: UIState = Field(default_factory=UIState)
    last_db_path: str = ""
    displayState: dict[str, Any] = field(default_factory=dict)
    initiativeState: dict[str, Any] = field(default_factory=dict)


def _s() -> QSettings:
    return QSettings(ORG, APP)


def _read_json(s: QSettings, key: str, default: dict) -> dict:
    raw = s.value(key, "")
    if isinstance(raw, (dict, list)):
        return raw  # some backends can store native types
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _write_json(s: QSettings, key: str, obj: dict | list) -> None:
    s.setValue(key, json.dumps(obj, ensure_ascii=False))


def load_config() -> Config:
    s = _s()

    # --- UI ---
    s.beginGroup("ui")
    geometry = _read_json(s, "geometry", {})
    splitter_sizes = _read_json(s, "splitterSizes", {})
    s.endGroup()

    # --- Database ---
    s.beginGroup("db")
    last_db_path = str(s.value("last_path", "", str))
    s.endGroup()

    # --- DisplayState ---
    s.beginGroup("displaystate")
    display_state = _read_json(s, "state", {})
    s.endGroup()

    # --- Initiative ---
    s.beginGroup("initiative")
    initiative_state = _read_json(s, "state", {})
    s.endGroup()

    return Config(
        ui=UIState(geometry=geometry, splitterSizes=splitter_sizes),
        last_db_path=last_db_path,
        displayState=display_state,
        initiativeState=initiative_state
    )


def save_config(cfg: Config) -> None:
    s = _s()

    # --- UI ---
    s.beginGroup("ui")
    _write_json(s, "geometry", dict(cfg.ui.geometry))
    _write_json(s, "splitterSizes", dict(cfg.ui.splitterSizes))
    s.endGroup()

    # --- Database ---
    s.beginGroup("db")
    s.setValue("last_path", cfg.last_db_path)
    s.endGroup()

    # --- DisplayState ---
    s.beginGroup("displaystate")
    _write_json(s, "state", cfg.displayState)
    s.endGroup()

    # --- Initiative ---
    s.beginGroup("initiative")
    _write_json(s, "state", cfg.initiativeState)
    s.endGroup()
