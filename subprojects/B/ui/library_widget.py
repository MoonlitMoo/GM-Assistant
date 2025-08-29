from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from PySide6.QtWidgets import QWidget
from jsonschema.validators import Draft202012Validator

from schema import TREE_SCHEMA


def _default_library() -> Dict:
    return {
        "version": "v1",
        "tree": {
            "New Folder": {}
        }
    }


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
        self.LIBRARY_FILENAME = None
        self._library: Dict = self._load_library(self.LIBRARY_FILENAME)

        # UI
        # root = QVBoxLayout(self)
        # actions = QHBoxLayout()
        # btn_new_folder = QPushButton("New Folder")
        # btn_new_collection = QPushButton("New Collection")
        # btn_new_folder.clicked.connect(self._create_folder)
        # btn_new_collection.clicked.connect(self._create_collection)
        # actions.addWidget(btn_new_folder)
        # actions.addWidget(btn_new_collection)
        # actions.addStretch(1)
        # root.addLayout(actions)
        #
        # self.tree = QTreeWidget()
        # self.tree.setHeaderHidden(True)
        # self.tree.setDragEnabled(True)
        # self.tree.setAcceptDrops(True)
        # self.tree.setDropIndicatorShown(True)
        # self.tree.setDefaultDropAction(Qt.MoveAction)
        # self.tree.setDragDropMode(QTreeWidget.DragDrop)
        # root.addWidget(self.tree, 1)
        #
        # # Context menu for rename/delete
        # self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        #
        # self._rebuild_tree()
        # self.tree.currentItemChanged.connect(self._on_current_changed)

    # --------- Persistence ---------
    def _validate_library(self, data : str):
        """ Validates the given text to follow the library tree schema.

        Parameters
        ----------
        data : str
            The json text of the library.

        Raises
        ------
        ValueError
            if invalid schema detected.
        """
        validator = Draft202012Validator(TREE_SCHEMA)
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            lines = []
            for e in errors:
                loc = "/".join(map(str, e.path)) or "<root>"
                lines.append(f"- at {loc}: {e.message}")
            raise ValueError("Invalid image tree:\n" + "\n".join(lines))

    def _load_library(self, json_path: str | None) -> Dict:
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
            return _default_library()

        p = Path(json_path)
        if not p.exists():
            raise FileNotFoundError(f"File {p} doesn't exist")

        data = json.loads(p.read_text(encoding="utf-8"))
        self._validate_library(data)
        return data

    def save_library(self) -> None:
        """ Save the current library to disk. """
        data = json.dumps(self._library, indent=2)
        self._validate_library(data)
        Path(self.LIBRARY_FILENAME).write_text(data, encoding="utf-8")

