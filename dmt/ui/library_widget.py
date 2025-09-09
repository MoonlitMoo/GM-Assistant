from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, \
    QInputDialog, QLineEdit, QMessageBox, QMenu, QTreeWidgetItem

from .library_items import LibraryTree, FolderItem, AlbumItem, ImageItem


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

    def __init__(self, parent=None, filename: str = "library.json") -> None:
        super().__init__(parent)
        self.LIBRARY_FILENAME = filename

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
        data = self._load_library(self.LIBRARY_FILENAME)
        self.tree = LibraryTree.create_tree_from_dict(data)
        self.tree.setHeaderHidden(True)
        self.tree.structureChanged.connect(lambda: self.save_library())
        self.tree.currentItemChanged.connect(self._on_current_changed)

        root.addWidget(self.tree, 1)

        # Context menu for rename/delete
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)

        # Name tree from filename
        base = os.path.splitext(self.LIBRARY_FILENAME)[0]
        if base:
            self.tree.visible_root().label = base

    # --------- Persistence ---------
    def _load_library(self, json_path: str | None) -> dict:
        """ Loads a library from the given path. If no path given, returns a default setup.

        Parameters
        ----------
        json_path : str or None
            The path to load, or None to use default library.

        Returns
        -------
        data : dict
            The loaded library data.
        """
        if json_path is None:
            return {"version": "v1", "tree": {}}
        p = Path(json_path)
        if not p.exists():
            raise FileNotFoundError(f"File {p} doesn't exist")
        return json.loads(p.read_text(encoding="utf-8"))

    def save_library(self) -> None:
        """ Save the current library to disk. """
        data = self.tree.export_tree_to_dict(self.tree)
        Path(self.LIBRARY_FILENAME).write_text(json.dumps(data, indent=2), encoding="utf-8")

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

        # Create & attach the new item
        new_item = AlbumItem(name) if make_album else FolderItem(name)
        item.addChild(new_item)
        item.setExpanded(True)

        self.save_library()

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

        menu = QMenu(self)
        act_rename = menu.addAction("Rename")
        act_delete = menu.addAction("Delete")
        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if not chosen:
            return

        # Rename action
        if chosen == act_rename:
            current_name = item.text(0)
            new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=current_name)
            if ok and new_name and new_name != current_name:
                item.label = new_name  # Label property updates text.
                self.save_library()
        # Delete action
        elif chosen == act_delete:
            if item.childCount() == 0:
                # In the case that the item has no children, just delete it.
                pass
            elif isinstance(item, FolderItem):
                confirm = QMessageBox.question(
                    self, "Delete folder?",
                    "This folder contains subfolders/albums. Delete it and everything inside?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm != QMessageBox.Yes:
                    return
            elif isinstance(item, AlbumItem):
                confirm = QMessageBox.question(
                    self, "Delete album?", "Delete this album?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm != QMessageBox.Yes:
                    return

            parent = item.parent() or self.tree.invisibleRootItem()
            parent.removeChild(item)
            self.save_library()

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
