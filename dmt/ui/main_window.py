from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QToolBar
)

from dmt.db.services.library_service import LibraryService
from dmt.db.services.tagging_service import TaggingService
from dmt.core.config import Config
from dmt.db.manager import DatabaseManager

from .player_window import PlayerWindow
from .image_tab import ImagesTab
from .initiative_tab import InitiativeTab
from .player_window.display_state import DisplayState
from .settings_tab import SettingsTab


class MainWindow(QMainWindow):
    """ The main window for the GM to use the tools from. """

    def __init__(self, cfg: Config, dbm: DatabaseManager, display_state: DisplayState) -> None:
        super().__init__()
        self.setWindowTitle("DM Assistant")
        self.resize(1200, 800)

        self.config = cfg
        self.dbm = dbm
        self.display_state: DisplayState = display_state
        self.playerWindow: PlayerWindow | None = None

        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)

        # Tabs
        self.images_tab = ImagesTab(
            service=LibraryService(self.dbm), tag_service=TaggingService(self.dbm), display_state=self.display_state)
        self.initiative_tab = InitiativeTab(self.config)
        self.settings_tab = SettingsTab(self.dbm, self.display_state)
        self.settings_tab.reloadedDatabase.connect(self.images_tab.library.reload)

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

    def open_player_window(self) -> None:
        """ Create the player window. """
        if self.playerWindow is None:
            self.playerWindow = PlayerWindow(self.display_state)

    def close_player_window(self) -> None:
        """ Destroy the player window. """
        if self.playerWindow is not None:
            self.playerWindow = self.playerWindow.close()
            self.playerWindow = None

    def closeEvent(self, event, /):
        """ Make sure the player window closes too. """
        if self.playerWindow is not None:
            self.close_player_window()
        super().closeEvent(event)
