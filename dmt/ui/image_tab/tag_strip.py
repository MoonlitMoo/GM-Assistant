from __future__ import annotations
from typing import Optional, List

from PySide6.QtCore import Qt, Signal, QSize, QPoint
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QCompleter,
    QLabel, QToolButton, QMenu, QColorDialog, QSizePolicy, QScrollArea, QFrame
)

def _contrast_text_color(hex_color: str) -> str:
    # Simple luminance check for readable text on chip
    try:
        c = hex_color.lstrip("#")
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        # perceived luminance (ITU-R BT.709)
        lum = 0.2126*r + 0.7152*g + 0.0722*b
        return "#000000" if lum > 160 else "#FFFFFF"
    except Exception:
        return "#FFFFFF"

class TagStrip(QWidget):
    """A reusable chip list + add box to view and edit tags for an image."""
    tagAdded = Signal(str)
    tagRemoved = Signal(str)
    tagColorEdited = Signal(str, str)
    tagRenamed = Signal(str, str)

    def __init__(self, tagging_service, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._service = tagging_service
        self._image_id: Optional[int] = None
        self._all_tags_cache: List[str] = []

        # Outer layout
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # Scrollable chip area (wrap)
        self._chips_container = QWidget()
        self._chips_layout = QHBoxLayout(self._chips_container)
        self._chips_layout.setContentsMargins(0, 0, 0, 0)
        self._chips_layout.setSpacing(6)
        self._chips_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(self._chips_container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        root.addWidget(scroll)

        # Add box
        self._input = QLineEdit(self)
        self._input.setPlaceholderText("Add tag…  (comma to add multiple)")
        self._input.returnPressed.connect(self._on_add_from_input)
        self._input.textEdited.connect(self._on_input_edited)
        root.addWidget(self._input)

        self._setup_completer()

    # ---------- public API ----------
    def set_image(self, image_id: Optional[int]) -> None:
        self._image_id = image_id
        self.refresh()

    def refresh(self) -> None:
        # Rebuild chips from service
        for i in reversed(range(self._chips_layout.count() - 1)):  # leave the stretch
            w = self._chips_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        if not self._image_id:
            return

        tags = self._service.get_tags_for_image(self._image_id)
        for t in tags:
            self._chips_layout.insertWidget(self._chips_layout.count() - 1, self._make_chip(t.name, t.color_hex))

    # ---------- internals ----------
    def _setup_completer(self) -> None:
        self._all_tags_cache = [t.name for t in self._service.list_tags(limit=200)]
        self._completer = QCompleter(self._all_tags_cache, self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._input.setCompleter(self._completer)

    def _update_completer(self) -> None:
        # lightweight refresh when user types
        q = self._input.text().strip()
        if not q:
            return
        names = [t.name for t in self._service.list_tags(query=q, limit=50)]
        if names != self._all_tags_cache:
            self._all_tags_cache = names
            self._completer.model().setStringList(self._all_tags_cache)

    def _on_input_edited(self, _text: str) -> None:
        self._update_completer()

    def _on_add_from_input(self) -> None:
        if self._image_id is None:
            return
        text = self._input.text().strip()
        if not text:
            return
        # support comma-separated multi-add
        to_add = [s.strip() for s in text.split(",") if s.strip()]
        added = self._service.add_tags_to_image(self._image_id, to_add)
        self._input.clear()
        self.refresh()
        # emit per-tag for external observers
        for t in added:
            self.tagAdded.emit(t.name)

    def _make_chip(self, name: str, color_hex: Optional[str]) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(8, 2, 6, 2)
        lay.setSpacing(6)

        lbl = QLabel(name, w)
        bg = color_hex or "#5a5a5a"
        fg = _contrast_text_color(bg)
        lbl.setStyleSheet(
            f"QLabel {{ background-color: {bg}; color: {fg}; border-radius: 10px; padding: 2px 8px; }}"
        )

        btn = QToolButton(w)
        btn.setText("×")
        btn.setAutoRaise(True)
        btn.setFixedSize(QSize(18, 18))
        btn.clicked.connect(lambda: self._remove_tag(name))

        # context menu for color / rename
        lbl.setContextMenuPolicy(Qt.CustomContextMenu)
        lbl.customContextMenuRequested.connect(lambda p: self._open_chip_menu(lbl, name))

        lay.addWidget(lbl)
        lay.addWidget(btn)
        return w

    def _open_chip_menu(self, owner: QWidget, name: str) -> None:
        menu = QMenu(owner)
        act_color = QAction("Set colour…", menu)
        act_rename = QAction("Rename…", menu)
        menu.addAction(act_color)
        menu.addAction(act_rename)

        act_color.triggered.connect(lambda: self._edit_color(name))
        act_rename.triggered.connect(lambda: self._rename_tag(name))
        menu.exec(owner.mapToGlobal(QPoint(0, owner.height())))

    def _remove_tag(self, name: str) -> None:
        if self._image_id is None:
            return
        self._service.remove_tags_from_image(self._image_id, [name])
        self.tagRemoved.emit(name)
        self.refresh()

    def _edit_color(self, name: str) -> None:
        col = QColorDialog.getColor(parent=self)
        if not col.isValid():
            return
        hexc = col.name()
        self._service.update_tag(name, color_hex=hexc)
        self.tagColorEdited.emit(name, hexc)
        self.refresh()

    def _rename_tag(self, old_name: str) -> None:
        # minimal inline rename dialog via QInputDialog would be fine;
        # here we keep it UX-agnostic—call your own dialog if preferred.
        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "Rename Tag", f"Rename “{old_name}” to:")
        if not ok or not new_name.strip():
            return
        updated = self._service.update_tag(old_name, new_name=new_name.strip())
        self.tagRenamed.emit(old_name, updated.name)
        self.refresh()
