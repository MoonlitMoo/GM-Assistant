from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QComboBox

from dmt.ui.player_window import ScaleMode


class ScaleModeButton(QComboBox):
    modeChanged = Signal(ScaleMode)

    def __init__(self, initial=ScaleMode.FIT, parent=None):
        super().__init__(parent)
        for mode in ScaleMode:
            self.addItem(mode.value.capitalize(), mode)
        self.setCurrentIndex(self.findData(initial))
        self.currentIndexChanged.connect(self._on_changed)

    def _on_changed(self, idx):
        mode = self.itemData(idx)
        self.modeChanged.emit(mode)


class BlackoutButton(QPushButton):
    """A toggle button styled for blackout control."""

    def __init__(self, parent=None):
        super().__init__("Blackout", parent)
        self.setCheckable(True)
        self.setChecked(False)
        self.setToolTip("Toggle blackout overlay")

        self.setStyleSheet("""
                    QPushButton {
                        background-color: white;
                        color: black;
                        border: 1px solid #555;
                        padding: 4px 10px;
                        border-radius: 6px;
                    }
                    QPushButton:checked {
                        background-color: black;
                        color: white;
                        border: 1px solid #222;
                    }
                """)
