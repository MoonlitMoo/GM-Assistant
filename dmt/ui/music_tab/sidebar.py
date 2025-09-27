from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QHBoxLayout, QMenu, QMessageBox
)

from db.repositories.tag_repo import TagRepo
from db.services.song_service import PlaylistService
from db.models.playlist import PlaylistType


class MusicSidebar(QWidget):
    allSongsRequested = Signal()
    playlistSelected = Signal(int, str)
    smartPlaylistSelected = Signal(int, str)
    searchChanged = Signal(str)
    tagsFilterChanged = Signal(list, list, list)  # any_ids, all_ids, not_ids

    def __init__(self, playlist_service: PlaylistService, tag_repo: TagRepo, parent=None):
        super().__init__(parent)
        self.pl = playlist_service
        self.tag_repo = tag_repo

        self._build_ui()
        self._reload_lists()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search library… (press Enter)")
        self.btn_all = QPushButton("All Songs")
        self.lbl_playlists = QLabel("Playlists")
        self.list_playlists = QListWidget()
        self.lbl_smart = QLabel("Smart Lists")
        self.list_smart = QListWidget()
        btns = QHBoxLayout()
        self.btn_new_playlist = QPushButton("New Playlist")
        self.btn_new_smart = QPushButton("New Smart")
        btns.addWidget(self.btn_new_playlist)
        btns.addWidget(self.btn_new_smart)

        lay.addWidget(self.search)
        lay.addWidget(self.btn_all)
        lay.addSpacing(8)
        lay.addWidget(self.lbl_playlists)
        lay.addWidget(self.list_playlists, 1)
        lay.addWidget(self.lbl_smart)
        lay.addWidget(self.list_smart, 1)
        lay.addLayout(btns)

        # Signals
        self.btn_all.clicked.connect(self.allSongsRequested)
        self.search.returnPressed.connect(lambda: self.searchChanged.emit(self.search.text().strip()))
        self.list_playlists.itemClicked.connect(self._on_playlist_clicked)
        self.list_smart.itemClicked.connect(self._on_smart_clicked)
        self.btn_new_playlist.clicked.connect(self._on_new_playlist)
        self.btn_new_smart.clicked.connect(self._on_new_smart)

        # Context menus
        self.list_playlists.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_playlists.customContextMenuRequested.connect(self._on_playlist_menu)
        self.list_smart.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_smart.customContextMenuRequested.connect(self._on_smart_menu)

    def _reload_lists(self):
        self.list_playlists.clear()
        self.list_smart.clear()
        pls = self.pl.list_all()
        for p in pls:
            it = QListWidgetItem(p.name)
            it.setData(Qt.UserRole, p.id)
            it.setData(Qt.UserRole + 1, p.type.value)
            if p.type == PlaylistType.SMART:
                self.list_smart.addItem(it)
            else:
                self.list_playlists.addItem(it)

    # --- Handlers ---

    def _on_playlist_clicked(self, item: QListWidgetItem):
        pid = item.data(Qt.UserRole)
        name = item.text()
        self.playlistSelected.emit(pid, name)

    def _on_smart_clicked(self, item: QListWidgetItem):
        pid = item.data(Qt.UserRole)
        name = item.text()
        self.smartPlaylistSelected.emit(pid, name)

    def _on_new_playlist(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Playlist", "Name:")
        if not ok or not name.strip():
            return
        self.pl.create_manual(name.strip())
        self._reload_lists()

    def _on_new_smart(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Smart List", "Name:")
        if not ok or not name.strip():
            return
        # Minimal empty query: {op: "AND"}
        self.pl.create_smart(name.strip(), {"op": "AND"})
        self._reload_lists()

    def _on_playlist_menu(self, pos):
        item = self.list_playlists.itemAt(pos)
        if not item:
            return
        pid = item.data(Qt.UserRole)
        menu = QMenu(self)
        act_rename = menu.addAction("Rename")
        act_delete = menu.addAction("Delete")
        act = menu.exec(self.list_playlists.mapToGlobal(pos))
        if act == act_rename:
            from PySide6.QtWidgets import QInputDialog
            name, ok = QInputDialog.getText(self, "Rename Playlist", "Name:", text=item.text())
            if ok and name.strip():
                self.pl.rename(pid, name.strip())
                self._reload_lists()
        elif act == act_delete:
            if QMessageBox.question(self, "Delete Playlist", f"Delete '{item.text()}'?") == QMessageBox.Yes:
                self.pl.delete(pid)
                self._reload_lists()

    def _on_smart_menu(self, pos):
        item = self.list_smart.itemAt(pos)
        if not item:
            return
        pid = item.data(Qt.UserRole)
        menu = QMenu(self)
        act_edit = menu.addAction("Edit Query (JSON)…")
        act_delete = menu.addAction("Delete")
        act = menu.exec(self.list_smart.mapToGlobal(pos))
        if act == act_edit:
            from PySide6.QtWidgets import QInputDialog
            p = self.pl.get(pid)
            cur = p.query or {"op": "AND"}
            txt, ok = QInputDialog.getMultiLineText(self, "Smart Query", "JSON:", str(cur))
            if ok:
                import json
                try:
                    parsed = json.loads(txt)
                except Exception as e:
                    QMessageBox.critical(self, "Invalid JSON", str(e))
                    return
                self.pl.update_smart_query(pid, parsed)
        elif act == act_delete:
            if QMessageBox.question(self, "Delete Smart List", f"Delete '{item.text()}'?") == QMessageBox.Yes:
                self.pl.delete(pid)
                self._reload_lists()
