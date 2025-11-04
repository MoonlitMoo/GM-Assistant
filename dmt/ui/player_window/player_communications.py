from __future__ import annotations
import json, os, sys, subprocess, uuid
from typing import Any

from PySide6 import QtCore
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from dmt.ui.player_window import PlayerWindow


class PlayerController(QtCore.QObject):
    """ Runs the subprocess for the player window and enables sending of json encoded information. """
    connected = QtCore.Signal()
    disconnected = QtCore.Signal()

    def __init__(self, player_script_path: str, *, parent=None):
        super().__init__(parent)
        self._server = QLocalServer(self)
        self._socket: QLocalSocket | None = None
        self._proc: subprocess.Popen | None = None
        self._name = f"gm_assistant_player_{uuid.uuid4().hex}"
        self._player_script_path = player_script_path

        # On *nix, leftover sockets can exist—remove if so:
        QLocalServer.removeServer(self._name)

        self._server.newConnection.connect(self._on_new_conn)
        if not self._server.listen(self._name):
            raise RuntimeError("Failed to start QLocalServer")

    def start(self):
        # Launch the helper process
        args = [sys.executable, self._player_script_path, "--socket", self._name]
        # For Windows you may prefer creationflags to hide console if using python.exe:
        # creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        creationflags = 0
        self._proc = subprocess.Popen(args, creationflags=creationflags)

    def stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()

    def is_running(self) -> bool:
        """Return True if the player process is still running."""
        if self._proc is None:
            return False
        return self._proc.poll() is None

    def _on_new_conn(self):
        if self._socket:
            # Only accept a single player connection; reject extras.
            extra = self._server.nextPendingConnection()
            extra.close()
            return
        self._socket = self._server.nextPendingConnection()
        self._socket.disconnected.connect(self._on_disconnect)
        self.connected.emit()

    def _on_disconnect(self):
        self._socket = None
        self.disconnected.emit()

    def send(self, obj: dict):
        if not self._socket:
            return
            raise RuntimeError("Player not connected yet")
        data = (json.dumps(obj) + "\n").encode("utf-8")
        self._socket.write(data)
        self._socket.flush()


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
