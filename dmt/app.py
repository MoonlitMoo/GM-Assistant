from __future__ import annotations

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QCoreApplication

from .core.config import (
    load_config, save_config, get_last_db_path, set_last_db_path, ORG, APP
)
from .ui.main_window import MainWindow

# Your DatabaseManager from earlier (engine + sessions, WAL PRAGMAs)
from db.manager import DatabaseManager
from .ui.player_window.display_state import DisplayState, parse_scale_mode, TransitionMode

DEFAULT_DB = Path.home() / "GMAssistant" / "library.db"


def _choose_initial_db_path() -> Path:
    last = get_last_db_path()
    return last if last else DEFAULT_DB


def main() -> None:
    # High-DPI friendly defaults
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # Set QSettings identity BEFORE any settings access
    QCoreApplication.setOrganizationName(ORG)
    QCoreApplication.setApplicationName(APP)

    # Load user prefs (QSettings-backed)
    cfg = load_config()

    # Create necessary states
    display_state = DisplayState(
        scale_mode=parse_scale_mode(cfg.fitMode),
        transition_mode=TransitionMode.CROSSFADE,
        windowed=cfg.playerWindowed,
        display_index=cfg.playerDisplay,
        on_persist=lambda d: (
            setattr(cfg, "fitMode", d["fitMode"]),
            setattr(cfg, "playerWindowed", d["playerWindowed"]),
            setattr(cfg, "playerDisplay", d["playerDisplay"])
        )
    )

    # Open database (last used or default) and remember it
    db = DatabaseManager()
    db_path = _choose_initial_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db.open(db_path, create_if_missing=True)
    set_last_db_path(db_path)

    # Construct and show the main window (pass db so widgets can use it)
    win = MainWindow(cfg=cfg, dbm=db, display_state=display_state)
    win.show()

    # Persist settings on quit
    def persist():
        snap = display_state.snapshot()
        cfg.fitMode = snap["fitMode"]
        cfg.playerWindowed = snap["playerWindowed"]
        cfg.playerDisplay = snap["playerDisplay"]
        save_config(cfg)
        if db.path:
            set_last_db_path(db.path)

    app.aboutToQuit.connect(persist)
    sys.exit(app.exec())
