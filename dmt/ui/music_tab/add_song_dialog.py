from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QPlainTextEdit, QDialogButtonBox, QLineEdit, QWidget, QHBoxLayout

from db.models.song import SongSource


class AddSongDialog(QDialog):
    """Add songs by URI or local path (one per line). Title/artist optional fallback."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Songs")

        lay = QVBoxLayout(self)
        self.src_combo = QComboBox()
        self.src_combo.addItems([SongSource.LOCAL.value, SongSource.SPOTIFY.value, SongSource.YOUTUBE.value])

        self.txt_uris = QPlainTextEdit()
        self.txt_uris.setPlaceholderText("Enter one URI or file path per line…")

        meta = QHBoxLayout()
        self.ed_title = QLineEdit()
        self.ed_title.setPlaceholderText("Optional default title")
        self.ed_artist = QLineEdit()
        self.ed_artist.setPlaceholderText("Optional default artist")
        meta.addWidget(self.ed_title)
        meta.addWidget(self.ed_artist)
        meta_w = QWidget(); meta_w.setLayout(meta)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        lay.addWidget(QLabel("Source:"))
        lay.addWidget(self.src_combo)
        lay.addWidget(QLabel("URIs / Paths (one per line):"))
        lay.addWidget(self.txt_uris, 1)
        lay.addWidget(meta_w)
        lay.addWidget(self.buttons)

    def payloads(self) -> list[dict]:
        src = self.src_combo.currentText()
        source = {
            "local": SongSource.LOCAL,
            "spotify": SongSource.SPOTIFY,
            "youtube": SongSource.YOUTUBE,
        }[src]
        title_default = self.ed_title.text().strip() or None
        artist_default = self.ed_artist.text().strip() or None
        out = []
        for line in self.txt_uris.toPlainText().splitlines():
            uri = line.strip()
            if not uri:
                continue
            out.append({
                "title": title_default or uri,
                "artist": artist_default,
                "uri": uri,
                "source": source,
            })
        return out
