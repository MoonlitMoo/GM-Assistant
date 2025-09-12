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

    # Open database (last used or default) and remember it
    db = DatabaseManager()
    db_path = _choose_initial_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db.open(db_path, create_if_missing=True)
    set_last_db_path(db_path)

    # Construct and show the main window (pass db so widgets can use it)
    win = MainWindow(cfg, db=db)
    win.show()

    # Persist settings on quit
    def persist():
        save_config(win.config)
        # Optionally ensure we store whatever DB the app ended with:
        if db.path:
            set_last_db_path(db.path)

    app.aboutToQuit.connect(persist)
    sys.exit(app.exec())
