from __future__ import annotations

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QTreeWidget, QAbstractItemView, QTreeWidgetItem

from dmt.db.services.library_service import LibraryService
from dmt.ui.image_tab.library_items import COL_LABEL, ROLE_KIND, FolderItem, AlbumItem, ImageItem


class LibraryTree(QTreeWidget):
    """ DB-backed library tree (folders/collections/images). """

    def __init__(self, parent=None, service: LibraryService = None):
        super().__init__(parent)
        self.service = service
        self.setColumnCount(1)
        self.setHeaderHidden(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

    # --- helpers --------------------------------------------------------------
    @staticmethod
    def kind(item: QTreeWidgetItem | None) -> str:
        if not item:
            return ""
        return item.data(COL_LABEL, ROLE_KIND) or ""

    def visible_root(self) -> QTreeWidgetItem:
        """Return the (single) visible root node; create if missing."""
        if self.topLevelItemCount() == 0:
            root = FolderItem(None, "root", 0)
            self.addTopLevelItem(root)

        return self.topLevelItem(0)

    @staticmethod
    def _is_descendant(parent: QTreeWidgetItem, potential_child: QTreeWidgetItem) -> bool:
        """ Check if the second item is a descendant of the first.
        Best way is to go up from the child to see if we hit the parent.

        Parameters
        ----------
        parent : QTreeWidgetItem
            The potential ancestor.
        potential_child : QTreeWidgetItem
            The item we want to check if is a descendant.

        Returns
        -------
        bool
        """
        cur = potential_child.parent()
        while cur:
            if cur is parent:
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

        src_kind = self.kind(src)
        # Drop target must be a container. If you point at an Image, treat its parent as target.
        dst_eff = dst
        if self.kind(dst) == "Image":
            dst_eff = dst.parent() or self.visible_root()
        dst_kind = self.kind(dst_eff)

        # Never allow moving the visible root; and never drop onto Image directly
        if src is self.visible_root() or dst_eff is None:
            return False

        # No cyclic moves
        if self._is_descendant(src, dst_eff):
            return False

        # Enforce container rules
        if not self._allowed_parent(src_kind, dst_kind):
            return False

        # If moving between folders, don't allow if contains an item with the same name
        if dst != src.parent() and src.label in [dst.child(i).label for i in range(dst.childCount())]:
            return False

        return True

    # --- Qt event overrides ---------------------------------------------------
    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """ Validate drag with awareness of the drop indicator (on/above/below).
        Calls super move to update the dropIndicatorPosition, then we check if the move action is valid failing if not.
        """
        QTreeWidget.dragMoveEvent(self, event)
        pos = event.position().toPoint()
        anchor = self.itemAt(pos) or self.visible_root()
        indicator = self.dropIndicatorPosition()

        # Resolve effective parent container for validation
        def effective_parent(anchor_item):
            kind = self.kind(anchor_item)
            if indicator == QAbstractItemView.OnItem:
                # Drop INTO the anchor: images aren't containers → use their parent
                return anchor_item if kind in ("Folder", "Album") else (anchor_item.parent() or self.visible_root())
            elif indicator in (QAbstractItemView.AboveItem, QAbstractItemView.BelowItem):
                # Drop BETWEEN siblings → parent is the anchor's parent (or visible root)
                return anchor_item.parent() or self.visible_root()
            else:  # OnViewport / unknown → default to visible root
                return self.visible_root()

        target_parent = effective_parent(anchor)
        srcs = self.selectedItems()

        ok = bool(target_parent and srcs and all(self._is_valid_drop(s, target_parent) for s in srcs))
        if ok:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """ Perform move/reorder with exact insertion index based on drop indicator.
        Pull relevant information from the event then pass through to the handler.
        """
        pos: QPoint = event.position().toPoint()
        anchor = self.itemAt(pos) or self.visible_root()
        indicator = self.dropIndicatorPosition()
        srcs = self.selectedItems()

        success = self._handle_item_movement(srcs, anchor, indicator)

        if not success:
            event.ignore()
            return

        # Notify & accept as a move
        event.setDropAction(Qt.IgnoreAction)
        event.accept()

    def _handle_item_movement(self, srcs, anchor, indicator):
        """ Performs the actual movement logic.
        First we resolve the target and row depending on the indicator and the type of item we are moving and dropped on.
        Then we validate the movement, and if ok, update the UI and the database.

        Parameters
        ----------
        srcs : list of QTreeWidgetItem
            The items to move
        anchor : QTreeWidgetItem
            The destination item
        indicator : QAbstractItemView
            The indicator when the drop was performed

        Returns
        -------
        bool
            If we performed the movement
        """

        # Helper to resolve (parent, insert_row) given anchor & indicator
        def resolve_target_and_row(anchor_item):
            # Normalise when dropping ON: images aren't containers → use their parent
            if indicator == QAbstractItemView.OnItem:
                parent = anchor_item if self.kind(anchor_item) in ("Folder", "Album") else (
                        anchor_item.parent() or self.visible_root())
                row = parent.childCount()  # append
                return parent, row

            # Between siblings → parent is the anchor's parent; compute index above/below
            if indicator in (QAbstractItemView.AboveItem, QAbstractItemView.BelowItem):
                parent = anchor_item.parent() or self.visible_root()
                idx = parent.indexOfChild(anchor_item)
                if idx < 0:
                    idx = parent.childCount()
                row = idx + (1 if indicator == QAbstractItemView.BelowItem else 0)
                return parent, row

            # On viewport or unknown → append to visible root
            parent = self.visible_root()
            return parent, parent.childCount()

        target_parent, insert_row = resolve_target_and_row(anchor)

        # Validate against the effective parent container
        if not (target_parent and srcs and all(self._is_valid_drop(s, target_parent) for s in srcs)):
            return False

        # Sort sources by their visual order to keep a stable sequence while inserting
        def item_row(it):
            p = it.parent() or self.invisibleRootItem()
            return p.indexOfChild(it)

        srcs_sorted = sorted(srcs, key=item_row)

        # For moves within the same parent, inserting below a position after removing earlier rows
        # requires compensating the target index when the source was above the insertion point.
        last_moved = None
        for src in srcs_sorted:
            old_parent = src.parent() or self.invisibleRootItem()
            old_row = old_parent.indexOfChild(src)

            # Compute compensation for same-parent moves
            target_row = insert_row
            if old_parent is target_parent and old_row < insert_row:
                target_row -= 1  # removing an earlier row shifts the target left by one

            # Detach & insert at the computed position
            old_parent.removeChild(src)
            clipped_target = max(0, min(target_row, target_parent.childCount()))
            target_parent.insertChild(clipped_target, src)

            # Update the DB
            if isinstance(src, FolderItem):
                self.service.move_node(src.id, "folder", target_parent.id, clipped_target)
            elif isinstance(src, AlbumItem):
                self.service.move_node(src.id, "album", target_parent.id, clipped_target)
            elif isinstance(src, ImageItem):
                self.service.move_image(src.id, target_parent.id, clipped_target)
            else:
                raise ValueError(f"Unknown item {type(src)}")

            # If we are inserting "below", and have multiple items, advance insertion point
            if target_parent is not None and indicator == QAbstractItemView.BelowItem:
                insert_row = target_row + 1
            last_moved = src

        # Selection/focus and UX niceties
        if last_moved is not None:
            self.setCurrentItem(last_moved)
        if target_parent is not None:
            target_parent.setExpanded(True)

        return True
