import json
import sys
from typing import Any

from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtNetwork import QLocalSocket
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication

from dmt.ui.player_window.display_state import ScaleMode, DisplayState
from dmt.ui.player_window.display_view import DisplayView
from dmt.ui.player_window.initiative_overlay import InitiativeOverlay


class PlayerWindow(QWidget):
    """Separate top-level window shown to players."""

    def __init__(self, display_state: DisplayState):
        super().__init__(None)
        self._display_state = display_state

        # child canvas for all image work
        self._canvas = DisplayView(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._canvas)

        # HUD overlay for initiative tracker
        self._init_overlay = InitiativeOverlay(self)
        self._init_overlay.hide()
        self._init_overlay.resized.connect(self._position_initiative_overlay)

        # Apply initial state
        self._canvas.set_scale_mode(self._display_state.scale_mode())
        self._canvas.set_transition_mode(self._display_state.transition_mode())
        self._on_initiative_changed(self._display_state.initiative_items(), self._display_state.initiative_index(),
                                    self._display_state.initiative_round(), self._display_state.initiative_visible())

        # Subscribe to state changes
        self._display_state.scaleModeChanged.connect(self._canvas.set_scale_mode)
        self._display_state.transitionModeChanged.connect(self._canvas.set_transition_mode)
        self._display_state.windowedChanged.connect(self._apply_window_mode)
        self._display_state.imageChanged.connect(self.set_image_bytes)
        self._display_state.blackoutChanged.connect(self._canvas.blackout)
        self._display_state.initiativeChanged.connect(self._on_initiative_changed)
        self._display_state.bringToFront.connect(self.bring_to_front)

        # Apply current window mode on start
        self.setWindowFlag(Qt.WindowDoesNotAcceptFocus, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)
        self._apply_window_mode(self._display_state.windowed())

    # ---- public proxies for convenience ----
    def set_image_qimage(self, img):
        self._canvas.set_image_qimage(img)

    def set_image_bytes(self, *a, **k):
        return self._canvas.set_image_bytes(*a, **k)

    def set_scale_mode(self, mode: ScaleMode):
        self._canvas.set_scale_mode(mode)

    def blackout(self, on: bool, *, fade_ms: int | None = None):
        self._canvas.blackout(on, fade_ms=fade_ms)

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

    def _position_initiative_overlay(self):
        """Anchor overlay in top-right corner of Player window."""
        m = 16  # margin
        if not self._init_overlay:
            return
        w = self._init_overlay.width()
        h = self._init_overlay.height()
        self._init_overlay.move(self.width() - w - m, m)

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

    # ---- overrides ----
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._position_initiative_overlay()

    def closeEvent(self, event):
        if event.spontaneous() and self.parent() is not None:
            self.parent().close_player_window()
        super().closeEvent(event)


class PlayerClient(QtCore.QObject):
    """ The socket to handle receiving the information for the player window display state. """

    def __init__(self, name: str, window: PlayerWindow):
        super().__init__()
        self.sock = QLocalSocket(self)
        self.window = window
        self._buffer = ""
        self.sock.readyRead.connect(self._read)
        self.sock.disconnected.connect(QApplication.quit)
        self.sock.errorOccurred.connect(lambda *_: QApplication.quit())
        self.sock.connectToServer(name)

    def _read(self):
        while self.sock.bytesAvailable():
            chunk = bytes(self.sock.readAll()).decode("utf-8", errors="ignore")
            self._buffer += chunk
            lines = self._buffer.splitlines(keepends=True)
            complete, rest = [], ""
            for ln in lines:
                if ln.endswith("\n"):
                    complete.append(ln.rstrip("\n"))
                else:
                    rest += ln
            self._buffer = rest
            for line in complete:
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                except Exception:
                    continue
                self._dispatch(msg)

    def _dispatch(self, msg: dict[str, Any]):
        method = getattr(self.window._display_state, msg['op'])
        method(*msg['args'], **msg['kwargs'])



def main():
    # argv: player_process.py --socket <name>
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "--socket":
        name = args[1]
    else:
        print("player_process: missing --socket <name>", file=sys.stderr)
        sys.exit(2)

    app = QApplication(sys.argv)
    dp = DisplayState(is_receiver=True)
    win = PlayerWindow(display_state=dp)
    client = PlayerClient(name, win)
    dp.socket = client
    # Show by default; main can immediately resize/move as desired.
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()