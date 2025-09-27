from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QToolBar, QLineEdit, QPushButton,
    QLabel, QComboBox, QSpinBox, QMessageBox
)

from db.services.song_service import SongService, LibraryQuery, DuplicateUriError, InvalidSourceError
from db.services.song_service import PlaylistService
from db.repositories.tag_repo import TagRepo
from db.services.tagging_service import TaggingService
from db.models.song import SongSource

from .sidebar import MusicSidebar
from .song_table import SongTableView
from .now_playing import NowPlayingPanel
from .add_song_dialog import AddSongDialog
from .tag_songs_dialog import TagSongsDialog


@dataclass
class Selection:
    mode: str  # "all" | "playlist" | "smart" | "image"
    id: Optional[int] = None
    name: Optional[str] = None


class SongTab(QWidget):
    """Music tab: sidebar (library/playlists/smart), songs table, now-playing panel."""

    # Emitted when queue should be replaced or modified (for a PlayerService to consume)
    playSongsRequested = Signal(list)  # list[int] song_ids
    enqueueSongsRequested = Signal(list)  # list[int] song_ids
    playNextRequested = Signal(list)  # list[int] song_ids

    def __init__(
            self,
            song_service: SongService,
            playlist_service: PlaylistService,
            tagging_service: TaggingService,
            player_service=None,
            parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.song_service = song_service
        self.playlist_service = playlist_service
        self.tagging_service = tagging_service
        self.tag_repo = TagRepo()
        self.player = player_service

        self._selection = Selection(mode="all")
        self._page = 0
        self._page_size = 200
        self._sort_field = "date_added"
        self._sort_desc = True
        self._text = ""
        self._tag_any: list[int] = []
        self._tag_all: list[int] = []
        self._tag_not: list[int] = []
        self._sources: set[SongSource] | None = None

        self._build_ui()
        self._wire_signals()
        self.reload()

    # ---------- UI ----------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        self.toolbar = QToolBar()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search title / artist / album / tags…")
        self.btn_add = QPushButton("Add")
        self.btn_tag = QPushButton("Tag…")
        self.btn_delete = QPushButton("Delete")
        self.btn_add_to_playlist = QPushButton("Add to Playlist…")

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["date_added", "title", "artist", "album", "duration_ms", "play_count", "last_played"])
        self.sort_combo.setCurrentText("date_added")
        self.order_combo = QComboBox()
        self.order_combo.addItems(["desc", "asc"])
        self.order_combo.setCurrentText("desc")
        self.page_size_spin = QSpinBox()
        self.page_size_spin.setRange(50, 2000)
        self.page_size_spin.setValue(self._page_size)

        self.toolbar.addWidget(QLabel("Search:"))
        self.toolbar.addWidget(self.search_edit)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(QLabel("Sort:"))
        self.toolbar.addWidget(self.sort_combo)
        self.toolbar.addWidget(self.order_combo)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(QLabel("Page size:"))
        self.toolbar.addWidget(self.page_size_spin)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.btn_add)
        self.toolbar.addWidget(self.btn_tag)
        self.toolbar.addWidget(self.btn_add_to_playlist)
        self.toolbar.addWidget(self.btn_delete)

        root.addWidget(self.toolbar)

        # Split layout: sidebar | table | now-playing
        self.splitter = QSplitter()
        self.splitter.setOrientation(Qt.Horizontal)

        self.sidebar = MusicSidebar(self.playlist_service, self.tag_repo, parent=self)
        self.table = SongTableView(parent=self)
        self.now_playing = NowPlayingPanel(player_service=self.player, parent=self)

        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.table)
        self.splitter.addWidget(self.now_playing)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)

        root.addWidget(self.splitter)

        # Paging footer
        footer = QHBoxLayout()
        self.btn_prev = QPushButton("Prev")
        self.btn_next = QPushButton("Next")
        self.lbl_page = QLabel("Page 1")
        footer.addWidget(self.btn_prev)
        footer.addWidget(self.btn_next)
        footer.addStretch(1)
        footer.addWidget(self.lbl_page)
        footer_w = QWidget()
        footer_w.setLayout(footer)
        root.addWidget(footer_w)

    def _wire_signals(self):
        self.sidebar.allSongsRequested.connect(self._on_all_songs)
        self.sidebar.playlistSelected.connect(self._on_playlist)
        self.sidebar.smartPlaylistSelected.connect(self._on_smart_playlist)
        self.sidebar.searchChanged.connect(self._on_sidebar_search)
        self.sidebar.tagsFilterChanged.connect(self._on_sidebar_tags_filter)

        self.search_edit.returnPressed.connect(self._on_search_enter)
        self.sort_combo.currentTextChanged.connect(self._on_sort_changed)
        self.order_combo.currentTextChanged.connect(self._on_sort_changed)
        self.page_size_spin.valueChanged.connect(self._on_page_size_changed)
        self.btn_prev.clicked.connect(self._go_prev)
        self.btn_next.clicked.connect(self._go_next)

        self.btn_add.clicked.connect(self._on_add_clicked)
        self.btn_tag.clicked.connect(self._on_tag_clicked)
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        self.btn_add_to_playlist.clicked.connect(self._on_add_to_playlist_clicked)

        self.table.playSongsRequested.connect(self.playSongsRequested)
        self.table.enqueueSongsRequested.connect(self.enqueueSongsRequested)
        self.table.playNextRequested.connect(self.playNextRequested)

    # ---------- Events ----------

    @Slot()
    def _on_all_songs(self):
        self._selection = Selection(mode="all")
        self._page = 0
        self.reload()

    @Slot(int, str)
    def _on_playlist(self, playlist_id: int, name: str):
        self._selection = Selection(mode="playlist", id=playlist_id, name=name)
        self._page = 0
        self.reload()

    @Slot(int, str)
    def _on_smart_playlist(self, playlist_id: int, name: str):
        self._selection = Selection(mode="smart", id=playlist_id, name=name)
        self._page = 0
        self.reload()

    @Slot(str)
    def _on_sidebar_search(self, text: str):
        # keep the toolbar search in sync but do not reload on every keystroke
        self.search_edit.setText(text)

    @Slot(list, list, list)
    def _on_sidebar_tags_filter(self, any_ids: list[int], all_ids: list[int], not_ids: list[int]):
        self._tag_any, self._tag_all, self._tag_not = any_ids, all_ids, not_ids

    @Slot()
    def _on_search_enter(self):
        self._text = self.search_edit.text().strip()
        self._page = 0
        self.reload()

    @Slot()
    def _on_sort_changed(self):
        self._sort_field = self.sort_combo.currentText()
        self._sort_desc = (self.order_combo.currentText() == "desc")
        self._page = 0
        self.reload()

    @Slot(int)
    def _on_page_size_changed(self, val: int):
        self._page_size = val
        self._page = 0
        self.reload()

    @Slot()
    def _go_prev(self):
        if self._page > 0:
            self._page -= 1
            self.reload()

    @Slot()
    def _go_next(self):
        self._page += 1
        self.reload()

    # ---------- Actions ----------

    @Slot()
    def _on_add_clicked(self):
        dlg = AddSongDialog(self)
        if dlg.exec():
            items = dlg.payloads()
            if not items:
                return
            try:
                self.song_service.add_songs_bulk(items)
            except DuplicateUriError as e:
                QMessageBox.warning(self, "Duplicate URI", f"A song with this URI already exists:\n{e}")
            except InvalidSourceError as e:
                QMessageBox.critical(self, "Invalid Source", f"Invalid song source: {e}")
            self.reload()

    @Slot()
    def _on_tag_clicked(self):
        sel_ids = self.table.selected_song_ids()
        if not sel_ids:
            QMessageBox.information(self, "No Selection", "Select one or more songs first.")
            return
        dlg = TagSongsDialog(self.tag_repo, parent=self)
        if dlg.exec():
            add_names, add_ids, remove_ids = dlg.result_sets()
            self.song_service.tag_songs(sel_ids, add_tag_names=add_names, add_tag_ids=add_ids,
                                        remove_tag_ids=remove_ids)
            self.reload(preserve_page=True)

    @Slot()
    def _on_delete_clicked(self):
        sel_ids = self.table.selected_song_ids()
        if not sel_ids:
            QMessageBox.information(self, "No Selection", "Select one or more songs first.")
            return
        if QMessageBox.question(self, "Delete Songs",
                                f"Delete {len(sel_ids)} song(s)? This removes them from playlists as well.") != QMessageBox.Yes:
            return
        for sid in sel_ids:
            self.song_service.delete_song(sid)
        self.reload(preserve_page=True)

    @Slot()
    def _on_add_to_playlist_clicked(self):
        from PySide6.QtWidgets import QInputDialog
        sel_ids = self.table.selected_song_ids()
        if not sel_ids:
            QMessageBox.information(self, "No Selection", "Select one or more songs first.")
            return
        # Quick chooser: list manual/image playlists
        pls = self.playlist_service.list_all()
        names = [f"{p.name} ({p.type.value.lower()})" for p in pls]
        if not names:
            QMessageBox.information(self, "No Playlists", "Create a playlist first in the sidebar.")
            return
        name, ok = QInputDialog.getItem(self, "Add to Playlist", "Choose:", names, editable=False)
        if not ok or not name:
            return
        idx = names.index(name)
        target = pls[idx]
        self.playlist_service.add_songs_append(target.id, sel_ids)
        QMessageBox.information(self, "Added", f"Added {len(sel_ids)} song(s) to '{target.name}'.")

    # ---------- Data loading ----------

    def reload(self, preserve_page: bool = False):
        if not preserve_page:
            self._page = max(0, self._page)
        # Load based on selection
        if self._selection.mode == "all":
            q = LibraryQuery(
                text=self._text or None,
                sources=self._sources,
                tag_any=self._tag_any or None,
                tag_all=self._tag_all or None,
                tag_not=self._tag_not or None,
                sort_field=self._sort_field,
                sort_desc=self._sort_desc,
                page=self._page,
                page_size=self._page_size,
            )
            rows, total = self.song_service.browse(q)
        elif self._selection.mode in ("playlist", "image"):
            items = self.playlist_service.items(self._selection.id)
            rows = [it.song for it in items]
            total = len(rows)
        elif self._selection.mode == "smart":
            rows, total = self.playlist_service.evaluate_smart(
                self._selection.id,
                page=self._page, page_size=self._page_size,
                sort_field=self._sort_field, sort_desc=self._sort_desc
            )
        else:
            rows, total = [], 0

        # Update table
        self.table.model().set_songs(rows)
        self.lbl_page.setText(f"Page {self._page + 1} · {len(rows)} / {total}")
