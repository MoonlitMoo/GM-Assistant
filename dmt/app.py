from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QCoreApplication

from .core.config import load_config, save_config, ORG, APP
from .ui.main_window import MainWindow


def main() -> None:
    # High-DPI friendly defaults
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # Make sure QSettings knows our identity BEFORE first access
    QCoreApplication.setOrganizationName(ORG)
    QCoreApplication.setApplicationName(APP)

    # Load settings-backed config
    cfg = load_config()

    # Create and show main window
    win = MainWindow(cfg)
    win.show()

    # Persist config on close (QSettings backend)
    def persist():
        save_config(win.config)

    app.aboutToQuit.connect(persist)
    sys.exit(app.exec())
