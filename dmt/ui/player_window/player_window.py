from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication

from dmt.core import DisplayState
from .player_canvas import PlayerCanvas
from .initiative_overlay import InitiativeOverlay


class PlayerWindow(QWidget):
    """Separate top-level window shown to players."""

    def __init__(self, display_state: DisplayState):
        super().__init__(None)
        self.setWindowTitle("DM Assistant (Player)")
        self._display_state = display_state

        # child canvas for all image work
        self._canvas = PlayerCanvas(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._canvas)

        # HUD overlay for initiative tracker
        self._init_overlay = InitiativeOverlay(self)
        self._init_overlay.hide()

        # Subscribe to state changes
        self._display_state.scaleModeChanged.connect(self._canvas.set_scale_mode)
        self._display_state.transitionModeChanged.connect(self._canvas.set_transition_mode)
        self._display_state.windowedChanged.connect(self._apply_window_mode)
        self._display_state.imageChanged.connect(self._canvas.set_image_bytes)
        self._display_state.blackoutChanged.connect(self._canvas.blackout)
        self._display_state.initiativeChanged.connect(self._on_initiative_changed)
        self._display_state.initiativeOverlayChanged.connect(lambda *args, **kwargs: self._init_overlay.set_overlay_params(*args, **kwargs))
        self._display_state.bringToFront.connect(self.bring_to_front)

        # Apply current window mode on start
        self.setWindowFlag(Qt.WindowDoesNotAcceptFocus, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)
        self._apply_window_mode(self._display_state.windowed())


    # ---- Initiative Overlay API ----
    def show_initiative_overlay(self, names, idx, round_num=None):
        self._init_overlay.set_entries(names, idx, round_num)
        self._init_overlay.show()

    def update_initiative_overlay(self, names, idx, round_num=None):
        self._init_overlay.set_entries(names, idx, round_num)
        if not self._init_overlay.isVisible():
            self._init_overlay.show()

    def hide_initiative_overlay(self):
        self._init_overlay.hide()

    # ---- Internal state handling ----
    def _on_initiative_changed(self, names: list, current_idx: int, round: int, visible: bool):
        if visible and names:
            self.show_initiative_overlay(names, current_idx, round)
        else:
            self.hide_initiative_overlay()

    # ---- window sizing logic ----
    def _apply_window_mode(self, windowed: bool):
        """Switch between normal resizable window and fullscreen on the chosen screen."""
        if windowed:
            self.setWindowFlags(
                Qt.Window |
                Qt.WindowTitleHint | Qt.WindowSystemMenuHint |
                Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint
            )
            self.showNormal()
            self.resize(1024, 768)
        else:
            screens = QGuiApplication.screens() or []
            target = self.windowHandle().screen()
            idx = screens.index(target)
            self._display_state.set_display_index(idx)
            if self.windowHandle():
                self.windowHandle().setScreen(target)
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
            self.setGeometry(target.geometry())
            self.showFullScreen()


    def bring_to_front(self, focus=False):
        """ Small function to bring to front without resetting geometry, since its a tool window. """
        g = self.geometry()

        # if minimized/hidden, restore to normal first
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.showNormal()  # ensures it's visible (also clears Hidden)
        self.raise_()  # raise in Z-order

        # restore geometry (Qt can change it on showNormal)
        if g.isValid():
            self.setGeometry(g)

        if focus:
            # request focus explicitly
            self.setWindowState(self.windowState() | Qt.WindowActive)
            self.activateWindow()
            QApplication.setActiveWindow(self)
