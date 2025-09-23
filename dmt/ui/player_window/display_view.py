from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt, QByteArray, QVariantAnimation, QEasingCurve, QRectF
from PySide6.QtGui import QImage, QPixmap, QPainter
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem

from .display_state import ScaleMode


class BaseImageItem(QGraphicsPixmapItem):
    """ Bottom level image canvas. """
    def __init__(self) -> None:
        super().__init__()
        self.setTransformationMode(Qt.SmoothTransformation)

    def set_qimage(self, img: QImage) -> None:
        pm = QPixmap.fromImage(img)
        self.setPixmap(pm)


class BlackoutOverlayItem(QGraphicsRectItem):
    """Full-scene black cover. Opacity is animated externally."""
    def __init__(self) -> None:
        super().__init__()
        self.setBrush(Qt.black)
        self.setPen(Qt.NoPen)
        self.setOpacity(0.0)       # start hidden
        self.setVisible(False)     # toggled by animation driver


class DisplayView(QGraphicsView):
    """
    GraphicsView-based display with:
      - Base image item (pixmap)
      - Blackout overlay (full cover, animated)
      - Scale modes compatible with existing API
      - Ctrl+Wheel zoom; panning via scrollbars (drag mode optional)
    """
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        scene = QGraphicsScene(self)
        self.setScene(scene)
        self.setFrameStyle(0)
        self.setBackgroundBrush(Qt.black)
        self.setRenderHints(self.renderHints() |
                            QPainter.SmoothPixmapTransform |
                            QPainter.Antialiasing)

        # Items & z-order
        self._base = BaseImageItem()
        self._base.setZValue(0)
        scene.addItem(self._base)

        self._blackout = BlackoutOverlayItem()
        self._blackout.setZValue(1000)
        scene.addItem(self._blackout)

        # State
        self._scale_mode: ScaleMode = ScaleMode.FIT
        self._zoom_factor: float = 1.0

        # Blackout animation driver
        self._blackout_anim = QVariantAnimation(self)
        self._blackout_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._blackout_anim.setDuration(250)
        self._blackout_anim.valueChanged.connect(self._apply_blackout_opacity)
        self._blackout_anim.finished.connect(self._finalize_blackout_visibility)

        # Disable scrollbars unless zooming/panning
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Optional: enable hand-drag panning
        # self.setDragMode(QGraphicsView.ScrollHandDrag)

    # ---------- Public API (same names as before) ----------
    def set_scale_mode(self, mode: ScaleMode) -> None:
        if mode is self._scale_mode:
            return
        self._scale_mode = mode
        self._apply_scale_mode()

    def scale_mode(self) -> ScaleMode:
        return self._scale_mode

    def set_image_qimage(self, img: QImage) -> None:
        self._base.set_qimage(img)
        # Scene rect tracks the image bounds
        pm = self._base.pixmap()
        r = QRectF(0, 0, pm.width(), pm.height()) if not pm.isNull() else QRectF()
        self.scene().setSceneRect(r)
        self._resize_overlays_to_scene()
        self._apply_scale_mode()

    def set_image_bytes(
        self,
        data: bytes,
        *,
        width: int | None = None,
        height: int | None = None,
        channels: int | None = None,
        format: str | None = None,
    ) -> bool:
        # Raw mode
        if width is not None and height is not None:
            if channels not in (1, 3, 4):
                raise ValueError("channels must be 1 (Gray), 3 (RGB), or 4 (RGBA).")
            backing = QByteArray(data)
            bpl = width * channels
            qfmt = {
                1: QImage.Format.Format_Grayscale8,
                3: QImage.Format.Format_RGB888,
                4: QImage.Format.Format_RGBA8888,
            }[channels]
            img = QImage(backing, width, height, bpl, qfmt)
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

    def blackout(self, on: bool, *, fade_ms: Optional[int] = None) -> None:
        """Animate a full black overlay in/out."""
        if fade_ms is not None:
            self._blackout_anim.setDuration(max(0, int(fade_ms)))
        start = float(self._blackout.opacity())
        end = 1.0 if on else 0.0
        if start == end:
            # ensure visibility consistent with state
            self._blackout.setVisible(end > 0.0)
            return
        self._ensure_blackout_geometry()
        self._blackout.setVisible(True)  # make sure it's on during animation
        self._blackout_anim.stop()
        self._blackout_anim.setStartValue(start)
        self._blackout_anim.setEndValue(end)
        self._blackout_anim.start()

    # ---------- Internals ----------
    def _apply_scale_mode(self) -> None:
        pm = self._base.pixmap()
        if pm.isNull():
            self.resetTransform()
            return

        if self._scale_mode is ScaleMode.ACTUAL:
            self.resetTransform()
            self.centerOn(self._base)
            return

        if self._scale_mode is ScaleMode.STRETCH:
            # Stretch: ignore aspect; we simulate by fitting then additional scale if needed
            self.fitInView(self.sceneRect(), Qt.IgnoreAspectRatio)
            return

        if self._scale_mode is ScaleMode.FIT:
            self.fitInView(self._base, Qt.KeepAspectRatio)
            return

        # FILL (cover): fit largest dimension (KeepAspectRatio), then allow cropping via view
        self.fitInView(self._base, Qt.KeepAspectRatio)

    def _apply_blackout_opacity(self, v):
        self._blackout.setOpacity(float(v))

    def _finalize_blackout_visibility(self):
        self._blackout.setVisible(self._blackout.opacity() > 0.0)

    def _ensure_blackout_geometry(self):
        # Cover full scene rect
        self._blackout.setRect(self.sceneRect())

    def _resize_overlays_to_scene(self):
        self._ensure_blackout_geometry()

    # ---------- QGraphicsView overrides ----------
    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        # Keep overlays correct on every resize
        self._resize_overlays_to_scene()
        self._apply_scale_mode()

    def wheelEvent(self, ev):
        # Ctrl + Wheel → zoom; otherwise default scroll
        if ev.modifiers() & Qt.ControlModifier:
            delta = ev.angleDelta().y()
            factor = 1.15 if delta > 0 else (1 / 1.15)
            self.scale(factor, factor)
            ev.accept()
        else:
            super().wheelEvent(ev)
