from __future__ import annotations


from typing import List, Optional

from PySide6.QtCore import Qt, QSize, QMimeData, QPoint
from PySide6.QtGui import QIcon, QPixmap, QDrag
from PySide6.QtWidgets import (
    QWidget, QSplitter, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QListWidget, QListWidgetItem, QTextEdit, QFileDialog, QMessageBox, QMenu, QInputDialog, QStyle
)

from db.services.library_service import LibraryService
from dmt.core.config import Config
from .library_items import AlbumItem
from .library_widget import LibraryWidget


class ThumbnailList(QListWidget):
    """
    Grid of thumbnails for the current album.
    Stores per-item:
      - Qt.UserRole      -> image_id (int)
      - Qt.UserRole + 1  -> caption (str)
    """
    # Optional: custom mime type for internal DnD between tree <-> thumbs
    MIME_IMAGE_IDS = "application/x-gm-image-ids"

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
        # TODO: Wire to the UI
        self._on_rename = None
        self._on_remove = None

    def set_handlers(self, on_rename, on_remove):
        self._on_rename = on_rename
        self._on_remove = on_remove

    def dropEvent(self, event):
        """Internal move → emit new order to parent for DB reorder."""
        super().dropEvent(event)
        image_ids_in_order = []
        for i in range(self.count()):
            it = self.item(i)
            image_ids_in_order.append(it.data(Qt.UserRole))
        self._on_reordered(image_ids_in_order)

    def startDrag(self, supportedActions):
        """Stub for cross-widget DnD: package selected image IDs."""
        ids = [it.id for it in self.selectedItems()]
        if not ids:
            return
        drag = QDrag(self)
        mime = QMimeData()
        # TODO: Wire LibraryWidget::dragEnterEvent/dropEvent to read MIME_IMAGE_IDS.
        import json
        mime.setData(self.MIME_IMAGE_IDS, json.dumps(ids).encode("utf-8"))
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
        act_remove = menu.addAction("Remove from album")
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
    def __init__(self, cfg: Config, service: LibraryService) -> None:
        super().__init__()
        self._cfg = cfg
        self._service = service

        self._current_album_id: Optional[int] = None
        self._preview_pixmap: Optional[QPixmap] = None
        self._selected_image_id: Optional[int] = None

        splitter = QSplitter(Qt.Horizontal, self)

        # Left: Library tree
        self.library = LibraryWidget(service=self._service)
        self.library.albumSelected.connect(self._on_album_selected)
        splitter.addWidget(self.library)

        # Right: thumbnails + preview/controls
        self._path_label = QLabel("No album selected")
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
    def _on_album_selected(self, album: AlbumItem) -> None:
        """ Updates the UI when an album is selected.

        Parameters
        ----------
        album : AlbumItem
            The selected album
        """
        if album:
            self._current_album_id = album.id
            # Build breadcrumb path from the tree
            self._path_label.setText(" > ".join(self._service.breadcrumb(self._current_album_id)))
        else:
            self._path_label.setText("No album selected")

        self._reload_thumbs()

    # def _on_images_dropped_to_tree(self, paths: List[str], target_collection_id: str) -> None:
    #     if not self._current_album:
    #         self.library.add_images_to_collection(target_collection_id, paths)
    #         return
    #     self.library.move_images_between_collections(
    #         self._current_album.get("id", ""),
    #         target_collection_id,
    #         paths
    #     )
    #     if self._current_album.get("id") != target_collection_id:
    #         self._reload_thumbs()

    # ----------------------- Thumbnails grid ----------------------------
    def _reload_thumbs(self) -> None:
        """ Resets the thumbnails using the currently selected album. """
        self._thumbs.clear()
        self._preview.clear()
        self._preview.setText("No image selected")
        self._btn_send.setEnabled(False)
        self._selected_image_id = None

        if self._current_album_id is None:
            return

        rows = self._service.get_album_images(self._current_album_id)
        for image_id, caption, _pos in rows:
            pm = QPixmap()
            tb = self._service.get_image_thumb_bytes(image_id)
            if tb:
                pm.loadFromData(tb)
            icon = QIcon(pm) if not pm.isNull() else self.style().standardIcon(QStyle.SP_FileIcon)
            text = caption or f"Image {image_id}"
            li = QListWidgetItem(icon, text)
            li.setData(Qt.UserRole, image_id)
            li.setData(Qt.UserRole + 1, caption or "")
            self._thumbs.addItem(li)

    def _on_thumb_clicked(self, item: QListWidgetItem) -> None:
        """ Get the full image data """
        image_id = item.data(Qt.UserRole)
        self._selected_image_id = image_id

        fb = self._service.get_image_full_bytes(image_id)
        pm = QPixmap()
        loaded = False
        if fb:
            loaded = pm.loadFromData(fb)
        if not loaded:
            tb = self._service.get_image_thumb_bytes(image_id)
            if tb:
                loaded = pm.loadFromData(tb)

        if not loaded or pm.isNull():
            self._preview.setText(f"Image {image_id}")
            self._preview_pixmap = None
        else:
            self._preview_pixmap = pm
            self._update_preview_scaled()

        self._btn_send.setEnabled(True)

    def _update_preview_scaled(self) -> None:
        if not self._preview_pixmap:
            return
        scaled = self._preview_pixmap.scaled(
            self._preview.width(), self._preview.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self._preview.setPixmap(scaled)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if self._preview_pixmap is not None and not self._preview_pixmap.isNull():
            self._update_preview_scaled()

    def _on_reordered(self, ordered_image_ids: List[int]) -> None:
        """Persist new order via LibraryService."""
        if self._current_album_id is None or not ordered_image_ids:
            return
        self._service.reorder_album_images(self._current_album_id, ordered_image_ids)
        # no need to re-query; our UI order is already correct

    # ----------------------- Buttons: add/remove -------------------------
    def _add_images(self) -> None:
        if self._current_album_id is None:
            QMessageBox.information(self, "Select album", "Select an album to add images.")
            return
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Images", "", "Images (*.png *.jpg *.jpeg *.webp *.gif)"
        )
        if not files:
            return
        self._service.add_images_from_paths(self._current_album_id, files)
        self._reload_thumbs()

    def _remove_selected(self) -> None:
        items = self._thumbs.selectedItems()
        if not items:
            return
        self._remove_items_explicit(items)

    def _rename_caption(self, item: QListWidgetItem) -> None:
        """Rename the DB image caption."""
        image_id = item.data(Qt.UserRole)
        old = item.data(Qt.UserRole + 1) or ""
        new, ok = QInputDialog.getText(self, "Rename caption", "Caption:", text=old)
        if not ok:
            return
        self._service.set_image_caption(image_id, new)
        item.setText(new or f"Image {image_id}")
        item.setData(Qt.UserRole + 1, new or "")

    def _remove_items_explicit(self, items: List[QListWidgetItem]) -> None:
        if not items or self._current_album_id is None:
            return
        image_ids = [it.data(Qt.UserRole) for it in items]
        self._service.remove_images_from_album(self._current_album_id, image_ids)
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
