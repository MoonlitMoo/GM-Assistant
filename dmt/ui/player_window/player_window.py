from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget, QVBoxLayout

from .display_state import ScaleMode
from .image_display import ImageDisplayWidget

class PlayerWindow(QWidget):
    """Separate top-level window shown to players."""

    def __init__(self, display_state, parent=None):
        super().__init__(parent)
        self._display_state = display_state

        # child canvas for all image work
        self._canvas = ImageDisplayWidget(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._canvas)

        # Apply state and subscribe
        self._canvas.set_scale_mode(self._display_state.scale_mode())
        self._display_state.scaleModeChanged.connect(self._canvas.set_scale_mode)
        self._display_state.windowedChanged.connect(self._apply_window_mode)
        self._display_state.blackoutChanged.connect(self._canvas.blackout)

        # Apply current window mode on start
        self._apply_window_mode(self._display_state.windowed())

    # ---- public proxies for convenience ----
    def set_image_qimage(self, img): self._canvas.set_image_qimage(img)
    def set_image_bytes(self, *a, **k): return self._canvas.set_image_bytes(*a, **k)
    def set_scale_mode(self, mode: ScaleMode): self._canvas.set_scale_mode(mode)
    def blackout(self, on: bool, *, fade_ms: int | None = None): self._canvas.blackout(on, fade_ms=fade_ms)

    # ---- window sizing logic ----
    def _apply_window_mode(self, windowed: bool):
        """Switch between normal resizable window and fullscreen on the chosen screen."""
        if windowed:
            self.setWindowFlags(
                Qt.Window
                | Qt.WindowTitleHint
                | Qt.WindowSystemMenuHint
                | Qt.WindowMinMaxButtonsHint
                | Qt.WindowCloseButtonHint
            )
            self.showNormal()
            self.resize(1024, 768)
        else:
            screens = QGuiApplication.screens() or []
            idx = max(0, min(self._display_state.display_index(), len(screens) - 1))
            target = screens[idx] if screens else QGuiApplication.primaryScreen()
            if self.windowHandle():
                self.windowHandle().setScreen(target)
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
            self.setGeometry(target.geometry())
            self.showFullScreen()
