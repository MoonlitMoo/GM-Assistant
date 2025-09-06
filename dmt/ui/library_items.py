from __future__ import annotations
from typing import Dict, Any, Iterable

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QAbstractItemView

from jsonschema.validators import Draft202012Validator
from .tree_schema import TREE_SCHEMA

# ---- Roles & column setup ----------------------------------------------------
COL_LABEL = 0  # single-column tree; label stored as text(0)

ROLE_KIND = Qt.ItemDataRole.UserRole + 1  # "Folder" | "Album" | "Image"
ROLE_PAYLOAD = Qt.ItemDataRole.UserRole + 2  # dict payload for images, etc.


def validate_library_string(data: dict):
    """ Validates the given dict to follow the library tree schema.

    Parameters
    ----------
    data : str or dict
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


# ---- Tree Items --------------------------------------------------------------
class FolderItem(QTreeWidgetItem):
    """ Folder — may contain FolderItem or AlbumItem. """

    def __init__(self, label: str):
        super().__init__([label])
        self.setData(COL_LABEL, ROLE_KIND, "Folder")
        self.setFlags(self.flags() | Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)

    @property
    def label(self) -> str:
        return self.text(COL_LABEL)

    @label.setter
    def label(self, v: str) -> None:
        self.setText(COL_LABEL, v)


class AlbumItem(QTreeWidgetItem):
    """ Album — may contain ImageItem children."""

    def __init__(self, label: str):
        super().__init__([label])
        self.setData(COL_LABEL, ROLE_KIND, "Album")
        self.setFlags(self.flags() | Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)

    @property
    def label(self) -> str:
        return self.text(COL_LABEL)

    @label.setter
    def label(self, v: str) -> None:
        self.setText(COL_LABEL, v)


class ImageItem(QTreeWidgetItem):
    """ Image item. Stores {'label', 'path'} payload."""

    def __init__(self, label: str, path: str):
        super().__init__([label])
        self.setData(COL_LABEL, ROLE_KIND, "Image")
        self.setData(COL_LABEL, ROLE_PAYLOAD, {"label": label, "path": path})
        self.setFlags(
            (self.flags() | Qt.ItemIsDragEnabled) & ~Qt.ItemIsDropEnabled
        )

    @property
    def label(self) -> str:
        return self.text(COL_LABEL)

    @label.setter
    def label(self, v: str) -> None:
        self.setText(COL_LABEL, v)
        # keep payload label in sync
        payload = dict(self.payload)
        payload["label"] = v
        self.setData(COL_LABEL, ROLE_PAYLOAD, payload)

    @property
    def path(self) -> str:
        return self.payload.get("path", "")

    @property
    def payload(self) -> Dict[str, Any]:
        return self.data(COL_LABEL, ROLE_PAYLOAD) or {}


class LibraryTree(QTreeWidget):
    """ The library tree widget. Shows the tree layout and implements all required logic for this.
    Can load and save directly to file.
    """
    structureChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(1)
        self.setHeaderHidden(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        if self.topLevelItemCount() == 0:
            self.addTopLevelItem(FolderItem("root"))

    # --- helpers --------------------------------------------------------------
    def visible_root(self) -> FolderItem:
        """ The visible root item displayed at the top of the tree. """
        return self.topLevelItem(0)

    # ---- Build from dict ----
    def _load_from_dict(self, library: dict) -> None:
        """ Loads the UI tree from the dictionary representation.

        Parameters
        ----------
        library : dict
            The library dict defining the layout.
        """
        validate_library_string(library)
        # Reset to a clean root
        self.clear()
        root = FolderItem("root")
        self.addTopLevelItem(root)

        def add_node(parent_item: QTreeWidgetItem, label: str, node: Any) -> QTreeWidgetItem:
            # Album: object with 'images' list
            if isinstance(node, dict) and "images" in node and isinstance(node["images"], list):
                album_item = AlbumItem(label)
                parent_item.addChild(album_item)
                for img in node["images"]:
                    # img must be {'label','path'} by schema
                    image_item = ImageItem(label=img["label"], path=img["path"])
                    album_item.addChild(image_item)
                return album_item

            # Folder: dict mapping names -> nodes
            if isinstance(node, dict):
                folder_item = FolderItem(label)
                parent_item.addChild(folder_item)
                for child_name, child_node in node.items():
                    add_node(folder_item, child_name, child_node)
                folder_item.setExpanded(False)
                return folder_item

            # Unknown/invalid types are ignored (schema validation should prevent this)
            return parent_item

        for name, sub in library["tree"].items():
            add_node(root, name, sub)
        root.setExpanded(True)

    # ---- Export to dict ----
    def _to_dict(self) -> dict:
        """ Returns the dictionary representation of the UI to be able to save to a file.

        Returns
        -------
        export : dict
            A saveable dictionary version of the UI.
        """
        def iter_children(item: QTreeWidgetItem) -> Iterable[QTreeWidgetItem]:
            for i in range(item.childCount()):
                yield item.child(i)

        def export_album(album_item: AlbumItem) -> Dict[str, Any]:
            images = []
            for child in iter_children(album_item):
                if child.data(COL_LABEL, ROLE_KIND) == "Image":
                    images.append(child.data(COL_LABEL, ROLE_PAYLOAD))
            return {"images": images}

        def export_folder(folder_item: FolderItem) -> Dict[str, Any]:
            out: Dict[str, Any] = {}
            for child in iter_children(folder_item):
                kind = child.data(COL_LABEL, ROLE_KIND)
                label = child.text(COL_LABEL)
                if kind == "Folder":
                    out[label] = export_folder(child)  # type: ignore[arg-type]
                elif kind == "Album":
                    out[label] = export_album(child)  # type: ignore[arg-type]
            return out

        export = {"version": "v1", "tree": export_folder(self.visible_root())}
        validate_library_string(export)
        return export

    # ---- Static helper functions -----------------------------------
    @staticmethod
    def create_tree_from_dict(library: dict) -> LibraryTree:
        """
        NEW: returns a LibraryTree widget (instead of a pure-Python Node tree).
        """
        tree = LibraryTree()
        tree._load_from_dict(library)
        return tree

    @staticmethod
    def export_tree_to_dict(tree: LibraryTree) -> dict:
        """Export the current QTreeWidget state back to schema dict."""
        return tree._to_dict()

    @staticmethod
    def _kind(item: QTreeWidgetItem | None) -> str:
        """ Get the kind of item Folder/Album/Image. """
        if not item:
            return ""
        return item.data(0, ROLE_KIND) or ""

    @staticmethod
    def _is_descendant(maybe_parent: QTreeWidgetItem, maybe_child: QTreeWidgetItem) -> bool:
        """ Check if the second item is a descendant of the first.

        Parameters
        ----------
        maybe_parent : QTreeWidgetItem
            The potential ancestor.
        maybe_child : QTreeWidgetItem
            The item we want to check if is a descendant.

        Returns
        -------
        bool
        """
        cur = maybe_child.parent()
        while cur:
            if cur is maybe_parent:
                return True
            cur = cur.parent()
        return False

    @staticmethod
    def _allowed_parent(child_kind: str, parent_kind: str) -> bool:
        """ Checks to see if the proposed parent is valid compared to the child.
        Folder: may contain Folder or Album,
        Album: may contain Image,
        Image: no children

        Parameters
        ----------
        child_kind : str
            The type of the child item.
        parent_kind : str
            The type of the proposed parent.

        Returns
        -------
        bool
        """
        if parent_kind == "Folder":
            return child_kind in ("Folder", "Album")
        if parent_kind == "Album":
            return child_kind == "Image"
        return False

    # --- DnD validation core --------------------------------------------------
    def _is_valid_drop(self, src: QTreeWidgetItem, dst: QTreeWidgetItem) -> bool:
        """ Check if the destination item is a valid target for the source to be moved to. """
        if src is dst:
            return False

        src_kind = self._kind(src)
        # Drop target must be a container. If you point at an Image, treat its parent as target.
        dst_eff = dst
        if self._kind(dst) == "Image":
            dst_eff = dst.parent() or self.visible_root()
        dst_kind = self._kind(dst_eff)

        # Never allow moving the visible root; and never drop onto Image directly
        if src is self.visible_root() or dst_eff is None:
            return False

        # No cyclic moves
        if self._is_descendant(src, dst_eff):
            return False

        # Enforce container rules
        if not self._allowed_parent(src_kind, dst_kind):
            return False

        return True

    # --- Qt event overrides ---------------------------------------------------
    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """ Test validity of the drag event. """
        pos = event.position().toPoint()
        dst = self.itemAt(pos) or self.visible_root()
        srcs = self.selectedItems()
        ok = bool(dst and srcs and all(self._is_valid_drop(s, dst) for s in srcs))
        if ok:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """ Perform the gated movement action. """
        pos: QPoint = event.position().toPoint()
        dst = self.itemAt(pos) or self.visible_root()
        srcs = self.selectedItems()
        if not (dst and srcs and all(self._is_valid_drop(s, dst) for s in srcs)):
            event.ignore()
            return

        # Normalize target: if pointing at Image, use its parent container
        if self._kind(dst) == "Image":
            dst = dst.parent() or self.visible_root()

        # Perform the move(s)
        for src in srcs:
            # Remove from old parent
            old_parent = src.parent() or self.invisibleRootItem()
            old_parent.removeChild(src)
            # Insert at end of dst
            dst.addChild(src)
        dst.setExpanded(True)

        # Then emit the tree changed signal
        self.structureChanged.emit()

        # We implemented the move ourselves so end the event with no further actions
        event.accept()
        event.setDropAction(Qt.IgnoreAction)
