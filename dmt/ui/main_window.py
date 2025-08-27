from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QToolBar
)

from dmt.core.config import Config
from .player_window import PlayerWindow
from .image_tab import ImagesTab
from .initiative_tab import InitiativeTab
from .settings_tab import SettingsTab


class MainWindow(QMainWindow):
    """ The main window for the GM to use the tools from. """

    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.setWindowTitle("DM Assistant (v1.0 skeleton)")
        self.resize(1200, 800)

        self.config = cfg
        self.playerWindow: PlayerWindow | None = None

        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)

        # Tabs
        self.images_tab = ImagesTab(self.config)
        self.initiative_tab = InitiativeTab(self.config)
        self.settings_tab = SettingsTab(self.config, on_config_changed=self._apply_settings)

        self._tabs.addTab(self.images_tab, "Images")
        self._tabs.addTab(self.initiative_tab, "Initiative")
        self._tabs.addTab(self.settings_tab, "Settings")

        # Toolbar actions
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, tb)

        # Player window controls
        act_open_player = QAction("Open Player Window", self)
        act_open_player.triggered.connect(self.open_player_window)
        tb.addAction(act_open_player)
        act_close_player = QAction("Close Player Window", self)
        act_close_player.triggered.connect(self.close_player_window)
        tb.addAction(act_close_player)

    def _apply_settings(self) -> None:
        """ Called when settings change; for now, just ensure player window respects windowed/fullscreen """
        if self.playerWindow is not None:
            self.playerWindow.apply_config(self.config)

    def open_player_window(self) -> None:
        """ Create the player window. """
        if self.playerWindow is None:
            self.playerWindow = PlayerWindow(self.config)

    def close_player_window(self) -> None:
        """ Destroy the player window. """
        if self.playerWindow is not None:
            self.playerWindow = self.playerWindow.close()
            self.playerWindow = None
