from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout
)

from db.repositories.tag_repo import TagRepo


class TagSongsDialog(QDialog):
    """Add/remove tags for a selection of songs."""

    def __init__(self, tag_repo: TagRepo, parent=None):
        super().__init__(parent)
        self.tag_repo = tag_repo
        self.setWindowTitle("Tag Songs")

        lay = QVBoxLayout(self)
        self.ed_add = QLineEdit()
        self.ed_add.setPlaceholderText("Add tag names (comma separated)")

        self.list_existing = QListWidget()
        self.list_existing.setSelectionMode(QListWidget.MultiSelection)
        self._load_existing_tags()

        self.btn_add_sel = QPushButton("Add Selected")
        self.btn_remove_sel = QPushButton("Remove Selected")

        btns = QHBoxLayout()
        btns.addWidget(self.btn_add_sel)
        btns.addWidget(self.btn_remove_sel)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        lay.addWidget(QLabel("Add by name:"))
        lay.addWidget(self.ed_add)
        lay.addWidget(QLabel("Existing tags:"))
        lay.addWidget(self.list_existing, 1)
        lay.addLayout(btns)
        lay.addWidget(self.buttons)

        self.btn_add_sel.clicked.connect(self._add_sel)
        self.btn_remove_sel.clicked.connect(self._remove_sel)

        self._add_ids: set[int] = set()
        self._add_names: list[str] = []
        self._remove_ids: set[int] = set()

    def _load_existing_tags(self):
        self.list_existing.clear()
        rows = self.tag_repo.song_tag_usage_counts()
        for tid, name, count in rows:
            item = QListWidgetItem(f"{name}  ({count})")
            item.setData(Qt.UserRole, tid)
            self.list_existing.addItem(item)

    def _add_sel(self):
        for it in self.list_existing.selectedItems():
            self._add_ids.add(it.data(Qt.UserRole))

    def _remove_sel(self):
        for it in self.list_existing.selectedItems():
            self._remove_ids.add(it.data(Qt.UserRole))

    def result_sets(self) -> tuple[list[str], list[int], list[int]]:
        # parse add names
        txt = self.ed_add.text().strip()
        names = [t.strip() for t in txt.split(",")] if txt else []
        names = [t for t in names if t]
        self._add_names = names
        return self._add_names, sorted(self._add_ids), sorted(self._remove_ids)
