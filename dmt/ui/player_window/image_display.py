from __future__ import annotations
from enum import Enum

from PySide6.QtCore import Qt, QTimer, QByteArray, QPropertyAnimation
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect

from .display_state import ScaleMode


class ImageDisplayWidget(QWidget):
    """
    Reusable image canvas:
      - Accepts QImage, encoded bytes, or raw bytes (8-bit 1/3/4 channel).
      - DPI-aware scaling with ScaleMode (FIT/FILL/STRETCH/ACTUAL).
      - Debounced re-render during live resize for smoothness.
      - Blackout overlay with optional fade.
    """
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Base content
        self._image_label = QLabel(self)
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setStyleSheet("background:black;")
        self._image_label.setScaledContents(False)  # we supply a correctly sized pixmap

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._image_label)

        # State
        self._base_image: QImage | None = None
        self._scale_mode = ScaleMode.FIT
        self._transform_mode = Qt.SmoothTransformation
        self._raw_backing_store: QByteArray | None = None  # keep raw bytes alive for QImage(raw)

        # Resize debouncer
        self._live_resize_timer = QTimer(self)
        self._live_resize_timer.setSingleShot(True)
        self._live_resize_timer.timeout.connect(self._render_scaled)

        # Blackout overlay
        self._blackout = QLabel(self)
        self._blackout.setStyleSheet("background:black;")
        self._blackout.setVisible(False)
        self._blackout.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._blackout.raise_()

        self._blackout_fx = QGraphicsOpacityEffect(self._blackout)
        self._blackout.setGraphicsEffect(self._blackout_fx)
        self._blackout_anim = QPropertyAnimation(self._blackout_fx, b"opacity", self)
        self._blackout_anim.setDuration(250)
        self._blackout_anim.finished.connect(
            lambda: self._blackout.setVisible(self._blackout_fx.opacity() > 0.0)
        )
        self._is_blackout = False

    # ---------- Public API ----------
    def set_scale_mode(self, mode: ScaleMode) -> None:
        if mode is self._scale_mode:
            return
        self._scale_mode = mode
        self._render_scaled()

    def scale_mode(self) -> ScaleMode:
        return self._scale_mode

    def set_image_qimage(self, img: QImage) -> None:
        """Set an already-decoded image."""
        self._base_image = img
        self._render_scaled()

    def set_image_bytes(
        self,
        data: bytes,
        *,
        width: int | None = None,
        height: int | None = None,
        channels: int | None = None,
        format: str | None = None,
    ) -> bool:
        """
        Load from bytes.

        Modes:
          - Encoded: provide only data (+ optional format: "PNG"/"JPG"...)
          - Raw: also specify width, height, channels in {1,3,4}, tightly packed, 8-bit.
        """
        # Raw mode
        if width is not None and height is not None:
            if channels not in (1, 3, 4):
                raise ValueError("channels must be 1 (Gray), 3 (RGB), or 4 (RGBA).")
            self._raw_backing_store = QByteArray(data)
            bpl = width * channels
            qfmt = {
                1: QImage.Format.Format_Grayscale8,
                3: QImage.Format.Format_RGB888,
                4: QImage.Format.Format_RGBA8888,
            }[channels]
            img = QImage(self._raw_backing_store, width, height, bpl, qfmt)
            if img.isNull():
                return False
            self.set_image_qimage(img)
            return True

        # Encoded mode
        img = QImage.fromData(data, format.encode() if format else None)
        if img.isNull():
            return False
        self.set_image_qimage(img)
        return True

    def blackout(self, on: bool, *, fade_ms: int | None = None) -> None:
        """Fade a full black overlay in/out on top of the image."""
        if on == self._is_blackout:
            return
        if fade_ms is not None:
            self._blackout_anim.setDuration(max(0, int(fade_ms)))
        self._ensure_overlay_covers()
        self._blackout.setVisible(True)
        self._blackout.raise_()
        end = 1.0 if on else 0.0
        if self._blackout_anim.duration() == 0:
            self._blackout_fx.setOpacity(end)
            self._blackout.setVisible(end > 0.0)
            self._is_blackout = on
            return
        self._blackout_anim.stop()
        self._blackout_anim.setStartValue(self._blackout_fx.opacity())
        self._blackout_anim.setEndValue(end)
        self._blackout_anim.start()
        self._is_blackout = on

    # ---------- Internals ----------
    def _render_scaled(self) -> None:
        if not self._base_image or self._base_image.isNull():
            self._image_label.clear()
            return

        # High-quality when idle
        if not self._live_resize_timer.isActive():
            self._transform_mode = Qt.SmoothTransformation

        dpr = self.devicePixelRatioF()
        target = self._image_label.size() * dpr
        tw, th = max(1, int(target.width())), max(1, int(target.height()))
        iw, ih = self._base_image.width(), self._base_image.height()

        if self._scale_mode is ScaleMode.ACTUAL:
            pm = QPixmap.fromImage(self._base_image)
            pm.setDevicePixelRatio(dpr)
            self._image_label.setPixmap(pm)
            self._image_label.setAlignment(Qt.AlignCenter)
            return

        if self._scale_mode is ScaleMode.STRETCH:
            img = self._base_image.scaled(tw, th, Qt.IgnoreAspectRatio, self._transform_mode)
            pm = QPixmap.fromImage(img)
            pm.setDevicePixelRatio(dpr)
            self._image_label.setPixmap(pm)
            return

        if self._scale_mode is ScaleMode.FIT:
            img = self._base_image.scaled(tw, th, Qt.KeepAspectRatio, self._transform_mode)
            pm = QPixmap.fromImage(img)
            pm.setDevicePixelRatio(dpr)
            self._image_label.setPixmap(pm)
            return

        # FILL (cover): scale then center-crop
        scale = max(tw / iw, th / ih)
        sw, sh = max(1, int(iw * scale)), max(1, int(ih * scale))
        scaled = self._base_image.scaled(sw, sh, Qt.KeepAspectRatio, self._transform_mode)
        x = max(0, (sw - tw) // 2)
        y = max(0, (sh - th) // 2)
        w, h = min(tw, sw), min(th, sh)
        cropped = scaled.copy(x, y, w, h)
        pm = QPixmap.fromImage(cropped)
        pm.setDevicePixelRatio(dpr)
        self._image_label.setPixmap(pm)

    def _ensure_overlay_covers(self):
        self._blackout.setGeometry(self.rect())

    # ---------- QWidget overrides ----------
    def resizeEvent(self, ev):
        # Fast during live resize, then smooth once settled
        self._transform_mode = Qt.FastTransformation
        self._render_scaled()
        self._live_resize_timer.start(120)
        self._ensure_overlay_covers()
        super().resizeEvent(ev)
