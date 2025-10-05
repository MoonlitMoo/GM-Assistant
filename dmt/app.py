from __future__ import annotations

import sys
from pathlib import Path
from importlib.metadata import version

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QCoreApplication

from .core.config import (
    load_config, save_config, ORG, APP
)
from .ui.main_window import MainWindow
from .ui.initiative_tab import InitiativeController
from .ui.player_window.display_state import DisplayState, parse_scale_mode, TransitionMode

from dmt.db.manager import DatabaseManager

DEFAULT_DB = Path.home() / "GMAssistant" / "library.db"


def main() -> None:
    # High-DPI friendly defaults
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # Set QSettings identity BEFORE any settings access
    QCoreApplication.setOrganizationName(ORG)
    QCoreApplication.setApplicationName(APP)
    QCoreApplication.setApplicationVersion(version("gm-assistant"))

    # Load user prefs (QSettings-backed)
    cfg = load_config()

    # Create necessary states
    display_state = DisplayState(on_persist=lambda d: setattr(cfg.displayState, d, {}))
    display_state.load_state(cfg.displayState)
    initiative_controller = InitiativeController()
    initiative_controller.load_state(cfg.initiativeState)

    # Open database (last used or default) and remember it
    db = DatabaseManager()
    db_path = Path(cfg.last_db_path if cfg.last_db_path else DEFAULT_DB)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db.open(db_path, create_if_missing=True)
    cfg.last_db_path = str(db_path)

    # Construct and show the main window (pass db so widgets can use it)
    win = MainWindow(cfg=cfg, dbm=db, display_state=display_state, initiative_ctl=initiative_controller)
    win.show()

    # Persist settings on quit
    def persist():
        cfg.last_db_path = str(db.path)
        cfg.displayState = display_state.snapshot()
        cfg.initiativeState = initiative_controller.snapshot()
        save_config(cfg)

    app.aboutToQuit.connect(persist)
    sys.exit(app.exec())
