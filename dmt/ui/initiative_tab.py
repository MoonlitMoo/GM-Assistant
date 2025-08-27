from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from ..core.config import Config


class InitiativeTab(QWidget):
    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self._cfg = cfg
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Initiative tracker will go here (skeleton)."))
