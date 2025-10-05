from PySide6.QtCore import (QAbstractTableModel, QModelIndex, Qt, QMimeData, QByteArray, QDataStream, QIODevice)
from PySide6.QtGui import QColor
from typing import Any
from .controller import InitiativeController

HEADERS = ["Name", "Initiative"]


class InitiativeTableModel(QAbstractTableModel):
    def __init__(self, ctl: InitiativeController):
        super().__init__()
        self.ctl = ctl

    # ----- basic shape -----
    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.ctl.list())

    def columnCount(self, parent=QModelIndex()) -> int:
        return 2

    # ----- data -----
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = self.ctl.list()[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return row.name
            if col == 1:
                return row.initiative

        if role == Qt.TextAlignmentRole and col == 1:
            return Qt.AlignRight | Qt.AlignVCenter

        if role == Qt.BackgroundRole and self.ctl.cursor_index() == index.row() and self.ctl.is_running():
            return QColor("#233")  # subtle current-row highlight

        if role == Qt.ForegroundRole and self.ctl.cursor_index() == index.row() and self.ctl.is_running():
            return QColor("#E6F3FF")

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return HEADERS[section]
        return None

    # ----- editing -----
    def flags(self, index: QModelIndex):
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.isValid():
            base |= Qt.ItemIsEditable | Qt.ItemIsDragEnabled
        else:
            base |= Qt.ItemIsDropEnabled
        # table supports dropping between rows
        return base

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole):
        if role != Qt.EditRole or not index.isValid():
            return False
        row = index.row()
        col = index.column()
        if col == 0:
            self.ctl.update_by_index(row, name=str(value))
            self.dataChanged.emit(index, index, [Qt.DisplayRole])
            return True
        if col == 1:
            try:
                ini = int(value)
            except ValueError:
                return False
            # reinsert to maintain sorted-on-update invariant
            self.beginResetModel()
            self.ctl.update_by_index(row, initiative=ini)
            self.endResetModel()
            return True
        return False

    # ----- insert/remove through model API -----
    def insertCombatant(self, name: str, initiative: int):
        # We don't know the position beforehand because of sort-on-insert,
        # do a reset for simplicity (small list, acceptable).
        self.beginResetModel()
        self.ctl.add(name, initiative)
        self.endResetModel()

    def removeRows(self, row: int, count: int, parent=QModelIndex()):
        self.beginResetModel()
        for _ in range(count):
            self.ctl.remove_by_index(row)
        self.endResetModel()
        return True

    # ----- drag & drop reorder (manual override) -----
    def supportedDropActions(self):
        return Qt.MoveAction

    def mimeTypes(self):
        return ["application/x-initiative-row", "application/x-qabstractitemmodeldatalist"]

    def mimeData(self, indexes):
        mime = QMimeData()
        if not indexes:
            return mime
        # We only support single-row moves; take the first selected index's row.
        row = indexes[0].row()
        ba = QByteArray()
        stream = QDataStream(ba, QIODevice.WriteOnly)
        stream.writeInt32(row)
        mime.setData("application/x-initiative-row", ba)
        return mime

    def dropMimeData(self, data: QMimeData, action, row, column, parent):
        if action != Qt.MoveAction:
            return False
        src_row = self._extract_drag_row(data)
        if src_row is None:
            return False

        # Determine destination row:
        dst_row = row if row != -1 else (parent.row() if parent.isValid() else self.rowCount())
        if dst_row > src_row:
            dst_row -= 1  # Qt's move semantics

        self.beginResetModel()
        self.ctl.move_row(src_row, dst_row)
        self.endResetModel()
        return True

    def _extract_drag_row(self, data: QMimeData):
        fmt = "application/x-initiative-row"
        if data.hasFormat(fmt):
            ba = data.data(fmt)
            stream = QDataStream(ba)
            try:
                row = stream.readInt32()
                return int(row)
            except Exception:
                return None

        # Fallbacks (not usually hit, but harmless)
        if data.hasText():
            try:
                return int(data.text())
            except ValueError:
                pass
        return None
