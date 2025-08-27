from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal, QMimeData, QUrl, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTreeWidget, QTreeWidgetItem, QFileDialog, QMessageBox, QMenu, QInputDialog
)

LIBRARY_FILENAME = "library.json"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _default_library() -> Dict:
    return {
        "id": _new_id(),
        "type": "group",
        "name": "root",
        "children": [
            {"id": _new_id(), "type": "group", "name": "Folder", "children": [
                {"id": _new_id(), "type": "collection", "name": "Collection", "items": [
                ]}
            ]},
            {"id": _new_id(), "type": "group", "name": "Folder 2", "children": [
                {"id": _new_id(), "type": "collection", "name": "Collection 2", "items": []}
            ]}
        ]
    }


class LibraryWidget(QWidget):
    """
    Virtual library: Groups (folders) contain Groups/Collections; Collections contain image items.
    Features:
    - Create Folder / Create Collection
    - Drag to reorder/move groups/collections (collections remain leaves)
    - Accept drops of images (from right pane) onto a Collection to move/add
    - Context menu: Rename / Delete on groups & collections
    Emits:
    - collectionSelected(dict)
    - imagesDropped(paths: List[str], target_collection_id: str)
    """
    collectionSelected = Signal(dict)
    imagesDropped = Signal(list, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._library: Dict = self._load_library()

        # UI
        root = QVBoxLayout(self)
        actions = QHBoxLayout()
        btn_new_folder = QPushButton("New Folder")
        btn_new_collection = QPushButton("New Collection")
        btn_new_folder.clicked.connect(self._create_folder)
        btn_new_collection.clicked.connect(self._create_collection)
        actions.addWidget(btn_new_folder)
        actions.addWidget(btn_new_collection)
        actions.addStretch(1)
        root.addLayout(actions)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDefaultDropAction(Qt.MoveAction)
        self.tree.setDragDropMode(QTreeWidget.DragDrop)
        root.addWidget(self.tree, 1)

        # Context menu for rename/delete
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)

        self._rebuild_tree()
        self.tree.currentItemChanged.connect(self._on_current_changed)

    # --------- Persistence ---------
    def _load_library(self) -> Dict:
        p = Path(LIBRARY_FILENAME)
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
        return _default_library()

    def save_library(self) -> None:
        Path(LIBRARY_FILENAME).write_text(json.dumps(self._library, indent=2), encoding="utf-8")

    # --------- Tree build helpers ---------
    def _rebuild_tree(self) -> None:
        self.tree.clear()
        root_item = self._make_item(self._library)
        self.tree.addTopLevelItem(root_item)
        self._populate_children(root_item, self._library.get("children", []))
        self.tree.expandItem(root_item)
        # Select first collection if exists
        first_coll = self._find_first_collection(root_item)
        if first_coll:
            self.tree.setCurrentItem(first_coll)

    def _make_item(self, node: Dict) -> QTreeWidgetItem:
        label = node.get("name", "(unnamed)")
        item = QTreeWidgetItem([label])
        item.setData(0, Qt.UserRole, node)
        if node.get("type") == "collection":
            font = item.font(0)
            font.setItalic(True)
            item.setFont(0, font)
        return item

    def _populate_children(self, parent_item: QTreeWidgetItem, children: List[Dict]) -> None:
        for ch in children:
            it = self._make_item(ch)
            parent_item.addChild(it)
            if ch.get("type") == "group":
                self._populate_children(it, ch.get("children", []))

    def _find_first_collection(self, item: QTreeWidgetItem) -> Optional[QTreeWidgetItem]:
        for i in range(item.childCount()):
            c = item.child(i)
            node = c.data(0, Qt.UserRole)
            if node and node.get("type") == "collection":
                return c
            sub = self._find_first_collection(c)
            if sub:
                return sub
        return None

    # --------- Selection ---------
    def _on_current_changed(self, cur: Optional[QTreeWidgetItem], prev: Optional[QTreeWidgetItem]) -> None:
        node = cur.data(0, Qt.UserRole) if cur else None
        if node and node.get("type") == "collection":
            self.collectionSelected.emit(node)

    # --------- Creation ---------
    def _create_folder(self) -> None:
        item = self.tree.currentItem() or self.tree.topLevelItem(0)
        if not item:
            return
        node = item.data(0, Qt.UserRole)
        if node.get("type") == "collection":
            item = item.parent() or self.tree.topLevelItem(0)
            node = item.data(0, Qt.UserRole)
        if node.get("type") != "group":
            return
        new = {"id": _new_id(), "type": "group", "name": "New Folder", "children": []}
        node.setdefault("children", []).append(new)
        new_item = self._make_item(new)
        item.addChild(new_item)
        item.setExpanded(True)
        self.save_library()

    def _create_collection(self) -> None:
        item = self.tree.currentItem() or self.tree.topLevelItem(0)
        if not item:
            return
        node = item.data(0, Qt.UserRole)
        if node.get("type") == "collection":
            item = item.parent() or self.tree.topLevelItem(0)
            node = item.data(0, Qt.UserRole)
        if node.get("type") != "group":
            return
        new = {"id": _new_id(), "type": "collection", "name": "New Collection", "items": []}
        node.setdefault("children", []).append(new)
        new_item = self._make_item(new)
        item.addChild(new_item)
        item.setExpanded(True)
        self.tree.setCurrentItem(new_item)
        self.save_library()

    # --------- Context menu (Rename/Delete) ---------
    def _on_tree_context_menu(self, pos: QPoint) -> None:
        item = self.tree.itemAt(pos)
        if not item:
            return
        node = item.data(0, Qt.UserRole)
        # Protect root from delete
        is_root = (item == self.tree.topLevelItem(0))

        menu = QMenu(self)
        act_rename = menu.addAction("Rename")
        if not is_root:
            act_delete = menu.addAction("Delete")
        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if not chosen:
            return

        if chosen == act_rename:
            current_name = node.get("name", "")
            new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=current_name)
            if ok and new_name and new_name != current_name:
                node["name"] = new_name
                item.setText(0, new_name)
                self.save_library()
        elif not is_root and chosen.text() == "Delete":
            if node.get("type") == "group" and item.childCount() > 0:
                confirm = QMessageBox.question(
                    self, "Delete folder?",
                    "This folder contains subfolders/collections. Delete it and everything inside?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm != QMessageBox.Yes:
                    return
            elif node.get("type") == "collection":
                confirm = QMessageBox.question(
                    self, "Delete collection?",
                    "Delete this collection?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm != QMessageBox.Yes:
                    return
            # Remove from data model
            if self._remove_node_inplace(self._library, node.get("id")):
                parent = item.parent() or self.tree.invisibleRootItem()
                (parent or self.tree.invisibleRootItem()).removeChild(item)
                self.save_library()

    def _remove_node_inplace(self, node: Dict, target_id: str) -> bool:
        """Remove child with id=target_id from 'node' (recursive). Returns True if removed."""
        kids = node.get("children", [])
        for i, ch in enumerate(kids):
            if ch.get("id") == target_id:
                del kids[i]
                node["children"] = kids
                return True
            if ch.get("type") == "group":
                if self._remove_node_inplace(ch, target_id):
                    return True
        return False

    # --------- Drag/drop behavior ---------
    def dropEvent(self, event):
        # External image drop onto collection
        mime: QMimeData = event.mimeData()
        target_item = self.tree.itemAt(event.position().toPoint())
        target_node = target_item.data(0, Qt.UserRole) if target_item else None

        if mime.hasUrls() and target_node and target_node.get("type") == "collection":
            paths = [url.toLocalFile() for url in mime.urls() if url.isLocalFile()]
            if paths:
                self.imagesDropped.emit(paths, target_node["id"])
                event.acceptProposedAction()
                return

        # Internal move handled by base; then rebuild model from tree
        src_items = self.tree.selectedItems()
        super().dropEvent(event)
        if not target_item or not src_items:
            return
        self._library = self._tree_to_dict(self.tree.topLevelItem(0))
        self.save_library()

    # --------- Helpers: tree <-> dict ---------
    def _tree_to_dict(self, item: QTreeWidgetItem) -> Dict:
        node = item.data(0, Qt.UserRole).copy()
        if node.get("type") == "group":
            node["children"] = [self._tree_to_dict(item.child(i)) for i in range(item.childCount())]
        else:
            node["items"] = node.get("items", [])
        return node

    # --------- Public API for image moves ---------
    def add_images_to_collection(self, coll_id: str, paths: List[str]) -> None:
        coll = self._find_collection(self._library, coll_id)
        if not coll:
            return
        for p in paths:
            coll.setdefault("items", []).append({"path": p, "caption": ""})
        self.save_library()
        self._reselect_id(coll_id)

    def move_images_between_collections(self, src_id: str, dst_id: str, paths: List[str]) -> None:
        if src_id == dst_id:
            return
        src = self._find_collection(self._library, src_id)
        dst = self._find_collection(self._library, dst_id)
        if not src or not dst:
            return
        keep = []
        moving = set(paths)
        for it in src.get("items", []):
            if it.get("path") in moving:
                continue
            keep.append(it)
        src["items"] = keep
        for p in paths:
            dst.setdefault("items", []).append({"path": p, "caption": ""})
        self.save_library()
        self._reselect_id(dst_id)

    def update_collection_items(self, coll_id: str, new_items: List[Dict]) -> None:
        coll = self._find_collection(self._library, coll_id)
        if not coll:
            return
        coll["items"] = new_items
        self.save_library()
        self._reselect_id(coll_id)

    def _find_collection(self, node: Dict, coll_id: str) -> Optional[Dict]:
        if node.get("type") == "collection" and node.get("id") == coll_id:
            return node
        for ch in node.get("children", []):
            found = self._find_collection(ch, coll_id)
            if found:
                return found
        return None

    def _reselect_id(self, coll_id: str) -> None:
        def _walk(item: QTreeWidgetItem) -> Optional[QTreeWidgetItem]:
            node = item.data(0, Qt.UserRole)
            if node.get("type") == "collection" and node.get("id") == coll_id:
                return item
            for i in range(item.childCount()):
                got = _walk(item.child(i))
                if got:
                    return got
            return None

        top = self.tree.topLevelItem(0)
        if not top:
            return
        found = _walk(top)
        if found:
            self.tree.setCurrentItem(found)
