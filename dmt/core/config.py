from __future__ import annotations

import json
from typing import List
from pydantic import BaseModel, Field
from PySide6.QtCore import QSettings

# QSettings scope
ORG = "None"
APP = "GM Assistant"


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


def _s() -> QSettings:
    # Organization/Application should be set once in app.py before first use,
    # but we also pass them here to be explicit.
    return QSettings(ORG, APP)


def _read_json(s: QSettings, key: str, default: dict) -> dict:
    raw = s.value(key, "")
    if isinstance(raw, (dict, list)):
        # Some backends may round-trip as native
        return raw  # type: ignore[return-value]
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

    # --- General ---
    s.beginGroup("general")
    image_roots = s.value("imageRoots", [], list)
    player_display = s.value("playerDisplay", 0, int)
    fit_mode = s.value("fitMode", "fit", str)
    watch_folders = s.value("watchFolders", False, bool)
    player_windowed = s.value("playerWindowed", True, bool)
    s.endGroup()

    # --- Hotkeys ---
    s.beginGroup("hotkeys")
    hk = Hotkeys(
        enabled=s.value("enabled", False, bool),
        fade=s.value("fade", "F", str),
        open=s.value("open", "O", str),
    )
    s.endGroup()

    # --- UI ---
    s.beginGroup("ui")
    geometry = _read_json(s, "geometry", {})
    splitter_sizes = _read_json(s, "splitterSizes", {})
    s.endGroup()

    return Config(
        imageRoots=image_roots,
        playerDisplay=player_display,
        fitMode=fit_mode,
        watchFolders=watch_folders,
        hotkeys=hk,
        ui=UIState(geometry=geometry, splitterSizes=splitter_sizes),
        playerWindowed=player_windowed,
    )


def save_config(cfg: Config) -> None:
    s = _s()

    # --- General ---
    s.beginGroup("general")
    s.setValue("imageRoots", list(cfg.imageRoots))
    s.setValue("playerDisplay", int(cfg.playerDisplay))
    s.setValue("fitMode", str(cfg.fitMode))
    s.setValue("watchFolders", bool(cfg.watchFolders))
    s.setValue("playerWindowed", bool(cfg.playerWindowed))
    s.endGroup()

    # --- Hotkeys ---
    s.beginGroup("hotkeys")
    s.setValue("enabled", bool(cfg.hotkeys.enabled))
    s.setValue("fade", str(cfg.hotkeys.fade))
    s.setValue("open", str(cfg.hotkeys.open))
    s.endGroup()

    # --- UI ---
    s.beginGroup("ui")
    _write_json(s, "geometry", dict(cfg.ui.geometry))
    _write_json(s, "splitterSizes", dict(cfg.ui.splitterSizes))
    s.endGroup()
