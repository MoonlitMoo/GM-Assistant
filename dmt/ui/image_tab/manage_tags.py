from __future__ import annotations
from typing import List, Optional, Any

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor, QAction, QBrush
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableView,
    QMessageBox, QColorDialog, QMenu, QInputDialog
)


class _TagRow:
    """ Row in the TagTable """
    __slots__ = ("id", "name", "color_hex", "usage")
    def __init__(self, id: int, name: str, color_hex: Optional[str], usage: int):
        self.id = id
        self.name = name
        self.color_hex = color_hex
        self.usage = usage

class _TagTableModel(QAbstractTableModel):
    HEADERS = ["Name", "Color", "Usage"]

    def __init__(self, rows: List[_TagRow]):
        super().__init__()
        self._all: List[_TagRow] = list(rows)
        self._filtered: List[_TagRow] = list(rows)
        self._query: str = ""          # current filter text
        self._sort_col = 2             # default: Usage
        self._sort_order = Qt.DescendingOrder

    # --- Qt model basics ---
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._filtered)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 3

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = self._filtered[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0: return row.name
            if col == 1: return row.color_hex or ""
            if col == 2: return str(row.usage)

        if role == Qt.BackgroundRole and col == 1 and row.color_hex:
            qc = QColor(row.color_hex)
            if qc.isValid():
                return QBrush(qc)

        if role == Qt.ForegroundRole and col == 1 and row.color_hex:
            # ensure readable text over background
            c = row.color_hex.lstrip("#")
            if len(c) == 6:
                r, g, b = int(c[0:2],16), int(c[2:4],16), int(c[4:6],16)
                lum = 0.2126*r + 0.7152*g + 0.0722*b
                return QBrush(QColor("#000000" if lum > 160 else "#FFFFFF"))

        if role == Qt.TextAlignmentRole and col == 2:
            return Qt.AlignRight | Qt.AlignVCenter

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return str(section + 1)

    # --- public helpers ---
    def set_rows(self, rows: List[_TagRow]) -> None:
        self.beginResetModel()
        self._all = list(rows)
        # keep current sort & filter
        self._apply_sort_inplace()
        self._apply_filter_inplace()
        self.endResetModel()

    def apply_filter(self, query: str) -> None:
        self._query = query or ""
        self.layoutAboutToBeChanged.emit()
        self._apply_filter_inplace()
        self.layoutChanged.emit()

    # --- sorting ---
    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:
        """Sort backing data, then reapply current filter."""
        self._sort_col = column
        self._sort_order = order
        self.layoutAboutToBeChanged.emit()
        self._apply_sort_inplace()
        self._apply_filter_inplace()
        self.layoutChanged.emit()

    def _apply_sort_inplace(self) -> None:
        """Sort self._all according to current (column, order) with stable tie-breaks."""
        col, order = self._sort_col, self._sort_order
        reverse = (order == Qt.DescendingOrder)

        # define key per column, with stable secondary keys
        if col == 2:  # Usage
            # Primary: usage (desc/asc), Secondary: name asc (case-insensitive)
            def key(r: _TagRow):
                # for reverse, we invert via 'reverse=True' rather than negating
                return (r.usage, r.name.lower())
            self._all.sort(key=key, reverse=reverse)

        elif col == 0:  # Name
            # Primary: name (A/Z per order), Secondary: usage desc (so popular names group first)
            def key(r: _TagRow):
                return (r.name.lower(), -r.usage)
            # reverse only flips the primary (name); secondary keeps usage-desc feel
            self._all.sort(key=key, reverse=reverse)

        elif col == 1:  # Color
            # Primary: color hex (case-insensitive), Secondary: name asc
            def key(r: _TagRow):
                return ((r.color_hex or "").lower(), r.name.lower())
            self._all.sort(key=key, reverse=reverse)

        else:
            # Fallback: by name
            self._all.sort(key=lambda r: r.name.lower(), reverse=reverse)

    def _apply_filter_inplace(self) -> None:
        q = self._query.strip().lower()
        if not q:
            self._filtered = list(self._all)
        else:
            self._filtered = [r for r in self._all if q in r.name.lower()]


class ManageTagsDialog(QDialog):
    def __init__(self, tagging_service, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Tags")
        self.resize(560, 420)
        self._svc = tagging_service

        root = QVBoxLayout(self)

        # Top bar
        top = QHBoxLayout()
        self._search = QLineEdit(self)
        self._search.setPlaceholderText("Search tags…")
        self._search.textChanged.connect(self._on_search)
        btn_cleanup = QPushButton("Delete unused")
        btn_cleanup.clicked.connect(self._on_cleanup)
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self._load)
        top.addWidget(self._search, 1)
        top.addWidget(btn_cleanup, 0)
        top.addWidget(btn_refresh, 0)
        root.addLayout(top)

        # Table
        self._table = QTableView(self)
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setSelectionMode(QTableView.SingleSelection)
        self._table.setSortingEnabled(True)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._open_row_menu)
        root.addWidget(self._table, 1)

        self._model = _TagTableModel([])
        self._table.setModel(self._model)
        self._table.setColumnWidth(0, 280)
        self._table.setColumnWidth(1, 120)
        self._table.setColumnWidth(2, 80)

        self._load()

    # ---------- data loading ----------
    def _load(self) -> None:
        tags = self._svc.list_tags(limit=10_000)  # generous cap
        rows = self._build_rows_with_usage(tags)
        self._model.set_rows(rows)

    def _build_rows_with_usage(self, tags) -> List[_TagRow]:
        # Use a service helper to avoid opening sessions in UI.
        usage_map = self._svc.tag_usage_map_for_images()
        rows: List[_TagRow] = []
        for t in tags:
            rows.append(_TagRow(t.id, t.name, t.color_hex, usage_map.get(t.id, 0)))
        return rows

    # ---------- interactions ----------
    def _on_search(self, text: str) -> None:
        self._model.apply_filter(text)

    def _open_row_menu(self, pos) -> None:
        idx = self._table.indexAt(pos)
        if not idx.isValid():
            return
        row = self._model.at(idx.row())

        menu = QMenu(self)
        act_rename = QAction("Rename…", menu)
        act_color  = QAction("Set colour…", menu)
        act_delete = QAction("Delete", menu)

        act_rename.triggered.connect(lambda: self._rename_row(row))
        act_color.triggered.connect(lambda: self._recolor_row(row))
        act_delete.triggered.connect(lambda: self._delete_row(row))

        menu.addAction(act_rename)
        menu.addAction(act_color)
        menu.addSeparator()
        menu.addAction(act_delete)
        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _rename_row(self, row: _TagRow) -> None:
        new_name, ok = QInputDialog.getText(self, "Rename Tag", f"Rename “{row.name}” to:", text=row.name)
        if not ok or not new_name.strip() or new_name.strip() == row.name:
            return
        try:
            self._svc.update_tag(row.id, new_name=new_name.strip())
        except Exception as e:
            QMessageBox.warning(self, "Rename failed", str(e))
            return
        self._load()

    def _recolor_row(self, row: _TagRow) -> None:
        init = QColor(row.color_hex) if row.color_hex else QColor("#888888")
        col = QColorDialog.getColor(init, self, "Choose tag colour")
        if not col.isValid():
            return
        try:
            self._svc.update_tag(row.id, color_hex=col.name())
        except Exception as e:
            QMessageBox.warning(self, "Colour update failed", str(e))
            return
        self._load()

    def _delete_row(self, row: _TagRow) -> None:
        # Guard: if in use, confirm or block
        if row.usage > 0:
            resp = QMessageBox.question(
                self, "Tag in use",
                f"“{row.name}” is used {row.usage} time(s).\nDelete anyway and detach from images?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if resp != QMessageBox.Yes:
                return
            force = True
        else:
            force = False

        ok = self._svc.delete_tag(row.id, force=force)
        if not ok and not force:
            QMessageBox.information(self, "Cannot delete", "Tag is in use. Use the context menu to force delete.")
        self._load()

    def _on_cleanup(self) -> None:
        deleted = self._svc.cleanup_unused_tags()
        if deleted > 0:
            QMessageBox.information(self, "Cleanup complete", f"Removed {deleted} unused tag(s).")
        self._load()
