from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtWidgets import QWidget, QTableView, QVBoxLayout, QHeaderView, QMenu

from db.models.song import Song


def _fmt_duration(ms: int | None) -> str:
    if not ms or ms <= 0:
        return ""
    sec = ms // 1000
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"


class SongTableModel(QAbstractTableModel):
    COLS = ["Title", "Artist", "Source", "Duration", "Album", "Plays", "Added"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: List[Song] = []

    def set_songs(self, songs: List[Song]):
        self.beginResetModel()
        self._rows = list(songs)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.COLS[section]
        return str(section + 1)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        s = self._rows[index.row()]
        c = index.column()
        if role == Qt.DisplayRole:
            if c == 0:
                return s.title or ""
            if c == 1:
                return s.artist or ""
            if c == 2:
                return s.source.value
            if c == 3:
                return _fmt_duration(s.duration_ms)
            if c == 4:
                return s.album or ""
            if c == 5:
                return str(s.play_count or 0)
            if c == 6:
                # Assume naive UTC datetime; render ISO without tz
                return s.date_added.isoformat(" ", "seconds") if getattr(s, "date_added", None) else ""
        if role == Qt.TextAlignmentRole and c in (3, 5, 6):
            return Qt.AlignRight | Qt.AlignVCenter
        return None

    def song_id_at(self, row: int) -> int | None:
        if 0 <= row < len(self._rows):
            return self._rows[row].id
        return None

    def song_ids_for_rows(self, rows: list[int]) -> list[int]:
        out = []
        for r in rows:
            sid = self.song_id_at(r)
            if sid is not None:
                out.append(sid)
        return out


class SongTableView(QWidget):
    playSongsRequested = Signal(list)      # song_ids
    enqueueSongsRequested = Signal(list)   # song_ids
    playNextRequested = Signal(list)       # song_ids

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self._model = SongTableModel(self)
        self.view = QTableView()
        self.view.setModel(self._model)
        self.view.setSelectionBehavior(QTableView.SelectRows)
        self.view.setSelectionMode(QTableView.ExtendedSelection)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.view.setSortingEnabled(False)  # sorting handled by service for consistency
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._on_ctx_menu)
        lay.addWidget(self.view)

    def model(self) -> SongTableModel:
        return self._model

    def selected_song_ids(self) -> list[int]:
        rows = sorted({idx.row() for idx in self.view.selectionModel().selectedRows()})
        return self._model.song_ids_for_rows(rows)

    def _on_ctx_menu(self, pos):
        ids = self.selected_song_ids()
        if not ids:
            idx = self.view.indexAt(pos)
            if idx.isValid():
                sid = self._model.song_id_at(idx.row())
                if sid is not None:
                    ids = [sid]
        if not ids:
            return
        menu = QMenu(self)
        act_play = menu.addAction("Play Now")
        act_next = menu.addAction("Play Next")
        act_enqueue = menu.addAction("Add to Queue")
        act = menu.exec(self.view.mapToGlobal(pos))
        if act == act_play:
            self.playSongsRequested.emit(ids)
        elif act == act_next:
            self.playNextRequested.emit(ids)
        elif act == act_enqueue:
            self.enqueueSongsRequested.emit(ids)
