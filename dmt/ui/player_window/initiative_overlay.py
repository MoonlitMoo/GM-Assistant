from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class InitiativeOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("""
            background-color: rgba(0, 0, 0, 180);
            border-radius: 8px;
            color: white;
            font-weight: 500;
            padding: 6px 10px;
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(4)
        self._labels: list[QLabel] = []

    def set_entries(self, names: list[str], current_idx: int):
        # Clear old labels
        for lbl in self._labels:
            lbl.deleteLater()
        self._labels.clear()

        # Build new labels
        for i, name in enumerate(names):
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            if i == current_idx:
                lbl.setStyleSheet("color: gold; font-weight: bold;")
            else:
                lbl.setStyleSheet("color: white;")
            self.layout.addWidget(lbl)
            self._labels.append(lbl)

        self.adjustSize()
