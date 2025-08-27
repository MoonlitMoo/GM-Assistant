from __future__ import annotations

from PySide6.QtCore import Qt, QPropertyAnimation
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QApplication

from ..core.config import Config


class PlayerWindow(QWidget):
    """ Separate window that contains information for the players. """

    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.setObjectName("PlayerWindow")
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self._cfg = cfg

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setStyleSheet("background-color: black;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._image_label)

        self._fade = QPropertyAnimation(self._image_label, b"windowOpacity", self)
        self._fade.setDuration(300)

        self.apply_config(cfg)

    def apply_config(self, cfg: Config) -> None:
        """Apply windowed vs fullscreen preference."""
        self._cfg = cfg
        if cfg.playerWindowed:
            self.setWindowFlag(Qt.FramelessWindowHint, False)
            self.showNormal()
            self.resize(1024, 768)
        else:
            self.setWindowFlag(Qt.FramelessWindowHint, True)
            self.showFullScreen()

    def set_image(self, path: str) -> None:
        pm = QPixmap(path)
        self._image_label.setPixmap(pm)
        self._image_label.setScaledContents(True)  # simple fit; refine later with Fit/Fill/Actual

    def fade_out_in(self):
        # Simple placeholder fade animation (out then in)
        self._fade.stop()
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.start()
        # NOTE: For a real out->in sequence, chain animations; left simple in skeleton.
