from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QCheckBox,
    QLabel,
    QSpinBox,
    QGroupBox,
    QFormLayout,
)

from ..core.config import Config


class SettingsTab(QWidget):
    """ Settings screen for all global options. """

    def __init__(self, cfg: Config, on_config_changed=None) -> None:
        super().__init__()
        self._cfg = cfg
        self._on_changed = on_config_changed or (lambda: None)

        root = QVBoxLayout(self)

        # Player Window settings
        grp_player = QGroupBox("Player Window")
        form = QFormLayout(grp_player)

        # Add the check button
        self.chk_windowed = QCheckBox("Player Screen uses windowed mode (default is fullscreen)")
        self.chk_windowed.setChecked(self._cfg.playerWindowed)
        self.chk_windowed.stateChanged.connect(self._update_player_windowed)
        form.addRow(self.chk_windowed)

        root.addWidget(grp_player)
        root.addStretch(1)

    def _update_player_windowed(self) -> None:
        self._cfg.playerWindowed = self.chk_windowed.isChecked()
        self._on_changed()
