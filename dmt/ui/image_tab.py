from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QSize, QMimeData, QPoint, QUrl
from PySide6.QtGui import QIcon, QPixmap, QDrag
from PySide6.QtWidgets import (
    QWidget, QSplitter, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QListWidget, QListWidgetItem, QTextEdit, QFileDialog, QMessageBox, QMenu, QInputDialog
)

from ..core.config import Config
from .library_widget import LibraryWidget


class ThumbnailList(QListWidget):
    def __init__(self, on_reordered, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.IconMode)
        self.setIconSize(QSize(128, 128))
        self.setResizeMode(QListWidget.Adjust)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self._on_reordered = on_reordered
        self._on_rename = None
        self._on_remove = None

    # hooks set by ImagesTab
    def set_handlers(self, on_rename, on_remove):
        self._on_rename = on_rename
        self._on_remove = on_remove

    def dropEvent(self, event):
        super().dropEvent(event)
        items = []
        for i in range(self.count()):
            it = self.item(i)
            items.append({"path": it.data(Qt.UserRole), "caption": it.data(Qt.UserRole + 1) or ""})
        self._on_reordered(items)

    def startDrag(self, supportedActions):
        drag = QDrag(self)
        mime = QMimeData()
        urls = []
        for it in self.selectedItems():
            p = it.data(Qt.UserRole)
            urls.append(Path(p).as_uri())
        if urls:
            mime.setUrls([QUrl(u) for u in urls])
        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction)

    def _on_context_menu(self, pos: QPoint):
        if self._on_rename is None or self._on_remove is None:
            return
        item = self.itemAt(pos)
        if item is None:
            return
        menu = QMenu(self)
        act_rename = menu.addAction("Rename caption…")
        act_remove = menu.addAction("Remove from collection")
        chosen = menu.exec(self.viewport().mapToGlobal(pos))
        if not chosen:
            return
        if chosen == act_rename:
            self._on_rename(item)
        elif chosen == act_remove:
            self._on_remove([item])


