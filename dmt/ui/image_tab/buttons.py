from __future__ import annotations
from PySide6.QtCore import Signal, QObject, Qt
from PySide6.QtGui import QActionGroup, QAction
from PySide6.QtWidgets import QToolButton, QMenu, QPushButton

from dmt.ui.player_window import ScaleMode


class ScaleModeButton(QToolButton):
    """A toolbutton with a dropdown to choose image scale mode (FIT/FILL/STRETCH/ACTUAL)."""
    modeChanged = Signal(ScaleMode)

    def __init__(self, *, initial: ScaleMode = ScaleMode.FIT, parent: QObject | None = None):
        super().__init__(parent)
        self.setText(f"Scale: {initial.value}")
        self.setToolButtonStyle(Qt.ToolButtonTextOnly)   # swap to IconOnly if you add icons
        self.setPopupMode(QToolButton.InstantPopup)

        menu = QMenu(self)
        self.setMenu(menu)

        # Exclusive group so only one mode is checked at a time
        self._group = QActionGroup(self)
        self._group.setExclusive(True)

        # Create actions
        self._actions: dict[ScaleMode, QAction] = {}

        def add_mode(mode: ScaleMode, text: str, tip: str):
            act = QAction(text, self, checkable=True)
            act.setToolTip(tip)
            self._group.addAction(act)
            menu.addAction(act)
            self._actions[mode] = act
            # keep a small lambda to capture mode
            act.triggered.connect(lambda _=False, m=mode: self._on_pick(m))

        add_mode(ScaleMode.FIT,     "Fit (letterbox)", "Keep aspect ratio; show whole image (may add bars).")
        add_mode(ScaleMode.FILL,    "Fill (cover)",    "Keep aspect ratio; fill window (crops overflow).")
        add_mode(ScaleMode.STRETCH, "Stretch",         "Ignore aspect ratio; no bars, no crop (distorts).")
        add_mode(ScaleMode.ACTUAL,  "Actual size",     "1:1 pixels; center without scaling.")

        # Set initial
        self.set_current_mode(initial)

    def set_current_mode(self, mode: ScaleMode) -> None:
        """Update the button's check-state without emitting modeChanged."""
        act = self._actions.get(mode)
        if act and not act.isChecked():
            act.setChecked(True)

    def _on_pick(self, mode: ScaleMode) -> None:
        self.set_current_mode(mode)
        self.setText(f"Scale: {mode.value}")
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
