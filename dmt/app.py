from __future__ import annotations

import os
import sys
from pathlib import Path
from importlib.metadata import version

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QCoreApplication

from .core.config import (
    load_config, save_config, ORG, APP
)
from .core.platform_helpers import set_app_identity, ensure_linux_desktop_entries
from .ui.main_window import MainWindow
from .ui.initiative_tab import InitiativeController
from .ui.player_window.display_state import DisplayState

from dmt.db.manager import DatabaseManager
from .ui.player_window.player_ipc import PlayerController

DEFAULT_DB = Path.home() / "GMAssistant" / "library.db"


def main() -> None:
    # High-DPI friendly defaults
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Check that setup is completed for desktop icons + files.
    ensure_linux_desktop_entries()

    app = QApplication(sys.argv)
    # Set QSettings identity BEFORE any settings access
    QCoreApplication.setOrganizationName(ORG)
    QCoreApplication.setApplicationName(APP)
    QCoreApplication.setApplicationVersion(version("gm-assistant"))
    set_app_identity("GMAssistant.Main", APP)

    # Load user prefs (QSettings-backed)
    cfg = load_config()

    # Set up the player window controller
    helper_path = os.path.join(os.path.dirname(__file__), "ui", "player_window", "player_window.py")
    player_controller = PlayerController(helper_path)

    # Create necessary states
    display_state = DisplayState(on_persist=lambda d: setattr(cfg, "displayState", d), is_receiver=True)
    display_state.sender = player_controller
    initiative_controller = InitiativeController()

    # Load persistence
    display_state.load_state(cfg.displayState)
    display_state.is_receiver = False  # We start as the receiver to load init state, then swap once that's done.
    player_controller.connected.connect(lambda: display_state.load_state(cfg.displayState))  # Connect so state propagates immediately to player window
    initiative_controller.load_state(cfg.initiativeState)

    # Open database (last used or default) and remember it
    db = DatabaseManager()
    db_path = Path(cfg.last_db_path if cfg.last_db_path else DEFAULT_DB)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db.open(db_path, create_if_missing=True)
    cfg.last_db_path = str(db_path)

    # Construct and show the main window (pass db so widgets can use it)
    win = MainWindow(cfg=cfg, dbm=db, player=player_controller,
                     display_state=display_state, initiative_ctl=initiative_controller)
    win.show()

    # Persist settings on quit
    def persist():
        cfg.last_db_path = str(db.path)
        cfg.displayState = display_state.snapshot()
        cfg.initiativeState = initiative_controller.snapshot()
        save_config(cfg)

    player_controller.disconnected.connect(lambda: persist())
    app.aboutToQuit.connect(persist)
    sys.exit(app.exec())
