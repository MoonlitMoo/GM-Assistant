from __future__ import annotations
from typing import Any
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QMimeData
from PySide6.QtGui import QColor
from .controller import InitiativeController, Combatant

HEADERS = ["👁", "Name", "Initiative"]

class InitiativeTableModel(QAbstractTableModel):
    """3 columns: visible checkbox, name, initiative. Drag to manually reorder."""
    MIME = "application/x-initiative-row"

    def __init__(self, ctl: InitiativeController):
        super().__init__()
        self.ctl = ctl

    # --- shape ---
    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.ctl.list())

    def columnCount(self, parent=QModelIndex()) -> int:
        return 3

    # --- data ---
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = self.ctl.list()[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 1:  # Name
                return row.name
            if col == 2:  # Initiative
                return row.initiative

        if role == Qt.CheckStateRole and col == 0:
            return Qt.Checked if row.is_revealed else Qt.Unchecked

        if role == Qt.TextAlignmentRole and col == 2:
            return Qt.AlignRight | Qt.AlignVCenter

        # highlight current turn while running
        if role == Qt.BackgroundRole and self.ctl.is_running() and self.ctl.cursor_index() == index.row():
            return QColor("#233")
        if role == Qt.ForegroundRole and self.ctl.is_running() and self.ctl.cursor_index() == index.row():
            return QColor("#E6F3FF")

        return None

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return HEADERS[section]
        return None

    # --- flags / editing ---
    def flags(self, index: QModelIndex):
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.isValid():
            base |= Qt.ItemIsDragEnabled
            if index.column() == 0:
                base |= Qt.ItemIsUserCheckable
            else:
                base |= Qt.ItemIsEditable
        else:
            base |= Qt.ItemIsDropEnabled
        return base

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole):
        if not index.isValid():
            return False
        r, c = index.row(), index.column()

        if c == 0 and role == Qt.CheckStateRole:
            self.ctl.set_revealed(r, value == Qt.Checked)
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True

        if role == Qt.EditRole:
            if c == 1:
                self.ctl.update_by_index(r, name=str(value))
                self.dataChanged.emit(index, index, [Qt.DisplayRole])
                return True
            if c == 2:
                try:
                    ini = int(value)
                except ValueError:
                    return False
                self.beginResetModel()
                self.ctl.update_by_index(r, initiative=ini)
                self.endResetModel()
                return True
        return False

    # --- insert/remove API for the tab ---
    def insertCombatant(self, name: str, initiative: int):
        self.beginResetModel()
        self.ctl.add(name, initiative)
        self.endResetModel()

    def removeRows(self, row: int, count: int, parent=QModelIndex()):
        self.beginResetModel()
        for _ in range(count):
            self.ctl.remove_by_index(row)
        self.endResetModel()
        return True

    # --- drag/drop reorder (custom mime, simple + robust) ---
    def supportedDropActions(self):
        return Qt.MoveAction

    def mimeTypes(self):
        return [self.MIME, "application/x-qabstractitemmodeldatalist"]

    def mimeData(self, indexes):
        mime = QMimeData()
        if indexes:
            mime.setData(self.MIME, str(indexes[0].row()).encode("utf-8"))
        return mime

    def dropMimeData(self, data: QMimeData, action, row, column, parent):
        if action != Qt.MoveAction or not data.hasFormat(self.MIME):
            return False
        try:
            src_row = int(bytes(data.data(self.MIME)).decode("utf-8"))
        except Exception:
            return False
        dst_row = row if row != -1 else (parent.row() if parent.isValid() else self.rowCount())
        if dst_row > src_row:
            dst_row -= 1
        self.beginResetModel()
        self.ctl.move_row(src_row, dst_row)
        self.endResetModel()
        return True
