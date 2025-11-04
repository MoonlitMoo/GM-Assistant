from PySide6.QtGui import QPainter, QBrush, QPen, QColor, QLinearGradient, QFont
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QEvent


class InitiativeOverlay(QWidget):
    """
    Overlay widget that can scale as a whole, align to any window corner, and use an adjustable margin.

    set_overlay_params(margin: int, alignment: str, scale: int)
      - margin:   pixels from the chosen corner
      - alignment: one of {"top-left","top-right","bottom-left","bottom-right"}
      - scale:    percentage size (e.g. 100 = 1.0x). Use 0 for 'auto' (~20% of parent width, with min clamp).
    """
    resized = Signal()

    MIN_W = 220     # sensible minimum width when auto-scaling
    MIN_H = 120     # sensible minimum height when auto-scaling
    MIN_SCALE = 50  # 50% lower bound when auto computes too small (safety)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # --- parameters controlled via set_overlay_params ---
        self._overlay_margin = 16
        self._overlay_alignment = "top-right"
        self._overlay_scale_pct = 1  # No user scaling

        # --- Parchment theme palette ---
        self._col_bg_light = QColor(236, 228, 204, 235)   # parchment base
        self._col_bg_dark  = QColor(220, 208, 178, 235)   # vignette edge
        self._col_border   = QColor(112, 86, 58, 255)     # oak-brown border
        self._col_ink      = QColor(54, 38, 25, 255)      # dark umber text
        self._col_ink_muted= QColor(80, 60, 46, 255)      # secondary text
        self._col_gold_wash= QColor(212, 170, 59, 70)     # highlight fill
        self._col_gold_bar = QColor(160, 120, 40, 220)    # highlight bar

        # base metrics (scaled later)
        self._radius_base = 12
        self._border_w_base = 2
        self._margins_base = (14, 14, 14, 14)
        self._main_spacing_base = 8
        self._header_spacing_base = 10
        self._row_hpad_base = 8
        self._row_vpad_base = 3
        self._divider_thickness = 1
        self._header_pt_base = 14
        self._row_pt_base = 11

        # runtime-scaled metrics
        self._scale = 1.0
        self._radius = self._radius_base
        self._border_w = self._border_w_base

        # subtle shadow to “lift” the card
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(22)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 90))
        self.setGraphicsEffect(shadow)

        # layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(*self._margins_base)
        self.main_layout.setSpacing(self._main_spacing_base)

        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(self._header_spacing_base)

        self.lbl_title = QLabel("Initiative")
        self.lbl_round = QLabel("Round: –")
        self.lbl_round.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.header_layout.addWidget(self.lbl_title, 1)

        vdiv = QFrame()
        vdiv.setObjectName("vdiv")
        vdiv.setFrameShape(QFrame.VLine)
        vdiv.setFrameShadow(QFrame.Plain)
        self.header_layout.addWidget(vdiv)

        self.header_layout.addWidget(self.lbl_round, 0)
        self.main_layout.addLayout(self.header_layout)

        hdiv = QFrame()
        hdiv.setObjectName("hdiv")
        hdiv.setFrameShape(QFrame.HLine)
        hdiv.setFrameShadow(QFrame.Plain)
        self.main_layout.addWidget(hdiv)

        self.list_layout = QVBoxLayout()
        self.list_layout.setSpacing(4)
        self.main_layout.addLayout(self.list_layout)

        self._labels: list[QLabel] = []
        self.current_index = -1

        # react to parent resizes so we keep our corner placement
        if self.parent():
            self.parent().installEventFilter(self)

        # apply initial styling/scale
        self._apply_scale()
        self._refresh_divider_styles()

    # --- public API ----------------------------------------------------------
    def set_overlay_params(self, margin: int, alignment: str, scale: int):
        """
        margin: pixels from the aligned window corner.
        alignment: "top-left" | "top-right" | "bottom-left" | "bottom-right"
        scale: percent; 0 enables auto (~20% of window width, min-clipped).
        """
        self._overlay_margin = max(0, int(margin))
        align = alignment.lower().strip()
        if align not in {"top-left","top-right","bottom-left","bottom-right"}:
            align = "top-right"
        self._overlay_alignment = align
        self._overlay_scale_pct = scale/100  # Convert from percentage to float

        self._apply_scale()
        self.adjustSize()
        self._reposition()

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

        row_font = QFont()
        row_font.setPointSize(max(6, self._scaled(self._row_pt_base)))

        for i, name in enumerate(names):
            lbl = QLabel(f"{i + 1}: {name}")
            lbl.setFont(row_font)
            lbl.setContentsMargins(self._scaled(self._row_hpad_base),
                                   self._scaled(self._row_vpad_base),
                                   self._scaled(self._row_hpad_base),
                                   self._scaled(self._row_vpad_base))
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            if i == current_idx:
                lbl.setStyleSheet(
                    f"background-color: {self._q(self._col_gold_wash)};"
                    f"border-left: {self._scaled(5)}px solid {self._q(self._col_gold_bar)};"
                    f"color: {self._q(self._col_ink)}; font-weight:600;"
                )
            else:
                lbl.setStyleSheet(f"background-color: transparent; color: {self._q(self._col_ink)};")
            self.list_layout.addWidget(lbl)
            self._labels.append(lbl)

        # Recompute layout geometry now (no paint yet)
        self.main_layout.activate()
        self.adjustSize()

        self.setUpdatesEnabled(True)

        # Defer one tick so fonts/metrics settle, then reposition & emit resized
        QTimer.singleShot(0, self._after_rebuild)

    # --- internal helpers ---
    def _q(self, c: QColor, a: int | None = None) -> str:
        if a is not None: c = QColor(c.red(), c.green(), c.blue(), a)
        return f"rgba({c.red()},{c.green()},{c.blue()},{c.alpha()})"

    def _scaled(self, value: int | float) -> int:
        return max(1, int(round(value * self._scale)))

    def _refresh_divider_styles(self):
        # keep divider thickness looking crisp at scale
        css = f"background-color: {self._q(self._col_ink_muted, a=90)};"
        vdiv = self.findChild(QFrame, "vdiv")
        hdiv = self.findChild(QFrame, "hdiv")
        if vdiv:
            vdiv.setStyleSheet(css + f" width:{self._scaled(self._divider_thickness)}px;")
        if hdiv:
            hdiv.setStyleSheet(css + f" height:{self._scaled(self._divider_thickness)}px;")

    def _apply_scale(self):
        """ Determines scale from the target size (20% window), clipped to a minimum width, and modified by the user
        defined percentage.
        """
        parent_w = max(1, self.parent().width())
        target_w = max(int(parent_w * 0.20), self.MIN_W)
        base_scale = target_w / self.MIN_W
        self._scale = base_scale * self._overlay_scale_pct

        # scale geometry metrics
        self._radius = self._scaled(self._radius_base)
        self._border_w = max(1, self._scaled(self._border_w_base))

        L, T, R, B = self._margins_base
        self.main_layout.setContentsMargins(self._scaled(L), self._scaled(T), self._scaled(R), self._scaled(B))
        self.main_layout.setSpacing(self._scaled(self._main_spacing_base))
        self.header_layout.setSpacing(self._scaled(self._header_spacing_base))
        self.list_layout.setSpacing(self._scaled(4))

        # fonts
        hfont = QFont()
        hfont.setPointSize(max(6, self._scaled(self._header_pt_base)))
        hfont.setBold(True)
        self.lbl_title.setFont(hfont)
        self.lbl_title.setStyleSheet(f"color: {self._q(self._col_ink)};")

        self.lbl_round.setFont(hfont)
        self.lbl_round.setStyleSheet(f"color: {self._q(self._col_ink)};")

        # labels will be (re)created in set_entries; if they already exist, update their fonts/padding now
        row_font = QFont()
        row_font.setPointSize(max(6, self._scaled(self._row_pt_base)))
        for lbl in self._labels:
            lbl.setFont(row_font)
            lbl.setContentsMargins(self._scaled(self._row_hpad_base),
                                   self._scaled(self._row_vpad_base),
                                   self._scaled(self._row_hpad_base),
                                   self._scaled(self._row_vpad_base))
        self._refresh_divider_styles()

    def _reposition(self):
        """Position the overlay at the chosen corner with the given margin."""
        if not self.parent():
            return
        p = self.parent()
        p_w, p_h = p.width(), p.height()
        self.adjustSize()
        s = self.size()
        m = self._overlay_margin

        if self._overlay_alignment == "top-left":
            x, y = m, m
        elif self._overlay_alignment == "top-right":
            x, y = p_w - s.width() - m, m
        elif self._overlay_alignment == "bottom-left":
            x, y = m, p_h - s.height() - m
        else:  # "bottom-right"
            x, y = p_w - s.width() - m, p_h - s.height() - m

        # keep fully on screen if parent is small
        x = max(0, min(x, max(0, p_w - s.width())))
        y = max(0, min(y, max(0, p_h - s.height())))
        self.move(x, y)

    def _after_rebuild(self):
        self._apply_scale()  # keep scale effects after rebuild
        self.adjustSize()
        self._reposition()
        self.update()
        self.resized.emit()

    # --- QWidget overrides ---------------------------------------------------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        r = self.rect().adjusted(self._border_w // 2, self._border_w // 2,
                                 -self._border_w // 2, -self._border_w // 2)

        # warm parchment gradient
        grad = QLinearGradient(r.topLeft(), r.bottomRight())
        grad.setColorAt(0.0, self._col_bg_light)
        grad.setColorAt(1.0, self._col_bg_dark)
        p.setBrush(QBrush(grad))

        p.setPen(QPen(self._col_border, self._border_w))
        p.drawRoundedRect(r, self._radius, self._radius)

        super().paintEvent(event)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._reposition()
        self.resized.emit()

    def showEvent(self, e):
        super().showEvent(e)
        self._apply_scale()
        self._reposition()

    def eventFilter(self, obj: QObject, ev: QEvent) -> bool:
        # Track parent resizes to maintain corner placement and auto-scale
        if obj is self.parent() and ev.type() == QEvent.Resize:
            self._apply_scale()
            self._reposition()
        return super().eventFilter(obj, ev)
