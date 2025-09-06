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

    # # --------- Public API for image moves ---------
    # def add_images_to_collection(self, coll_id: str, paths: List[str]) -> None:
    #     coll = self._find_collection(self._library, coll_id)
    #     if not coll:
    #         return
    #     for p in paths:
    #         coll.setdefault("items", []).append({"path": p, "caption": ""})
    #     self.save_library()
    #     self._reselect_id(coll_id)
    #
    # def move_images_between_collections(self, src_id: str, dst_id: str, paths: List[str]) -> None:
    #     if src_id == dst_id:
    #         return
    #     src = self._find_collection(self._library, src_id)
    #     dst = self._find_collection(self._library, dst_id)
    #     if not src or not dst:
    #         return
    #     keep = []
    #     moving = set(paths)
    #     for it in src.get("items", []):
    #         if it.get("path") in moving:
    #             continue
    #         keep.append(it)
    #     src["items"] = keep
    #     for p in paths:
    #         dst.setdefault("items", []).append({"path": p, "caption": ""})
    #     self.save_library()
    #     self._reselect_id(dst_id)
    #
    # def update_collection_items(self, coll_id: str, new_items: List[Dict]) -> None:
    #     coll = self._find_collection(self._library, coll_id)
    #     if not coll:
    #         return
    #     coll["items"] = new_items
    #     self.save_library()
    #     self._reselect_id(coll_id)
    #
    # def _find_collection(self, node: Dict, coll_id: str) -> Optional[Dict]:
    #     if node.get("type") == "collection" and node.get("id") == coll_id:
    #         return node
    #     for ch in node.get("children", []):
    #         found = self._find_collection(ch, coll_id)
    #         if found:
    #             return found
    #     return None
    #
    # def _reselect_id(self, coll_id: str) -> None:
    #     def _walk(item: QTreeWidgetItem) -> Optional[QTreeWidgetItem]:
    #         node = item.data(0, Qt.UserRole)
    #         if node.get("type") == "collection" and node.get("id") == coll_id:
    #             return item
    #         for i in range(item.childCount()):
    #             got = _walk(item.child(i))
    #             if got:
    #                 return got
    #         return None
    #
    #     top = self.tree.topLevelItem(0)
    #     if not top:
    #         return
    #     found = _walk(top)
    #     if found:
    #         self.tree.setCurrentItem(found)
    def _on_current_changed(self, cur: Optional[QTreeWidgetItem], prev: Optional[QTreeWidgetItem]) -> None:
        """ Emits a signal for the selected album. """
        if not cur:
            return
        # Only trigger signal when an AlbumItem is selected
        if isinstance(cur, AlbumItem):
            # Emit the album's dict — could also emit the AlbumItem itself if you prefer
            self.albumSelected.emit(cur.label, [cur.child(i) for i in range(cur.childCount())])
