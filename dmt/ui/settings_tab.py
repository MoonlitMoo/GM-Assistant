from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QCheckBox,
    QLabel,
    QSpinBox,
    QGroupBox,
    QFormLayout, QLineEdit, QPushButton, QHBoxLayout, QFileDialog, QMessageBox,
)

from db.manager import DatabaseManager
from .player_window import DisplayState
from ..core.config import Config


class DatabaseSelectorWidget(QWidget):
    """Settings section for selecting/creating a database file.

    Signals
    -------
    databaseSelected(str): emitted after user picks an existing DB file.
    databaseCreated(str):  emitted after user defines a new DB file to create.
    """
    databaseSelected = Signal(str)
    databaseCreated = Signal(str)

    def __init__(self, parent: QWidget | None = None, *, show_create_button: bool = True):
        super().__init__(parent)

        self._current_path_edit = QLineEdit(self)
        self._current_path_edit.setReadOnly(True)
        self._current_path_edit.setPlaceholderText("No database selected")

        self._btn_change = QPushButton("Change…", self)
        self._btn_change.clicked.connect(self._on_change_clicked)

        self._btn_new = QPushButton("New…", self)
        self._btn_new.clicked.connect(self._on_new_clicked)
        self._btn_new.setVisible(show_create_button)

        # Layout
        row = QHBoxLayout()
        row.addWidget(QLabel("Current Database:", self))
        row.addWidget(self._current_path_edit, stretch=1)
        row.addWidget(self._btn_change)
        if show_create_button:
            row.addWidget(self._btn_new)

        root = QVBoxLayout(self)
        root.addLayout(row)
        root.addStretch(1)
        self.setLayout(root)

    # --- Public API --------------------------------------------------------

    def set_current_path(self, path: str | Path | None) -> None:
        """Update the displayed path (does not emit signals)."""
        if not path:
            self._current_path_edit.clear()
            return
        self._current_path_edit.setText(str(Path(path)))

    def current_path(self) -> str:
        return self._current_path_edit.text().strip()

    # --- Slots -------------------------------------------------------------

    def _on_change_clicked(self) -> None:
        start_dir = str(Path(self.current_path()).parent) if self.current_path() else ""
        fname, _ = QFileDialog.getOpenFileName(
            self,
            "Open Database",
            start_dir,
            "SQLite Databases (*.db *.sqlite *.sqlite3);;All Files (*)"
        )
        if not fname:
            return
        p = Path(fname)
        if not p.exists() or not p.is_file():
            QMessageBox.warning(self, "Invalid File", "Please select an existing database file.")
            return

        # Update UI and notify app (you can hook DBM here)
        self.set_current_path(p)
        self.databaseSelected.emit(str(p))

    def _on_new_clicked(self) -> None:
        start_dir = str(Path(self.current_path()).parent) if self.current_path() else ""
        fname, _ = QFileDialog.getSaveFileName(
            self,
            "Create New Database",
            start_dir,
            "SQLite Databases (*.db *.sqlite *.sqlite3);;All Files (*)"
        )
        if not fname:
            return

        p = Path(fname)
        if p.exists():
            resp = QMessageBox.question(
                self,
                "Overwrite?",
                f"“{p.name}” already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if resp != QMessageBox.Yes:
                return

        # Don’t create the file here; let your DBM handle init/migrations.
        # We just update the path and signal intent.
        self.set_current_path(p)
        self.databaseCreated.emit(str(p))


class SettingsTab(QWidget):
    """ Settings screen for all global options. """
    reloadedDatabase = Signal()

    def __init__(self, dbm: DatabaseManager, display_state: DisplayState) -> None:
        super().__init__()
        self._dbm = dbm
        self._display_state = display_state

        root = QVBoxLayout(self)

        # Open DB settings
        grp_db = QGroupBox("Database")
        form = QFormLayout(grp_db)
        self.db_section = DatabaseSelectorWidget(self, show_create_button=True)
        self.db_section.set_current_path(self._dbm.path)
        self.db_section.databaseSelected.connect(self._on_db_selected)
        self.db_section.databaseCreated.connect(self._on_db_created)
        form.addWidget(self.db_section)
        root.addWidget(grp_db)

        # Player Window settings
        grp_player = QGroupBox("Player Window")
        form = QFormLayout(grp_player)

        # Add the check button
        self.chk_windowed = QCheckBox("Player Screen uses windowed mode (default is fullscreen)")
        self.chk_windowed.setChecked(self._display_state.windowed())
        self.chk_windowed.stateChanged.connect(self._display_state.set_windowed)
        form.addRow(self.chk_windowed)

        root.addWidget(grp_player)
        root.addStretch(1)

    def _on_db_selected(self, path: str) -> None:
        if path == self._dbm.path:
            return
        self._dbm.dispose()
        self._dbm.open(Path(path), create_if_missing=False)
        self.reloadedDatabase.emit()

    def _on_db_created(self, path: str) -> None:
        self._dbm.dispose()
        self._dbm.open(Path(path), create_if_missing=True)
        self.reloadedDatabase.emit()
