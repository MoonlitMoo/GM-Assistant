from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QHBoxLayout

from ..core.config import Config


class ImagesTab(QWidget):
    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self._cfg = cfg

        self._selected_path: str | None = None
        self._preview = QLabel("No image selected")
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setMinimumHeight(240)

        btn_pick = QPushButton("Pick Image…")
        btn_pick.clicked.connect(self._pick_image)

        btn_send = QPushButton("Send to Player")
        btn_send.clicked.connect(self._send_to_player)
        btn_send.setEnabled(False)
        self._btn_send = btn_send

        layout = QVBoxLayout(self)
        layout.addWidget(self._preview)

        row = QHBoxLayout()
        row.addWidget(btn_pick)
        row.addWidget(btn_send)
        layout.addLayout(row)

    def _pick_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select image", filter="Images (*.png *.jpg *.jpeg *.webp *.gif)")
        if path:
            self._selected_path = path
            self._preview.setText(path)
            self._btn_send.setEnabled(True)

    def _send_to_player(self) -> None:
        if not self._selected_path:
            return
        # The main window owns/opens the player window. We can bubble via parent chain.
        mw = self.window()
        if hasattr(mw, "playerWindow"):
            if mw.playerWindow is None:
                mw.open_player_window()
            mw.playerWindow.set_image(self._selected_path)
            mw.playerWindow.raise_()
            mw.playerWindow.activateWindow()
