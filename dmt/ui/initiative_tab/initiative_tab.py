from PySide6.QtGui import QShortcut, QKeySequence, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QSpinBox, QPushButton,
    QTableView, QMessageBox, QLabel, QHeaderView
)
from .controller import InitiativeController
from .table_model import InitiativeTableModel


class InitiativeTab(QWidget):
    def __init__(self, parent=None, ctl: InitiativeController = None):
        super().__init__(parent)
        self.ctl = ctl
        self.model = InitiativeTableModel(self.ctl)

        # ---- Top bar with Round label ----
        self.lbl_round = QLabel(self)
        self.lbl_round.setText("Round: –")
        self.lbl_round.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_round.setStyleSheet("font-weight: 600;")

        # --- UI ---
        self.table = QTableView(self)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setDragEnabled(True)
        self.table.setAcceptDrops(True)
        self.table.setDragDropMode(QTableView.InternalMove)
        self.table.setDropIndicatorShown(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(False)
        # Auto fit header size
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(80)
        # Add table row deletion
        self._sc_delete = QShortcut(QKeySequence(Qt.Key_Delete), self.table)
        self._sc_delete.activated.connect(self._delete_selected)

        self.name_edit = QLineEdit(self)
        self.name_edit.setPlaceholderText("Name")
        self.init_spin = QSpinBox(self)
        self.init_spin.setRange(-999, 999)
        self.init_spin.setValue(10)
        self.btn_add = QPushButton("Add", self)
        # Fix widths
        self.name_edit.setFixedWidth(140)
        self.init_spin.setFixedWidth(60)
        self.btn_add.setFixedWidth(60)
        # Shortcuts for adding combatant
        self.name_edit.returnPressed.connect(self._on_add)  # when typing in Name
        self._sc_add_return = QShortcut(QKeySequence(Qt.Key_Return), self)
        self._sc_add_enter = QShortcut(QKeySequence(Qt.Key_Enter), self)
        self._sc_add_return.activated.connect(self._trigger_add_shortcut)
        self._sc_add_enter.activated.connect(self._trigger_add_shortcut)
        self.btn_add.setAutoDefault(True)
        self.btn_add.setDefault(True)

        self.btn_start = QPushButton("Start Visual", self)
        self.btn_next = QPushButton("Next ▶", self)
        self.btn_back = QPushButton("◀ Back", self)
        self.btn_end = QPushButton("End", self)
        # Arrow key shortcuts for Next / Back
        self._sc_next = QShortcut(QKeySequence(Qt.Key_Right), self)
        self._sc_back = QShortcut(QKeySequence(Qt.Key_Left), self)
        self._sc_next.activated.connect(self._on_next)
        self._sc_back.activated.connect(self._on_back)
        self._sc_next.setContext(Qt.WidgetWithChildrenShortcut)
        self._sc_back.setContext(Qt.WidgetWithChildrenShortcut)

        self.btn_next.setEnabled(False)
        self.btn_back.setEnabled(False)
        self.btn_end.setEnabled(False)

        # layout
        topbar = QHBoxLayout()
        topbar.addWidget(self.lbl_round, 0)
        topbar.addStretch()

        form = QHBoxLayout()
        form.setSpacing(4)
        form.addWidget(self.name_edit, 2)
        form.addWidget(self.init_spin, 1)
        form.addWidget(self.btn_add, 0)
        form.addStretch()

        controls = QHBoxLayout()
        controls.addWidget(self.btn_start)
        controls.addWidget(self.btn_back)
        controls.addWidget(self.btn_next)
        controls.addWidget(self.btn_end)
        controls.addStretch()

        root = QVBoxLayout(self)
        root.addLayout(topbar)
        root.addLayout(form)
        root.addWidget(self.table, 0)
        root.addLayout(controls)
        self.setLayout(root)
        self._resize_table_width()

        # --- signals ---
        self.btn_add.clicked.connect(self._on_add)
        self.btn_start.clicked.connect(self._on_start)
        self.btn_next.clicked.connect(self._on_next)
        self.btn_back.clicked.connect(self._on_back)
        self.btn_end.clicked.connect(self._on_end)

        self.model.modelReset.connect(self._after_model_change)
        self.model.layoutChanged.connect(self._after_model_change)
        self.model.rowsInserted.connect(lambda *_: self._after_model_change())
        self.model.rowsRemoved.connect(lambda *_: self._after_model_change())

    # ------------- handlers -------------
    def _on_add(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Please enter a name.")
            return
        ini = int(self.init_spin.value())
        self.model.insertCombatant(name, ini)
        self.name_edit.clear()
        # keep Start enabled if we have at least one entry
        self._refresh_buttons()

    def _trigger_add_shortcut(self):
        """Fire Add when Return/Enter is pressed in the name field, initiative spinbox, or Add button."""
        fw = self.focusWidget()
        if fw in (self.name_edit, self.init_spin, self.btn_add):
            self._on_add()

    def _delete_selected(self):
        """Delete currently selected row(s) in the table."""
        sel = self.table.selectionModel()
        if not sel:
            return
        rows = sorted({idx.row() for idx in sel.selectedRows()}, reverse=True)
        if not rows:
            return
        for r in rows:
            self.model.removeRows(r, 1)
        # keep buttons state sensible
        self._refresh_buttons()
        self._after_model_change()

    def _on_start(self):
        if not self.ctl.list():
            return
        self.ctl.start()
        self.model.layoutChanged.emit()  # refresh highlight
        self.btn_start.setEnabled(False)
        self.btn_next.setEnabled(True)
        self.btn_back.setEnabled(True)
        self.btn_end.setEnabled(True)
        self.table.setFocus()
        self._after_model_change()

    def _on_next(self):
        self.ctl.next()
        self.model.layoutChanged.emit()
        self._after_model_change()

    def _on_back(self):
        self.ctl.back()
        self.model.layoutChanged.emit()
        self._after_model_change()

    def _on_end(self):
        self.ctl.end()
        self.model.layoutChanged.emit()
        self._refresh_buttons()
        self._after_model_change()

    def _refresh_buttons(self):
        has_any = bool(self.ctl.list())
        running = self.ctl.is_running()
        self.btn_start.setEnabled(has_any and not running)
        self.btn_next.setEnabled(running)
        self.btn_back.setEnabled(running)
        self.btn_end.setEnabled(running)

    def _resize_table_width(self, extra_padding: int = 12, min_width: int = 240,
                            max_width: int = 420, col_min_widths: tuple[int, int] = (160, 80)):
        """Resize table width to fit current column contents (no height changes)."""
        # Compute natural content sizes first
        header = self.table.horizontalHeader()
        self.table.resizeColumnsToContents()
        cols = self.model.columnCount()
        # Enforce per-column minimums
        for c in range(cols):
            current = header.sectionSize(c)
            min_col = col_min_widths[c] if c < len(col_min_widths) else 40
            if current < min_col:
                header.resizeSection(c, min_col)

        col_sum = sum(self.table.columnWidth(c) for c in range(cols))
        frame = self.table.frameWidth() * 2
        vheader_w = self.table.verticalHeader().width() if self.table.verticalHeader().isVisible() else 0
        vscroll_w = self.table.verticalScrollBar().width() if self.table.verticalScrollBar().isVisible() else 0

        w = col_sum + frame + vheader_w + vscroll_w + extra_padding
        w = max(min_width, min(max_width, w))
        self.table.setFixedWidth(w)

    def _update_round_label(self):
        r = self.ctl.round()
        self.lbl_round.setText(f"Round: {r if r > 0 else '–'}")

    def _after_model_change(self):
        self._resize_table_width()
        self._update_round_label()

    # --- overrides
    def showEvent(self, event):
        """Automatically focus correct widget when tab becomes visible."""
        super().showEvent(event)
        self._focus_appropriate_widget()

    def focusInEvent(self, event):
        """Also handle keyboard focus switching to this tab."""
        super().focusInEvent(event)
        self._focus_appropriate_widget()

    def _focus_appropriate_widget(self):
        """Focus the correct widget depending on state."""
        if self.ctl.is_running():
            self.table.setFocus()
        else:
            self.name_edit.setFocus()
