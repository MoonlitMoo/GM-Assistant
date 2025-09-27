from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSlider


class MiniPlayer(QWidget):
    """Reusable mini-player bar (use this in the Images tab)."""

    def __init__(self, player_service=None, parent=None):
        super().__init__(parent)
        self.player = player_service

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)

        self.btn_prev = QPushButton("⏮")
        self.btn_play = QPushButton("⏯")
        self.btn_next = QPushButton("⏭")
        self.lbl = QLabel("—")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)

        lay.addWidget(self.btn_prev)
        lay.addWidget(self.btn_play)
        lay.addWidget(self.btn_next)
        lay.addWidget(self.lbl, 1)
        lay.addWidget(self.slider, 2)

        self.btn_prev.clicked.connect(lambda: getattr(self.player, "prev", lambda: None)())
        self.btn_next.clicked.connect(lambda: getattr(self.player, "next", lambda: None)())
        self.btn_play.clicked.connect(lambda: getattr(self.player, "toggle", lambda: None)())
        self.slider.sliderReleased.connect(self._seek)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    def _tick(self):
        if not self.player:
            return
        np = getattr(self.player, "get_now_playing", lambda: None)()
        if np:
            self.lbl.setText(f"{np.get('title','—')} — {np.get('artist','')}")
        else:
            self.lbl.setText("—")
        dur = np.get("duration_ms") if np else 0
        pos = getattr(self.player, "get_position_ms", lambda: 0)()
        self.slider.blockSignals(True)
        self.slider.setValue(int(1000 * (pos / dur)) if dur else 0)
        self.slider.blockSignals(False)

    def _seek(self):
        if not self.player:
            return
        np = getattr(self.player, "get_now_playing", lambda: None)()
        if not np:
            return
        dur = np.get("duration_ms") or 0
        target = int(dur * (self.slider.value() / 1000.0))
        getattr(self.player, "seek", lambda _ms: None)(target)