class ImagesTab(QWidget):
    """
    Left: LibraryWidget (virtual groups/collections).
    Right: Thumbnails (selected collection) + Preview/Controls.
    Adds context menus:
      - Library: rename/delete on groups & collections
      - Thumbnails: rename caption / remove from collection
    """
    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self._cfg = cfg

        self._current_collection: Optional[Dict] = None
        self._preview_pixmap: Optional[QPixmap] = None
        self._selected_path: Optional[str] = None

        splitter = QSplitter(Qt.Horizontal, self)

        # Left: Library
        self.library = LibraryWidget()
        self.library.collectionSelected.connect(self._on_collection_selected)
        self.library.imagesDropped.connect(self._on_images_dropped_to_tree)
        splitter.addWidget(self.library)

        # Right: thumbnails + preview/controls
        self._path_label = QLabel("No collection selected")
        self._path_label.setStyleSheet("color: #888; font-style: italic; padding: 4px;")

        right = QSplitter(Qt.Vertical)
        right.addWidget(self._path_label)

        self._thumbs = ThumbnailList(on_reordered=self._on_reordered)
        self._thumbs.set_handlers(self._rename_caption, self._remove_items_explicit)
        self._thumbs.itemClicked.connect(self._on_thumb_clicked)
        right.addWidget(self._thumbs)

        bottom = QWidget()
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(6, 6, 6, 6)
        bl.setSpacing(6)

        self._preview = QLabel("No image selected")
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setMinimumHeight(240)
        bl.addWidget(self._preview, 1)

        row_top = QHBoxLayout()
        btn_add = QPushButton("Add Images…")
        btn_add.clicked.connect(self._add_images)
        btn_remove = QPushButton("Remove Selected")
        btn_remove.clicked.connect(self._remove_selected)
        row_top.addWidget(btn_add)
        row_top.addWidget(btn_remove)
        row_top.addStretch(1)
        bl.addLayout(row_top)

        self._caption = QTextEdit()
        self._caption.setPlaceholderText("Notes / caption (DM only)")
        bl.addWidget(self._caption)

        row_controls = QHBoxLayout()
        self._btn_send = QPushButton("Send to Player")
        self._btn_send.setEnabled(False)
        self._btn_send.clicked.connect(self._send_to_player)

        self._btn_fade = QPushButton("Fade")
        self._btn_fade.clicked.connect(self._fade_player)

        self._btn_black = QPushButton("Blackout")
        self._btn_black.setEnabled(False)

        row_controls.addWidget(self._btn_send)
        row_controls.addWidget(self._btn_fade)
        row_controls.addWidget(self._btn_black)
        bl.addLayout(row_controls)

        right.addWidget(bottom)
        splitter.addWidget(right)
        splitter.setSizes([320, 880])

        lay = QVBoxLayout(self)
        lay.addWidget(splitter)

    # ----------------------- Library interactions -----------------------
    def _on_collection_selected(self, coll: Dict) -> None:
        self._current_collection = coll
        # Build breadcrumb path from the tree
        item = self.library.tree.currentItem()
        if item:
            parts = []
            while item is not None:
                parts.insert(0, item.text(0))
                item = item.parent()
            self._path_label.setText(" > ".join(parts))
        else:
            self._path_label.setText("No collection selected")

        self._reload_thumbs()

    def _on_images_dropped_to_tree(self, paths: List[str], target_collection_id: str) -> None:
        if not self._current_collection:
            self.library.add_images_to_collection(target_collection_id, paths)
            return
        self.library.move_images_between_collections(
            self._current_collection.get("id", ""),
            target_collection_id,
            paths
        )
        if self._current_collection.get("id") != target_collection_id:
            self._reload_thumbs()

    # ----------------------- Thumbnails grid ----------------------------
    def _reload_thumbs(self) -> None:
        self._thumbs.clear()
        self._preview.clear()
        self._preview.setText("No image selected")
        self._btn_send.setEnabled(False)
        if not self._current_collection:
            return
        for it in self._current_collection.get("items", []):
            path = it.get("path", "")
            icon = self._make_icon(path)
            name = Path(path).name or "(unnamed)"
            li = QListWidgetItem(icon, name)
            li.setData(Qt.UserRole, path)
            li.setData(Qt.UserRole + 1, it.get("caption", ""))
            self._thumbs.addItem(li)

    def _on_reordered(self, new_items: List[Dict]) -> None:
        if not self._current_collection:
            return
        self.library.update_collection_items(self._current_collection["id"], new_items)
        self._current_collection["items"] = new_items

    def _on_thumb_clicked(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.UserRole)
        self._selected_path = path
        pm = QPixmap(path)
        if pm.isNull():
            self._preview.setText(path)
            self._preview_pixmap = None
        else:
            self._preview_pixmap = pm
            self._update_preview_scaled()
        self._btn_send.setEnabled(True)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if self._preview_pixmap is not None and not self._preview_pixmap.isNull():
            self._update_preview_scaled()

    def _update_preview_scaled(self) -> None:
        if not self._preview_pixmap:
            return
        scaled = self._preview_pixmap.scaled(
            self._preview.width(), self._preview.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self._preview.setPixmap(scaled)

    def _make_icon(self, path: str) -> QIcon:
        pm = QPixmap(path)
        if not pm.isNull():
            pm = pm.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            return QIcon(pm)
        return QIcon()

    # ----------------------- Buttons: add/remove -------------------------
    def _add_images(self) -> None:
        if not self._current_collection:
            QMessageBox.information(self, "Select collection", "Select a collection to add images.")
            return
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Images",
            "", "Images (*.png *.jpg *.jpeg *.webp *.gif)"
        )
        if not files:
            return
        self.library.add_images_to_collection(self._current_collection["id"], files)
        self._current_collection = self.library._find_collection(self.library._library, self._current_collection["id"])
        self._reload_thumbs()

    def _remove_selected(self) -> None:
        if not self._current_collection:
            return
        selected = self._thumbs.selectedItems()
        if not selected:
            return
        self._remove_items_explicit(selected)

    # ----- Context menu handlers for thumbnails -----
    def _rename_caption(self, item: QListWidgetItem) -> None:
        if not self._current_collection:
            return
        current_caption = item.data(Qt.UserRole + 1) or ""
        new_caption, ok = QInputDialog.getText(self, "Rename caption", "Caption:", text=current_caption)
        if not ok:
            return
        # Update model
        path = item.data(Qt.UserRole)
        new_items: List[Dict] = []
        for it in self._current_collection.get("items", []):
            if it.get("path") == path:
                new_items.append({"path": path, "caption": new_caption})
            else:
                new_items.append(it)
        self.library.update_collection_items(self._current_collection["id"], new_items)
        self._current_collection["items"] = new_items
        # Keep UI item's data in sync
        item.setData(Qt.UserRole + 1, new_caption)

    def _remove_items_explicit(self, items: List[QListWidgetItem]) -> None:
        if not self._current_collection or not items:
            return
        remove_paths = {it.data(Qt.UserRole) for it in items}
        keep = [it for it in self._current_collection.get("items", []) if it.get("path") not in remove_paths]
        self.library.update_collection_items(self._current_collection["id"], keep)
        self._current_collection["items"] = keep
        self._reload_thumbs()

    # ----------------------- Player controls -----------------------------
    def _send_to_player(self):
        if not self._selected_path:
            return
        mw = self.window()
        if hasattr(mw, "playerWindow"):
            if mw.playerWindow is None:
                mw.open_player_window()
            mw.playerWindow.set_image(self._selected_path)
            mw.playerWindow.raise_()
            mw.playerWindow.activateWindow()

    def _fade_player(self) -> None:
        mw = self.window()
        if hasattr(mw, "playerWindow") and mw.playerWindow is not None:
            mw.playerWindow.fade_out_in()
