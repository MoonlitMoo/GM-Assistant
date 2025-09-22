from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QByteArray
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PySide6.QtGui import QImage, QPixmap

from .display_state import ScaleMode, DisplayState


class PlayerWindow(QWidget):
    """ Separate window that contains information for the players. """

    def __init__(self, display_state: DisplayState) -> None:
        super().__init__()
        self.setObjectName("PlayerWindow")
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)

        # Rendering widget
        self._raw_backing_store = None
        self._base_image = None
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setStyleSheet("background-color: black;")
        self._image_label.setScaledContents(False)
        # Rendering modifiers
        self._scale_mode = ScaleMode.FIT
        self._base_image: QImage | None = None
        self._transform_mode = Qt.SmoothTransformation
        self._live_resize_timer = QTimer(self)
        self._live_resize_timer.setSingleShot(True)
        self._live_resize_timer.timeout.connect(self._render_scaled)

        # Set up display state
        self._display_state = display_state
        self.set_scale_mode(self._display_state.scale_mode())
        self._apply_window_mode(self._display_state.windowed())
        # Subscribe to changes
        self._display_state.scaleModeChanged.connect(self.set_scale_mode)
        self._display_state.windowedChanged.connect(self._apply_window_mode)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._image_label)

        self._fade = QPropertyAnimation(self._image_label, b"windowOpacity", self)
        self._fade.setDuration(300)

    # ------ DisplayState functions -------
    def _apply_window_mode(self, windowed: bool):
        if windowed:
            self.setWindowFlags(Qt.Window | Qt.WindowTitleHint |
                                Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint |
                                Qt.WindowCloseButtonHint)
            self.showNormal()
        else:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
            self.showFullScreen()

    def set_scale_mode(self, mode: ScaleMode):
        self._scale_mode = mode
        self._render_scaled()

    # -------- Rendering functions --------
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

    def fade_out_in(self):
        self._fade.stop()
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.start()
