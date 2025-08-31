from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtCore import Qt, QPoint, QMimeData
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem, \
    QInputDialog, QLineEdit, QMessageBox, QMenu

from ui.library_items import create_tree_from_dict, export_tree_to_dict, Node, Leaf, Image


class LibraryTree(QTreeWidget):
    """ Tree with guarded internal drag/drop.
    Drag and drop events are checked with the owner, LibraryWidget, to ensure that the move is valid.
    """
    def __init__(self, owner: "LibraryWidget"):
        super().__init__(owner)
        self.owner = owner
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)
        # We manage the move ourselves (not using InternalMove)
        self.setDragDropMode(QTreeWidget.DragDrop)

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        pos = event.position().toPoint()
        dst_item = self.itemAt(pos)
        src_items = self.selectedItems()
        if dst_item and src_items and self.owner._is_valid_drop(src_items[0], dst_item):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        pos = event.position().toPoint()
        dst_item = self.itemAt(pos) or self.topLevelItem(0)  # fallback to visible root
        src_items = self.selectedItems()
        if not (dst_item and src_items and self.owner._is_valid_drop(src_items[0], dst_item)):
            event.ignore()
            return
        self.owner._handle_internal_move(src_items[0], dst_item)
        event.acceptProposedAction()


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

    # collectionSelected = Signal(dict)
    # imagesDropped = Signal(list, str)

    def __init__(self, parent=None, filename: str = "library.json") -> None:
        super().__init__(parent)
        self.LIBRARY_FILENAME = filename
        self._library: Node = self._load_library(self.LIBRARY_FILENAME)

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

        self.tree = LibraryTree(self)
        self.tree.setHeaderHidden(True)
        root.addWidget(self.tree, 1)

        # Context menu for rename/delete
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        #
        self._rebuild_tree()
        # self.tree.currentItemChanged.connect(self._on_current_changed)

    # --------- Persistence ---------
    def _load_library(self, json_path: str | None) -> Node:
        """ Loads a library from the given path. If no path given, returns a default setup.

        Parameters
        ----------
        json_path : str or None
            The path to load, or None to use default library.

        Returns
        -------
        data : Node
            The loaded library data.
        """
        if json_path is None:
            return Node("root")

        p = Path(json_path)
        if not p.exists():
            raise FileNotFoundError(f"File {p} doesn't exist")

        data = json.loads(p.read_text(encoding="utf-8"))
        root_node = create_tree_from_dict(data)
        return root_node

    def save_library(self) -> None:
        """ Save the current library to disk. """
        data = export_tree_to_dict(self._library)
        Path(self.LIBRARY_FILENAME).write_text(json.dumps(data, indent=2), encoding="utf-8")

    # --------- Tree build helpers ---------
    def _rebuild_tree(self) -> None:
        """ Refresh the tree layout.
        We use a visible root, which we prevent collapses to allow new folders to be created at root level.
        Then add all the nodes from the library into the tree.
        """
        self.tree.clear()
        self.tree.setHeaderLabels(["name"])

        root_item = self.tree.invisibleRootItem()
        root_item.setData(0, Qt.UserRole, {"type": "Library"})

        # Create the visible root item to allow top level folder creation
        visible_root = QTreeWidgetItem([os.path.splitext(self.LIBRARY_FILENAME)[0], "Folder"])
        visible_root.setData(0, Qt.UserRole, {"type": "Folder", "ref": self._library})
        self.tree.addTopLevelItem(visible_root)
        visible_root.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicatorWhenChildless)
        visible_root.setExpanded(True)
        self.tree.expandItem(visible_root)
        # Set flags to allow drop onto, but not drag/moving of the root
        self._set_item_flags(visible_root)
        visible_root.setFlags((visible_root.flags() | Qt.ItemIsDropEnabled) & ~Qt.ItemIsDragEnabled)

        # Prevent collapse of the visible root item.
        def prevent_collapse(item):
            if item is visible_root:
                self.tree.expandItem(visible_root)

        self.tree.itemCollapsed.connect(prevent_collapse)

        for child in self._library:
            self._add_tree_node(visible_root, child)

    def _add_tree_node(self, parent: QTreeWidgetItem | None, node: Node | Leaf) -> QTreeWidgetItem:
        """ Adds a node to the tree.
        If it is a folder, recurse for children. If album stop recursion, add images.

        Parameters
        ----------
        parent : QTreeWidgetItem or None
            The parent node to add to, None means it will be added to the root.
        node : Node or Leaf
            The node to add to the library.
        """
        # Album: object with 'images' array
        if isinstance(node, Leaf):
            item = QTreeWidgetItem([node.label, "Album"])
            item.setData(0, Qt.UserRole, {"type": "Album", "ref": node})
            parent.addChild(item)
            self._set_item_flags(item)

            # Add images as children
            for img in node:
                img_item = QTreeWidgetItem(item, [img.label, "Image"])
                img_item.setData(0, Qt.UserRole, {"type": "Album", "ref": img})
                self._set_item_flags(img_item)
            return item

        # Folder: object mapping names → nodes
        if isinstance(node, Node):
            item = QTreeWidgetItem([node.label, "Folder"])
            item.setData(0, Qt.UserRole, {"type": "Folder", "ref": node})
            parent.addChild(item)
            self._set_item_flags(item)
            for child_node in node:
                self._add_tree_node(item, child_node)
            return item

        return parent

    # # --------- Selection ---------
    # def _on_current_changed(self, cur: Optional[QTreeWidgetItem], prev: Optional[QTreeWidgetItem]) -> None:
    #     node = cur.data(0, Qt.UserRole) if cur else None
    #     if node and node.get("type") == "collection":
    #         self.collectionSelected.emit(node)
    #
    # --------- Creation ---------
    def _create_node(self, make_album: bool = False) -> None:
        """Create a new node under the currently selected Folder (or the root).
        Makes a folder by default, but can create album on toggle.

        Parameters
        ----------
        make_album : bool, default=False
            Whether new folder is album or folder
        """
        item = self.tree.currentItem() or self.tree.topLevelItem(0).child(0)
        if not item:
            return

        data = item.data(0, Qt.UserRole) or {}
        node = data.get("ref")

        # If an Album is selected, create alongside it (in its parent Folder).
        if isinstance(node, Leaf):
            item = item.parent() or self.tree.topLevelItem(0)
            data = item.data(0, Qt.UserRole) or {}
            node = data.get("ref")

        if not isinstance(node, Node):
            return  # Only allow creating inside a node

        parent_item = item
        parent_node = node

        # Ask for a name
        if not make_album:
            name, ok = QInputDialog.getText(
                self, "New Folder", "Folder name:", QLineEdit.Normal, "New Folder"
            )
        else:
            name, ok = QInputDialog.getText(
                self, "New Album", "Album name:", QLineEdit.Normal, "New Album"
            )

        if not ok:
            return
        name = name.strip()
        if not name:
            return

        # Ensure unique within this folder
        if name in [c.label for c in parent_node]:
            QMessageBox.warning(self, "Name in use",
                                f'A node named "{name}" already exists in this folder.')
            return

        # Create new node
        if not make_album:
            node = Node(label=name, parent=parent_node)
        else:
            node = Leaf(label=name, parent=parent_node)
        parent_node.add_child(node)

        # Add UI node
        self._add_tree_node(parent_item, node)
        parent_item.setExpanded(True)
        self.save_library()

    # --------- Context menu (Rename/Delete) ---------
    def _on_tree_context_menu(self, pos: QPoint) -> None:
        """ Add the context menu for renaming and deleting folders/albums.
        Ignore if the item is an Image or the visible root.
        """
        item = self.tree.itemAt(pos)
        if not item:
            return
        node = item.data(0, Qt.UserRole).get("ref")
        is_root = (item == self.tree.topLevelItem(0))
        if isinstance(node, Image) or is_root:
            return

        menu = QMenu(self)
        act_rename = menu.addAction("Rename")
        act_delete = menu.addAction("Delete")
        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if not chosen:
            return

        if chosen == act_rename:
            current_name = node.label
            new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=current_name)
            if ok and new_name and new_name != current_name:
                node.label = new_name
                item.setText(0, new_name)
                self.save_library()
        elif chosen == act_delete:
            if isinstance(node, Node):
                confirm = QMessageBox.question(
                    self, "Delete folder?",
                    "This folder contains subfolders/collections. Delete it and everything inside?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm != QMessageBox.Yes:
                    return
            elif isinstance(node, Leaf):
                confirm = QMessageBox.question(
                    self, "Delete album?",
                    "Delete this album?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm != QMessageBox.Yes:
                    return
            # Remove from data model
            node.parent.remove_child(node)
            # Update the ui
            item.parent().removeChild(item)
            self.save_library()

    # --------- Drag/drop behavior ---------
    def _set_item_flags(self, item: QTreeWidgetItem) -> None:
        """ Sets drag and drop flags for a given QTreeWidgetItem

        Parameters
        ----------
        item : QTreeWidgetItem
            The item to set flags to.
        """
        node = item.data(0, Qt.UserRole).get("ref")
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        # All can be dragged
        if isinstance(node, (Node, Leaf, Image)):
            flags |= Qt.ItemIsDragEnabled
        # Image doesn't accept drops
        if isinstance(node, (Node, Leaf)):
            flags |= Qt.ItemIsDropEnabled
        item.setFlags(flags)

    def _is_descendant(self, item: QTreeWidgetItem, possible_ancestor: QTreeWidgetItem) -> bool:
        """ Check if the item is an ancestor of the drop location. """
        p = item.parent()
        while p:
            if p is possible_ancestor:
                return True
            p = p.parent()
        return False

    def _is_valid_drop(self, src_item: QTreeWidgetItem, dst_item: QTreeWidgetItem) -> bool:
        """ Check if the drop is valid between the source and destination.
        Not valid if moving to a descendant of itself.
        Folders and albums can only be moved to folders. Images can only be moved to albums.

        Parameters
        ----------
        src_item : QTreeWidgetItem
            The source to be moved
        dst_item : QTreeWidgetItem
            The destination to be moved to

        Returns
        -------
        bool
            If valid move action.
        """
        if src_item is dst_item or self._is_descendant(dst_item, src_item):
            return False
        src = (src_item.data(0, Qt.UserRole) or {})
        dst = (dst_item.data(0, Qt.UserRole) or {})
        s_node, d_node = src.get("ref"), dst.get("ref")
        # Folders/Albums → Folder only
        if isinstance(s_node, (Node, Leaf)) and isinstance(d_node, Node):
            return True
        # Images → Album only
        if isinstance(s_node, Image) and isinstance(d_node, Leaf):
            return True
        return False

    def _handle_internal_move(self, src_item: QTreeWidgetItem, dst_item: QTreeWidgetItem) -> None:
        """ Handle the internal rearrangement of ui and library nodes.

        Parameters
        ----------
        src_item : QTreeWidgetItem
            The item to move to a new parent.
        dst_item : QTreeWidgetItem
            The destination parent.
        """
        s_node = src_item.data(0, Qt.UserRole).get("ref")
        d_node = dst_item.data(0, Qt.UserRole).get("ref")

        if isinstance(s_node, (Node, Leaf)):
            old_parent_item = src_item.parent()
            if not old_parent_item:
                return  # Skip if there isn't a parent
            # Move library node to new parent
            old_parent_node = old_parent_item.data(0, Qt.UserRole).get("ref")
            old_parent_node.remove_child(s_node)
            d_node.add_child(s_node)
            # Move ui node to new parent
            old_parent_item.removeChild(src_item)
            dst_item.addChild(src_item)
            dst_item.setExpanded(True)
            self.save_library()

        elif isinstance(s_node, Image):
            old_parent_item = src_item.parent()
            if not old_parent_item:
                return  # Ignore if no parent
            old_album_node = old_parent_item.data(0, Qt.UserRole).get("ref")
            new_album_node = d_node
            # Move library image to new node
            old_album_node.images.remove(s_node)
            new_album_node.images.append(s_node)
            # Update UI node
            old_parent_item.removeChild(src_item)
            dst_item.addChild(src_item)
            dst_item.setExpanded(True)
            self.save_library()

    # def dropEvent(self, event):
    #     # External image drop onto collection
    #     mime: QMimeData = event.mimeData()
    #     target_item = self.tree.itemAt(event.position().toPoint())
    #     target_node = target_item.data(0, Qt.UserRole) if target_item else None
    #
    #     if mime.hasUrls() and target_node and target_node.get("type") == "collection":
    #         paths = [url.toLocalFile() for url in mime.urls() if url.isLocalFile()]
    #         if paths:
    #             self.imagesDropped.emit(paths, target_node["id"])
    #             event.acceptProposedAction()
    #             return
    #
    #     # Internal move handled by base; then rebuild model from tree
    #     src_items = self.tree.selectedItems()
    #     super().dropEvent(event)
    #     if not target_item or not src_items:
    #         return
    #     self._library = self._tree_to_dict(self.tree.topLevelItem(0))
    #     self.save_library()
    #
    # # --------- Helpers: tree <-> dict ---------
    # def _tree_to_dict(self, item: QTreeWidgetItem) -> Dict:
    #     node = item.data(0, Qt.UserRole).copy()
    #     if node.get("type") == "group":
    #         node["children"] = [self._tree_to_dict(item.child(i)) for i in range(item.childCount())]
    #     else:
    #         node["items"] = node.get("items", [])
    #     return node
    #
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
