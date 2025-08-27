from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from .core.config import load_config, save_config, CONFIG_PATH
from .ui.main_window import MainWindow


def main() -> None:
    # High-DPI friendly defaults
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # Ensure config directory exists and load config
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    cfg = load_config()

    # Create and show main window
    win = MainWindow(cfg)
    win.show()

    # Persist config on close
    def persist():
        save_config(win.config)

    app.aboutToQuit.connect(persist)
    sys.exit(app.exec())
