from __future__ import annotations

import json
import os
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
        btn_bew_album = QPushButton("New Album")
        btn_new_folder.clicked.connect(lambda: self._create_node(make_album=False))
        btn_bew_album.clicked.connect(lambda: self._create_node(make_album=True))
        actions.addWidget(btn_new_folder)
        actions.addWidget(btn_bew_album)
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
        Path(self.LIBRARY_FILENAME).write_text(json.dumps(data), encoding="utf-8")

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
