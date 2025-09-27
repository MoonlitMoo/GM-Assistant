from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QSlider, QListWidget


class NowPlayingPanel(QWidget):
    """Compact now-playing and queue view. Expects a player_service with a minimal interface."""

    def __init__(self, player_service=None, parent=None):
        super().__init__(parent)
        self.player = player_service

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)

        self.lbl_title = QLabel("—")
        self.lbl_artist = QLabel("")
        self.lbl_title.setStyleSheet("font-weight: 600;")
        lay.addWidget(self.lbl_title)
        lay.addWidget(self.lbl_artist)

        ctrls = QHBoxLayout()
        self.btn_prev = QPushButton("⏮")
        self.btn_play = QPushButton("⏯")
        self.btn_next = QPushButton("⏭")
        ctrls.addWidget(self.btn_prev)
        ctrls.addWidget(self.btn_play)
        ctrls.addWidget(self.btn_next)
        lay.addLayout(ctrls)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        lay.addWidget(self.slider)

        lay.addWidget(QLabel("Queue"))
        self.queue_list = QListWidget()
        lay.addWidget(self.queue_list, 1)

        # polling timer to update position; replace with signals if your player exposes them
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

        self.btn_prev.clicked.connect(lambda: getattr(self.player, "prev", lambda: None)())
        self.btn_next.clicked.connect(lambda: getattr(self.player, "next", lambda: None)())
        self.btn_play.clicked.connect(lambda: getattr(self.player, "toggle", lambda: None)())
        self.slider.sliderReleased.connect(self._seek)

        self.refresh()

    def refresh(self):
        if not self.player:
            return
        np = getattr(self.player, "get_now_playing", lambda: None)()
        if np:
            self.lbl_title.setText(np.get("title") or "—")
            self.lbl_artist.setText(np.get("artist") or "")
        else:
            self.lbl_title.setText("—")
            self.lbl_artist.setText("")
        self.queue_list.clear()
        queue = getattr(self.player, "get_queue", lambda: [])()
        for item in queue or []:
            self.queue_list.addItem(item.get("title", f"Song {item.get('song_id','')}"))

    def _tick(self):
        if not self.player:
            return
        np = getattr(self.player, "get_now_playing", lambda: None)()
        if not np:
            return
        dur = np.get("duration_ms") or 0
        pos = getattr(self.player, "get_position_ms", lambda: 0)()
        self.slider.blockSignals(True)
        self.slider.setValue(int(1000 * (pos / dur)) if dur else 0)
        self.slider.blockSignals(False)

    @Slot()
    def _seek(self):
        if not self.player:
            return
        np = getattr(self.player, "get_now_playing", lambda: None)()
        if not np:
            return
        dur = np.get("duration_ms") or 0
        frac = self.slider.value() / 1000.0
        target = int(dur * frac)
        getattr(self.player, "seek", lambda _ms: None)(target)
