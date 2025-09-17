from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, \
    QInputDialog, QLineEdit, QMessageBox, QMenu, QTreeWidgetItem

from db.services.library_service import LibraryService
from .library_items import LibraryTree, FolderItem, AlbumItem, ImageItem, COL_LABEL


class LibraryWidget(QWidget):
    """
    Virtual library: Groups (folders) contain Groups/Collections; Collections contain image items.
    Features:
    - Create Folder / Create Album
    - Drag to reorder/move groups/collections (collections remain leaves)
    - Accept drops of images (from right pane) onto a Collection to move/add
    - Context menu: Rename / Delete on groups & collections
    Emits:
    - collectionSelected(dict)
    - imagesDropped(paths: List[str], target_collection_id: str)
    """

    albumSelected = Signal(str, list)
    imagesDropped = Signal(list, str)

    def __init__(self, service: LibraryService, parent=None) -> None:
        super().__init__(parent)
        self.LIBRARY_FILENAME = None
        self.service = service

        # UI
        root = QVBoxLayout(self)
        actions = QHBoxLayout()
        btn_new_folder = QPushButton("New Folder")
        btn_bew_album = QPushButton("New Album")
        btn_new_folder.clicked.connect(lambda: self._create_node(make_album=False))
        btn_bew_album.clicked.connect(lambda: self._create_node(make_album=True))
        actions.addWidget(btn_new_folder)
        actions.addWidget(btn_bew_album)
        actions.addStretch(1)
        root.addLayout(actions)

        # Set up the tree
        self.tree = LibraryTree(parent=self, service=self.service)
        self.tree.setHeaderHidden(True)
        # self.tree.currentItemChanged.connect(self._on_current_changed)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        root.addWidget(self.tree, 1)

        self._populate_roots()

    # --------- DB → UI population ---------
    def _populate_roots(self) -> None:
        """Set up the root structure of the tree, then populate children."""
        self.tree.clear()
        root = self.tree.visible_root()
        root.setText(COL_LABEL, "root")

        for row in self.service.get_root_items():
            if row.kind == "folder":
                it = FolderItem(row.id, row.name, row.position)
                root.addChild(it)
                self._populate_children(it, row.id)
            else:  # album
                it = AlbumItem(row.id, row.name, row.position)
                root.addChild(it)
                self._populate_album_images(it, row.id)

        root.setExpanded(True)

    def _populate_children(self, parent_item: QTreeWidgetItem, folder_id: int) -> None:
        """Rebuild the children from the database for a folder."""
        parent_item.takeChildren()
        for row in self.service.get_folder_children(folder_id):
            if row.kind == "folder":
                it = FolderItem(row.id, row.name, row.position)
                parent_item.addChild(it)
            else:  # album
                it = AlbumItem(row.id, row.name, row.position)
                parent_item.addChild(it)
                self._populate_album_images(it, row.id)

    def _populate_album_images(self, album_item: AlbumItem, album_id: int) -> None:
        album_item.takeChildren()
        for img_id, caption, pos in self.service.get_album_images(album_id):
            album_item.addChild(ImageItem(img_id, caption, pos))

    def _create_node(self, make_album: bool = False) -> None:
        """ Adds a new node into the LibraryTree.

        Parameters
        ----------
        make_album : bool, default=False
            If the node is an album, default is folder.
        """
        item = self.tree.currentItem() or self.tree.visible_root()
        if item is None:
            return

        # If an Album is selected, create alongside it (i.e., in its parent Folder)
        if isinstance(item, AlbumItem):
            item = item.parent() or self.tree.visible_root()

        # New name dialog
        title = "New Album" if make_album else "New Folder"
        placeholder = "New Album" if make_album else "New Folder"
        name, ok = QInputDialog.getText(self, title, f"{title} name:", QLineEdit.Normal, placeholder)
        if not ok:
            return
        name = name.strip()
        if not name:
            return

        # Ensure uniqueness inside this container
        sibling_labels = {item.child(i).text(0) for i in range(item.childCount())}
        if name in sibling_labels:
            QMessageBox.warning(self, "Name in use", f'A node named "{name}" already exists here.')
            return

        # Get parameters for new item, create in the DB, then add to the tree
        if item == self.tree.visible_root():
            parent_id = None
            index = self.tree.visible_root().childCount()
        else:
            parent_id = item.id
            index = item.childCount()

        if make_album:
            new_id = self.service.create_album(parent_id=parent_id, name=name, position=index)
            it = AlbumItem(new_id, name, index)
        else:
            new_id = self.service.create_folder(parent_id=parent_id, name=name, position=index)
            it = FolderItem(new_id, name, index)

        item.addChild(it)
        item.setExpanded(True)

    def _on_tree_context_menu(self, pos: QPoint) -> None:
        """ Context menu when right-clicking library item.
        Implements the rename and delete actions.

        Parameters
        ----------
        pos : QPoint
            The position clicked on the widget.
        """
        item = self.tree.itemAt(pos)
        if not item:
            return

        # Disallow menu on visible root
        if item is self.tree.visible_root():
            return

        # Ignore Image context menu for now
        if isinstance(item, ImageItem):
            return

        # Validation passed, create the menu
        menu = QMenu(self)
        act_rename = menu.addAction("Rename")
        act_delete = menu.addAction("Delete")
        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if not chosen:
            return

        # Execute the action
        if chosen == act_rename:
            self._on_rename(item)
        elif chosen == act_delete:
            self._on_delete(item)

    def _on_rename(self, item: QTreeWidgetItem):
        """Rename in DB then update the tree item text."""
        current_name = item.text(COL_LABEL)
        new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=current_name)
        if not (ok and new_name and new_name != current_name):
            return

        # Update DB based on item type
        if isinstance(item, FolderItem):
            self.service.rename_folder(item.id, new_name)
        elif isinstance(item, AlbumItem):
            self.service.rename_album(item.id, new_name)
        elif isinstance(item, ImageItem):
            raise NotImplementedError("Haven't yet implemented rename image function.")

        # Update UI text
        item.setText(COL_LABEL, new_name)

    def _on_delete(self, item: QTreeWidgetItem):
        """Delete in DB then remove from the tree."""
        if isinstance(item, FolderItem):
            self.service.delete_folder(item.id, hard=False)

        elif isinstance(item, AlbumItem):
            self.service.delete_album(item.id, hard=False)

        elif isinstance(item, ImageItem):
            raise NotImplementedError("Haven't implemented delete for images.")

        # Finally, remove from UI
        parent = item.parent() or self.tree.invisibleRootItem()
        parent.removeChild(item)

    def _on_current_changed(self, cur: Optional[QTreeWidgetItem], prev: Optional[QTreeWidgetItem]) -> None:
        """ Emits a signal for the selected album. """
        if not cur:
            return
        # Trigger signal for album or image.
        if isinstance(cur, AlbumItem):
            self.albumSelected.emit(cur.label, [cur.child(i) for i in range(cur.childCount())])
        if isinstance(cur, ImageItem):
            cur = cur.parent()
            self.albumSelected.emit(cur.label, [cur.child(i) for i in range(cur.childCount())])

    # --- Album helpers to utilise in the image tab (operate on the *currently selected* album) ---
    def _current_album_item(self) -> AlbumItem | None:
        """ Return the selected QTreeWidgetItem if it is an Album, else None. """
        item = self.tree.currentItem()
        if not item:
            return None
        return item if isinstance(item, AlbumItem) else None

    def get_current_album_images(self) -> list[ImageItem]:
        """ Return the ImageItem list for the selected album (model objects). """
        item = self._current_album_item()
        if not item:
            return []
        return list([item.child(i) for i in range(item.childCount())])

    def add_images_to_current_album(self, paths: list[str]) -> None:
        """ Append paths as ImageItem(s) to the selected album. """
        album = self._current_album_item()
        if not album or not paths:
            return

        for p in paths:
            img = ImageItem(label=Path(p).stem, path=p)
            album.addChild(img)

        album.setExpanded(True)
        self.save_library()

    def remove_images_from_current_album(self, paths: list[str]) -> None:
        """ Remove any ImageItem whose .path is in `paths` from selected album. """
        album = self._current_album_item()
        if not album or not paths:
            return

        for i in range(album.childCount()):
            image: ImageItem = album.child(i)
            if image.path in paths:
                album.removeChild(image)

        self.save_library()

    def reorder_current_album_images(self, new_paths_in_order: list[str]) -> None:
        """Reorder the selected album’s images to match `new_paths_in_order`."""
        item = self._current_album_item()
        if not item:
            return
        album: AlbumItem = item.data(0, Qt.UserRole)["ref"]
        # remap model
        path_to_img = {img.path: img for img in album}
        album._items = [path_to_img[p] for p in new_paths_in_order if p in path_to_img]

        # rebuild UI children in the same order
        # collect existing children
        rows = []
        for i in range(item.childCount()):
            rows.append(item.child(i))
        # drop all
        for ch in rows:
            item.removeChild(ch)
        # re-add in order (images first, any stray non-images later)
        for p in new_paths_in_order:
            # find original UI item for this path
            for ch in rows:
                ch_ref = (ch.data(0, Qt.UserRole) or {}).get("ref")
                if isinstance(ch_ref, ImageItem) and ch_ref.path == p:
                    item.addChild(ch)
                    break
        # append any non-image children back (shouldn't exist under album)
        for ch in rows:
            if ch.parent() is None:
                item.addChild(ch)

        item.setExpanded(True)
        self.save_library()
