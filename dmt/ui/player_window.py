from __future__ import annotations
from enum import Enum

from PySide6.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QByteArray, Signal, QObject
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QToolButton, QMenu
from PySide6.QtGui import QImage, QPixmap, QActionGroup, QAction

from dmt.core.config import Config


class ScaleMode(Enum):
    FIT = "fit"  # letterbox, keep AR
    FILL = "fill"  # cover, keep AR, crop overflow
    STRETCH = "stretch"  # fill, ignore AR
    ACTUAL = "actual"  # 1:1 pixels, centered


class PlayerWindow(QWidget):
    """ Separate window that contains information for the players. """

    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.setObjectName("PlayerWindow")
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self._cfg = cfg

        self._raw_backing_store = None
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setStyleSheet("background-color: black;")
        self._image_label.setScaledContents(False)

        self._scale_mode = ScaleMode.FIT
        self._base_image: QImage | None = None
        self._transform_mode = Qt.SmoothTransformation
        self._live_resize_timer = QTimer(self)
        self._live_resize_timer.setSingleShot(True)
        self._live_resize_timer.timeout.connect(self._render_scaled)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._image_label)

        self._fade = QPropertyAnimation(self._image_label, b"windowOpacity", self)
        self._fade.setDuration(300)

        self.apply_config(cfg)

    def apply_config(self, cfg: Config) -> None:
        """Apply windowed vs fullscreen preference."""
        self._cfg = cfg
        if cfg.playerWindowed:
            # Restore normal, resizable window
            self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowSystemMenuHint |
                                Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
            self.showNormal()
            self.resize(1024, 768)  # only as a default first size
        else:
            self.setWindowFlag(Qt.FramelessWindowHint, True)
            self.showFullScreen()

    # -------- Rendering --------
    def set_image_qimage(self, img: QImage) -> None:
        """Set the base image (already decoded) and render."""
        self._base_image = img
        self._render_scaled()

    def _render_scaled(self) -> None:
        """Render _base_image into a pixmap sized for the label and current scale mode."""
        if not self._base_image or self._base_image.isNull():
            self._image_label.clear()
            return

        # Switch back to high-quality when resize settles
        if not self._live_resize_timer.isActive():
            self._transform_mode = Qt.SmoothTransformation

        # Compute target (consider HiDPI)
        dpr = self.devicePixelRatioF()
        target_size = self._image_label.size() * dpr
        tw, th = max(1, int(target_size.width())), max(1, int(target_size.height()))
        iw, ih = self._base_image.width(), self._base_image.height()

        if self._scale_mode is ScaleMode.ACTUAL:
            # Centered, no scaling. (Optionally clamp to window or add scroll/pan in future.)
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

        # FIT / FILL: keep aspect ratio
        if self._scale_mode is ScaleMode.FIT:
            img = self._base_image.scaled(tw, th, Qt.KeepAspectRatio, self._transform_mode)
            pm = QPixmap.fromImage(img)
            pm.setDevicePixelRatio(dpr)
            self._image_label.setPixmap(pm)
            return

        # FILL (Cover): scale to cover target, then center-crop to target rect
        # 1) scale with AR preserved so that the scaled image >= target in both axes
        scale = max(tw / iw, th / ih)
        sw, sh = max(1, int(iw * scale)), max(1, int(ih * scale))
        scaled = self._base_image.scaled(sw, sh, Qt.KeepAspectRatio, self._transform_mode)

        # 2) crop centered to the target size (guard against off-by-one)
        x = max(0, (sw - tw) // 2)
        y = max(0, (sh - th) // 2)
        w = min(tw, sw)
        h = min(th, sh)
        cropped = scaled.copy(x, y, w, h)

        pm = QPixmap.fromImage(cropped)
        pm.setDevicePixelRatio(dpr)
        self._image_label.setPixmap(pm)

    # -------- QWidget Overrides --------
    def resizeEvent(self, ev):
        # Fast during live resize; schedule a smooth re-render after a short idle.
        self._transform_mode = Qt.FastTransformation
        self._render_scaled()
        self._live_resize_timer.start(120)  # adjust debounce as desired
        super().resizeEvent(ev)

    # -------- Main Window tools --------
    def set_image_bytes(
            self,
            data: bytes,
            width: int | None = None,
            height: int | None = None,
            channels: int | None = None,
            format: str | None = None,
    ) -> bool:
        """
        Display image from bytes.

        Modes:
          - Encoded: pass only `data`, optionally `format` ("PNG", "JPG", etc.).
          - Raw: also pass `width`, `height`, and `channels` (1, 3, or 4).
            Assumes 8 bits per channel, tightly packed rows (no padding).
        """
        # Raw mode
        if width is not None and height is not None:
            if channels not in (1, 3, 4):
                raise ValueError("channels must be 1 (Gray), 3 (RGB), or 4 (RGBA).")

            # Keep backing store alive so QImage memory stays valid
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

            # Hand off to scaling pipeline
            self.set_image_qimage(img)
            return True

        # Encoded mode
        img = QImage.fromData(data, format.encode() if format else None)
        if img.isNull():
            return False

        self.set_image_qimage(img)
        return True

    def set_scale_mode(self, mode: ScaleMode) -> None:
        """Change scaling behavior and re-render."""
        self._scale_mode = mode
        self._render_scaled()

    def fade_out_in(self):
        self._fade.stop()
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.start()
