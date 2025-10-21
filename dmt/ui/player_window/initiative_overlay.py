from PySide6.QtGui import QPainter, QBrush, QPen, QColor, QLinearGradient, QFont
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy
from PySide6.QtCore import Qt, QTimer, Signal


class InitiativeOverlay(QWidget):
    resized = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # --- Parchment theme palette ---
        self._col_bg_light = QColor(236, 228, 204, 235)   # parchment base
        self._col_bg_dark  = QColor(220, 208, 178, 235)   # vignette edge
        self._col_border   = QColor(112, 86, 58, 255)     # oak-brown border
        self._col_ink      = QColor(54, 38, 25, 255)      # dark umber text
        self._col_ink_muted= QColor(80, 60, 46, 255)      # secondary text
        self._col_gold_wash= QColor(212, 170, 59, 70)     # highlight fill
        self._col_gold_bar = QColor(160, 120, 40, 220)    # highlight bar

        self._radius = 12

        # subtle shadow to “lift” the card
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(22)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 90))
        self.setGraphicsEffect(shadow)

        # layout identical to your current version:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 14, 14, 14)
        self.main_layout.setSpacing(8)

        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(10)

        self.lbl_title = QLabel("Initiative")
        hfont = QFont(); hfont.setPointSize(14); hfont.setBold(True)
        self.lbl_title.setFont(hfont); self.lbl_title.setStyleSheet(f"color: {self._q(self._col_ink)};")

        self.lbl_round = QLabel("Round: –")
        self.lbl_round.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_round.setFont(hfont)
        self.lbl_round.setStyleSheet(f"color: {self._q(self._col_ink)};")

        self.header_layout.addWidget(self.lbl_title, 1)

        vdiv = QFrame()
        vdiv.setFrameShape(QFrame.VLine)
        vdiv.setFrameShadow(QFrame.Plain)
        vdiv.setStyleSheet(f"background-color: {self._q(self._col_ink_muted, a=90)}; width:1px;")
        self.header_layout.addWidget(vdiv)

        self.header_layout.addWidget(self.lbl_round, 0)
        self.main_layout.addLayout(self.header_layout)

        hdiv = QFrame()
        hdiv.setFrameShape(QFrame.HLine)
        hdiv.setFrameShadow(QFrame.Plain)
        hdiv.setStyleSheet(f"background-color: {self._q(self._col_ink_muted, a=90)}; height:1px;")
        self.main_layout.addWidget(hdiv)

        self.list_layout = QVBoxLayout(); self.list_layout.setSpacing(4)
        self.main_layout.addLayout(self.list_layout)

        self._labels: list[QLabel] = []
        self.current_index = -1

    # helper to turn QColor into rgba() css string
    def _q(self, c: QColor, a: int | None = None) -> str:
        if a is not None: c = QColor(c.red(), c.green(), c.blue(), a)
        return f"rgba({c.red()},{c.green()},{c.blue()},{c.alpha()})"

    # parchment card paint (background + border)
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        r = self.rect().adjusted(1, 1, -1, -1)

        # warm parchment gradient (slight vignette top-left -> bottom-right)
        grad = QLinearGradient(r.topLeft(), r.bottomRight())
        grad.setColorAt(0.0, self._col_bg_light)
        grad.setColorAt(1.0, self._col_bg_dark)
        p.setBrush(QBrush(grad))

        p.setPen(QPen(self._col_border, 2))
        p.drawRoundedRect(r, self._radius, self._radius)

        super().paintEvent(event)

    def set_entries(self, names: list[str], current_idx: int, round_num: int | None = None):
        # Pause repaints while we rebuild
        self.setUpdatesEnabled(False)

        if round_num is not None:
            self.lbl_round.setText(f"Round: {round_num}")
        else:
            self.lbl_round.setText("Round: –")

        # Clear + rebuild rows
        for lbl in self._labels:
            lbl.deleteLater()
        self._labels.clear()

        for i, name in enumerate(names):
            lbl = QLabel(f"{i + 1}: {name}")
            lbl.setContentsMargins(8, 3, 8, 3)
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            if i == current_idx:
                lbl.setStyleSheet(
                    "background-color: rgba(212,170,59,70);"
                    "border-left: 5px solid rgba(160,120,40,220);"
                    "color: rgba(54,38,25,255); font-weight:600;"
                )
            else:
                lbl.setStyleSheet("background-color: transparent; color: rgba(54,38,25,255);")
            self.list_layout.addWidget(lbl)
            self._labels.append(lbl)

        # Recompute layout geometry now (no paint yet)
        self.main_layout.activate()
        self.adjustSize()

        self.setUpdatesEnabled(True)

        # Defer one tick so fonts/metrics settle, then emit resized
        QTimer.singleShot(0, self._after_rebuild)

    def _after_rebuild(self):
        self.adjustSize()
        self.update()
        self.resized.emit()  # PlayerWindow will reposition us

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.resized.emit()
