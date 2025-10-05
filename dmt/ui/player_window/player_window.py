from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget, QVBoxLayout

from .display_state import ScaleMode, DisplayState
from .display_view import DisplayView


class PlayerWindow(QWidget):
    """Separate top-level window shown to players."""

    def __init__(self, display_state: DisplayState, parent=None):
        super().__init__(None)
        self._display_state = display_state

        # child canvas for all image work
        self._canvas = DisplayView(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._canvas)

        # Apply state and subscribe
        self._canvas.set_scale_mode(self._display_state.scale_mode())
        self._display_state.scaleModeChanged.connect(self._canvas.set_scale_mode)
        self._display_state.transitionModeChanged.connect(self._canvas.set_transition_mode)
        self._display_state.windowedChanged.connect(self._apply_window_mode)
        self._display_state.blackoutChanged.connect(self._canvas.blackout)

        # Apply current window mode on start
        self.setWindowFlag(Qt.WindowDoesNotAcceptFocus, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._apply_window_mode(self._display_state.windowed())
        self.make_companion_tool()

    # ---- public proxies for convenience ----
    def set_image_qimage(self, img):
        self._canvas.set_image_qimage(img)

    def set_image_bytes(self, *a, **k):
        return self._canvas.set_image_bytes(*a, **k)

    def set_scale_mode(self, mode: ScaleMode):
        self._canvas.set_scale_mode(mode)

    def blackout(self, on: bool, *, fade_ms: int | None = None):
        self._canvas.blackout(on, fade_ms=fade_ms)

    # ---- window sizing logic ----
    def _apply_window_mode(self, windowed: bool):
        """Switch between normal resizable window and fullscreen on the chosen screen."""
        if windowed:
            self.setWindowFlags(
                Qt.Tool | Qt.Window |
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
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.Window)
            self.setGeometry(target.geometry())
            self.showFullScreen()

    def closeEvent(self, event):
        if event.spontaneous() and self.parent() is not None:
            self.parent().close_player_window()
        super().closeEvent(event)

    def make_companion_tool(self):
        # preserve current position/size
        g = self.geometry()

        # Normal chrome + tool behaviour, but independent
        self.setWindowFlags(
            Qt.Tool | Qt.Window |
            Qt.WindowTitleHint |
            Qt.WindowSystemMenuHint |
            Qt.WindowMinMaxButtonsHint |
            Qt.WindowCloseButtonHint
        )

        # Optional: smoother painting on Windows
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)

        self.show()  # reapply flags
        self.setGeometry(g)  # restore exact position

    def bring_to_front(self, focus=False):
        """ Small function to bring to front without resetting geometry, since its a tool window. """
        geom = self.geometry()
        self.show()
        self.raise_()
        self.setGeometry(geom)
        if focus:
            self.activateWindow()
