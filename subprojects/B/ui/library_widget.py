from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem, \
    QInputDialog, QLineEdit, QMessageBox

from ui.library_items import create_tree_from_dict, export_tree_to_dict, Node, Leaf


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

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.LIBRARY_FILENAME = "library.json"
        self._library: Node = self._load_library(self.LIBRARY_FILENAME)

        # UI
        root = QVBoxLayout(self)
        actions = QHBoxLayout()
        btn_new_folder = QPushButton("New Folder")
        btn_new_collection = QPushButton("New Album")
        # btn_new_folder.clicked.connect(self._create_folder)
        # btn_new_collection.clicked.connect(self._create_collection)
        actions.addWidget(btn_new_folder)
        actions.addWidget(btn_new_collection)
        actions.addStretch(1)
        root.addLayout(actions)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        # self.tree.setDragEnabled(True)
        # self.tree.setAcceptDrops(True)
        # self.tree.setDropIndicatorShown(True)
        # self.tree.setDefaultDropAction(Qt.MoveAction)
        # self.tree.setDragDropMode(QTreeWidget.DragDrop)
        root.addWidget(self.tree, 1)
        #
        # # Context menu for rename/delete
        # self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)
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
        Path(self.LIBRARY_FILENAME).write_text(data, encoding="utf-8")

    # --------- Tree build helpers ---------
    def _rebuild_tree(self) -> None:
        """ Refresh the tree layout. """
        self.tree.clear()
        self.tree.setHeaderLabels(["name", "type"])

        root_item = self.tree.invisibleRootItem()
        root_item.setData(0, Qt.UserRole, {"type": "Folder", "ref": self._library})

        for child in self._library:
            self._add_tree_node(root_item, child)

    def _add_tree_node(self, parent: QTreeWidgetItem | None, node: Node | Leaf) -> QTreeWidgetItem:
        """ Adds a node to the tree.
        If it is a folder, recurse for children. If album, add images as the leaves.

        Parameters
        ----------
        parent : QTreeWidgetItem or None
            The parent node to add to, None means it will be added to the root.
        name : str
            The name to use for the node.
        node : dict
            The node data for recursion and testing collection/group.
        """
        # Album: object with 'images' array
        if isinstance(node, Leaf):
            item = QTreeWidgetItem([node.label, "Album"])
            item.setData(0, Qt.UserRole, {"type": "Album", "ref": node})
            parent.addChild(item)

            # Add images as children
            for img in node:
                img_item = QTreeWidgetItem(item, [img.label, "Image"])
                img_item.setData(0, Qt.UserRole, {"type": "Album", "ref": img})

            return item

        # Folder: object mapping names → nodes
        if isinstance(node, Node):
            item = QTreeWidgetItem([node.label, "Folder"])
            item.setData(0, Qt.UserRole, {"type": "Folder", "ref": node})
            parent.addChild(item)
            for child_node in node:
                self._add_tree_node(item, child_node)
            return item

        return parent
