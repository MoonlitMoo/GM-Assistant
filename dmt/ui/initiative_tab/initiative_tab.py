from __future__ import annotations
from typing import Tuple, List

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QPushButton, QTableView, QMessageBox, QHeaderView, QSizePolicy
)

from dmt.core import DisplayState

from .controller import InitiativeController
from .table_model import InitiativeTableModel

class InitiativeTab(QWidget):
    def __init__(self, parent, ctl: InitiativeController, state: DisplayState):
        super().__init__(parent)
        self.state = state
        self.ctl = ctl
        self.model = InitiativeTableModel(self.ctl)

        # ---------- Header bar ----------
        self.lbl_round = QLabel("Round: –")
        self.lbl_round.setStyleSheet("font-weight: 600;")

        self.btn_show = QPushButton("Show on Player")
        self.btn_show.setCheckable(True)
        self.btn_show.setChecked(self.state.initiative_visible())

        self.btn_reset = QPushButton("Reset")
        self.btn_clear = QPushButton("Clear Table")

        header = QHBoxLayout()
        header.addWidget(self.lbl_round)
        header.addStretch(1)
        header.addWidget(self.btn_show)
        header.addWidget(self.btn_reset)
        header.addWidget(self.btn_clear)

        # ---------- Add row ----------
        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText("Name")
        self.name_edit.setFixedWidth(160)
        self.init_spin = QSpinBox(); self.init_spin.setRange(-999, 999); self.init_spin.setValue(10)
        self.init_spin.setFixedWidth(64)
        self.btn_add = QPushButton("Add"); self.btn_add.setFixedWidth(64)

        addrow = QHBoxLayout()
        addrow.addWidget(self.name_edit)
        addrow.addWidget(self.init_spin)
        addrow.addWidget(self.btn_add)
        addrow.addStretch(1)

        # ---------- Table ----------
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setDragEnabled(True)
        self.table.setAcceptDrops(True)
        self.table.setDragDropMode(QTableView.InternalMove)
        self.table.setDropIndicatorShown(True)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setVisible(False)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 👁
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)           # Name
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Initiative
        self.table.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        # ---------- Footer bar ----------
        self.btn_back = QPushButton("◀ Back")
        self.btn_next = QPushButton("Next ▶")
        self.btn_end  = QPushButton("End")
        self.btn_back.setEnabled(False)
        self.btn_next.setEnabled(False)
        self.btn_end.setEnabled(False)

        footer = QHBoxLayout()
        footer.addWidget(self.btn_back)
        footer.addWidget(self.btn_next)
        footer.addStretch(1)
        footer.addWidget(self.btn_end)

        # ---------- Root layout ----------
        root = QVBoxLayout(self)
        root.addLayout(header)
        root.addLayout(addrow)
        root.addWidget(self.table, 1)
        root.addLayout(footer)
        self.setLayout(root)

        # ---------- Signals ----------
        self.btn_add.clicked.connect(self._on_add)
        self.btn_show.toggled.connect(self._on_toggle_show)
        self.btn_reset.clicked.connect(self._on_reset)
        self.btn_clear.clicked.connect(self._on_clear)
        self.btn_back.clicked.connect(self._on_back)
        self.btn_next.clicked.connect(self._on_next)
        self.btn_end.clicked.connect(self._on_end)

        # Shortcuts
        QShortcut(QKeySequence(Qt.Key_Return), self, self._trigger_add_shortcut)
        QShortcut(QKeySequence(Qt.Key_Enter),  self, self._trigger_add_shortcut)
        QShortcut(QKeySequence(Qt.Key_Delete), self.table, self._delete_selected)
        sc_next = QShortcut(QKeySequence(Qt.Key_Right), self, self._on_next)
        sc_back = QShortcut(QKeySequence(Qt.Key_Left),  self, self._on_back)
        sc_next.setContext(Qt.WidgetWithChildrenShortcut)
        sc_back.setContext(Qt.WidgetWithChildrenShortcut)

        # Initial sizing
        QTimer.singleShot(0, self._resize_table_width)
        self._refresh_buttons()
        self._update_round_label()

    # ---------- Helpers ----------
    def _revealed_subset(self) -> Tuple[List[str], int]:
        L = self.ctl.list()
        cur = self.ctl.cursor_index()
        if not L or cur is None:
            return ([], -1)
        revealed = [c.name for c in L if c.is_revealed]
        current_name = L[cur].name
        return revealed, revealed.index(current_name) if current_name in revealed else -1

    def _push_overlay_snapshot(self):
        if not self.state:
            return
        names, idx = self._revealed_subset()
        if self.btn_show.isChecked() and names:
            self.state.set_initiative(names, idx, self.ctl.round())
        else:
            self.state.hide_initiative()

    def _refresh_buttons(self):
        has_any = bool(self.ctl.list())
        running = self.ctl.is_running()
        self.btn_back.setEnabled(running and has_any)
        self.btn_next.setEnabled(running and has_any)
        self.btn_end.setEnabled(has_any)  # End hides overlay; keep enabled when list exists

    def _update_round_label(self):
        r = self.ctl.round()
        self.lbl_round.setText(f"Round: {r if r > 0 else '–'}")

    # width-only resize that clamps minimums
    def _resize_table_width(self, extra_padding: int = 12, min_width: int = 220, max_width: int = 520):
        self.table.resizeColumnsToContents()
        cols = self.model.columnCount()
        # clip column mins (👁, Name, Init)
        mins = (40, 100, 60)
        hdr = self.table.horizontalHeader()
        for c in range(cols):
            size = hdr.sectionSize(c)
            if size < mins[c]:
                hdr.resizeSection(c, mins[c])
        col_sum = sum(hdr.sectionSize(c) for c in range(cols))
        frame = self.table.frameWidth() * 2
        vscroll_w = self.table.verticalScrollBar().width() if self.table.verticalScrollBar().isVisible() else 0
        w = col_sum + frame + vscroll_w + extra_padding
        w = max(min_width, min(max_width, w))
        self.table.setFixedWidth(w)

    # ---------- Slots ----------
    def _on_add(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Please enter a name.")
            return
        self.model.insertCombatant(name, int(self.init_spin.value()))
        self.name_edit.clear()
        self._resize_table_width()
        self._refresh_buttons()

    def _on_toggle_show(self, checked: bool):
        if checked and not self.ctl.is_running() and self.ctl.list():
            # auto-start if DM wants to show before pressing next/back
            self.ctl.start()
        self._refresh_buttons()
        self._push_overlay_snapshot()
        # focus table for arrows
        if self.ctl.is_running():
            self.table.setFocus()

    def _on_reset(self):
        self.ctl.reset_round_and_visibility()
        self.model.layoutChanged.emit()
        self._update_round_label()
        # If visible, overlay will clear until next advancement
        self._push_overlay_snapshot()

    def _on_clear(self):
        self.ctl.clear()
        self.model.layoutChanged.emit()
        self._update_round_label()
        self._refresh_buttons()
        if self.state:
            self.state.hide_initiative()
        self.btn_show.setChecked(False)

    def _on_back(self):
        if not self.ctl.is_running():
            self.ctl.start()
        self.ctl.back()
        self.model.layoutChanged.emit()
        self._update_round_label()
        self._push_overlay_snapshot()

    def _on_next(self):
        if not self.ctl.is_running():
            self.ctl.start()
        self.ctl.next()
        self.model.layoutChanged.emit()
        self._update_round_label()
        self._push_overlay_snapshot()

    def _on_end(self):
        self.btn_show.setChecked(False)
        self.ctl.end()
        self.model.layoutChanged.emit()
        self._update_round_label()
        self._refresh_buttons()
        if self.state:
            self.state.hide_initiative()

    def _trigger_add_shortcut(self):
        fw = self.focusWidget()
        if fw in (self.name_edit, self.init_spin, self.btn_add):
            self._on_add()

    def _delete_selected(self):
        sel = self.table.selectionModel()
        if not sel:
            return
        rows = sorted({i.row() for i in sel.selectedRows()}, reverse=True)
        for r in rows:
            self.model.removeRows(r, 1)
        self._resize_table_width()
        self._refresh_buttons()

    # keep table sized if fonts/rows change
    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self._resize_table_width)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        QTimer.singleShot(0, self._resize_table_width)
