from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, \
    QInputDialog, QLineEdit, QMessageBox, QMenu, QTreeWidgetItem

from dmt.db.services.library_service import LibraryService
from .library_items import FolderItem, AlbumItem, ImageItem, COL_LABEL
from .library_tree import LibraryTree


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

    albumSelected = Signal(AlbumItem)
    imagesDropped = Signal(list, str)

    def __init__(self, service: LibraryService, parent=None) -> None:
        super().__init__(parent)
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
        self.tree.currentItemChanged.connect(self._on_current_changed)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        root.addWidget(self.tree, 1)

        self._populate_roots()

    # --------- DB → UI population ---------
    def reload(self):
        """ Global helper to reload the widget. """
        self._populate_roots()

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
        for row in self.service.get_children(folder_id):
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

        # If it's an image, set current item to the parent album
        if isinstance(item, ImageItem):
            item = item.parent() or self.tree.visible_root()

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
            new_id = self.service.create_album(parent_id=parent_id, name=name)
            it = AlbumItem(new_id, name, index)
        else:
            new_id = self.service.create_folder(parent_id=parent_id, name=name)
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

        # Validation passed, create the menu
        menu = QMenu(self)
        if not item == self.tree.visible_root():
            act_rename = menu.addAction("Rename")
            act_delete = menu.addAction("Delete")
        else:
            act_rename, act_delete = None, None
        if not isinstance(item, ImageItem):
            act_create_f = menu.addAction("Create Folder")
            act_create_a = menu.addAction("Create Album")
        else:
            act_create_f, act_create_a = None, None

        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if not chosen:
            return

        # Execute the action
        if chosen == act_rename:
            self._on_rename(item)
        elif chosen == act_delete:
            self._on_delete(item)
        elif chosen == act_create_f:
            self._create_node(make_album=False)
        elif chosen == act_create_a:
            self._create_node(make_album=True)

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
            self.service.rename_image(item.id, new_name)
            self.albumSelected.emit(self._current_album_item())
        else:
            raise ValueError(f"Unknown type {type(item)}")
        # Update UI text
        item.setText(COL_LABEL, new_name)

    def _on_delete(self, item: QTreeWidgetItem):
        """Delete in DB then remove from the tree."""
        if isinstance(item, FolderItem):
            self.service.delete_folder(item.id, hard=True)

        elif isinstance(item, AlbumItem):
            self.service.delete_album(item.id, hard=True)

        elif isinstance(item, ImageItem):
            self.service.delete_image_from_album(item.parent().id, item.id)
            self.albumSelected.emit(self._current_album_item())
        else:
            raise ValueError(f"Unknown type {type(item)}.")
        # Finally, remove from UI
        parent = item.parent() or self.tree.invisibleRootItem()
        parent.removeChild(item)

    def _on_current_changed(self, cur: Optional[QTreeWidgetItem], prev: Optional[QTreeWidgetItem]) -> None:
        """ Emits a signal for the selected album. """
        if not cur:
            return
        # Trigger signal for album or image.
        if isinstance(cur, AlbumItem):
            self.albumSelected.emit(cur)
        if isinstance(cur, ImageItem):
            cur = cur.parent()
            self.albumSelected.emit(cur)

    # --- Album helpers to utilise in the image tab (operate on the *currently selected* album) ---
    def _current_album_item(self) -> AlbumItem | None:
        """ Return the selected QTreeWidgetItem if it is an Album, else None. """
        item = self.tree.currentItem()
        if not item:
            return None
        if isinstance(item, AlbumItem):
            return item
        if isinstance(item, ImageItem):
            return item.parent()
        return None

    def get_current_album_images(self) -> list[ImageItem]:
        """ Return the ImageItem list for the selected album (model objects). """
        item = self._current_album_item()
        if not item:
            return []
        return list([item.child(i) for i in range(item.childCount())])

    def add_images_to_current_album(self, paths: list[str]) -> None:
        album_item = self._current_album_item()
        if not album_item or not paths:
            return

        added = self.service.add_images_from_paths(album_item.id, paths)

        # Reflect in the tree
        for img in added:
            album_item.addChild(ImageItem(*img))

        album_item.setExpanded(True)
