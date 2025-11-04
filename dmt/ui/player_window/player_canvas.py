from __future__ import annotations

import base64
from typing import Optional, Collection

from PySide6.QtCore import Qt, QByteArray, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QImage, QPixmap, QPainter
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem

from dmt.core.state import ScaleMode, TransitionMode
from .transitions import REGISTRY, TransitionAPI, ViewportSnapshot


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


class PlayerCanvas(QGraphicsView):
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

        # Blackout overlay
        self._blackout = BlackoutOverlayItem()
        self._blackout.setZValue(1000)
        scene.addItem(self._blackout)

        # Blackout animation driver
        self._blackout_anim = QVariantAnimation(self)
        self._blackout_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._blackout_anim.setDuration(250)
        self._blackout_anim.valueChanged.connect(self._apply_blackout_opacity)
        self._blackout_anim.finished.connect(self._finalize_blackout_visibility)

        # Disable scrollbars unless zooming/panning
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Navigation config
        self._nav_enabled: bool = True
        self._nav_modes: set[ScaleMode] = {ScaleMode.ACTUAL, ScaleMode.FIT_NAV}  # which modes allow nav
        self._nav_require_ctrl: bool = False
        self._zoom_min: float = 0.25
        self._zoom_max: float = 8.0
        self._user_zoom: float = 1.0
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)

        # State
        self._scale_mode: ScaleMode = ScaleMode.FIT
        self._apply_scale_mode()
        self._transition_mode: TransitionMode = TransitionMode.CROSSFADE
        self._transition_running: bool = False

    # ---------- Image API ----------
    def set_scale_mode(self, mode: ScaleMode) -> None:
        if mode is self._scale_mode:
            return
        self._scale_mode = mode
        self._apply_scale_mode()
        self._sync_nav_state()

    def scale_mode(self) -> ScaleMode:
        return self._scale_mode

    def set_transition_mode(self, mode: TransitionMode) -> None:
        self._transition_mode = mode

    def transition_mode(self) -> TransitionMode:
        return self._transition_mode

    def configure_navigation(self, *, enable: bool, modes: Collection[ScaleMode] | None = None,
                             require_ctrl: bool = True, min_zoom: float = 0.25, max_zoom: float = 8.0) -> None:
        """Enable/disable panning+zooming and specify which ScaleModes it applies to."""
        self._nav_enabled = bool(enable)
        self._nav_modes = set(modes) if modes is not None else self._nav_modes
        self._nav_require_ctrl = bool(require_ctrl)
        self._zoom_min = float(min_zoom)
        self._zoom_max = float(max_zoom)
        self._sync_nav_state()

    def set_image_qimage(self, img: QImage) -> None:
        pm_new = QPixmap.fromImage(img)

        if self._base.pixmap().isNull() or self._transition_mode == TransitionMode.CUT:
            self._base.setPixmap(pm_new)
            self.scene().setSceneRect(0, 0, pm_new.width(), pm_new.height())
            self._resize_overlays_to_scene()
            self._apply_scale_mode()
            return

        if self._transition_running:
            self._base.setPixmap(pm_new)
            return
        self._transition_running = True

        def get_current(): return self._base
        def set_current(new_item): self._base = new_item
        def on_finish(): self._transition_running = False

        api = TransitionAPI(
            parent=self,
            scene=self.scene(),
            viewport=self._viewport_snapshot,
            get_current=get_current,
            set_current=set_current,
            on_finish=on_finish,
            prepare_new_under_overlay=self._prepare_new_under_overlay,
        )

        fn = REGISTRY.get(self._transition_mode) or REGISTRY[TransitionMode.CROSSFADE]
        fn(api, pm_new, 260)

    def set_image_bytes(self, data: bytes, *, width: int | None = None, height: int | None = None,
                        channels: int | None = None, format: str | None = None) -> bool:
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

        # Encoded mode (hack fix for coverting str to bytes)
        if isinstance(data, str):
            data = base64.b64decode(data)
        img = QImage.fromData(data, format.encode() if format else None)
        if img.isNull():
            return False
        self.set_image_qimage(img)
        return True

    # ---------- Blackout overlay API ----------
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

    # ---------- Image Internals ----------
    def _apply_scale_mode(self) -> None:
        pm = self._base.pixmap()
        if pm.isNull():
            self.resetTransform()
            self._user_zoom = 1.0
            return

        # Reset to the mode's baseline transform
        if self._scale_mode is ScaleMode.ACTUAL:
            self.resetTransform()
            self.centerOn(self._base)
        elif self._scale_mode is ScaleMode.STRETCH:
            self.fitInView(self.sceneRect(), Qt.IgnoreAspectRatio)
        elif self._scale_mode is ScaleMode.FIT:
            self.fitInView(self._base, Qt.KeepAspectRatio)
        else:  # FILL
            self.fitInView(self._base, Qt.KeepAspectRatio)

        # After refit, user zoom resets to "1x"
        self._user_zoom = 1.0  # <— add

    # ---------- Blackout Internals ----------
    def _apply_blackout_opacity(self, v):
        self._blackout.setOpacity(float(v))

    def _finalize_blackout_visibility(self):
        self._blackout.setVisible(self._blackout.opacity() > 0.0)

    def _ensure_blackout_geometry(self):
        # Cover full scene rect
        self._blackout.setRect(self.sceneRect())

    # ---------- General Internals ----------
    def _resize_overlays_to_scene(self):
        self._ensure_blackout_geometry()

    def _nav_active(self) -> bool:
        return self._nav_enabled and (self._scale_mode in self._nav_modes)

    def _sync_nav_state(self) -> None:
        active = self._nav_active()
        self.setDragMode(QGraphicsView.ScrollHandDrag if active else QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse if active else QGraphicsView.AnchorViewCenter)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)

    # ---- Transition helpers ----
    def _viewport_snapshot(self) -> ViewportSnapshot:
        pm = self.viewport().grab()
        rect = self.mapToScene(self.viewport().rect()).boundingRect()
        return ViewportSnapshot(pixmap=pm, scene_rect=rect, full_rect=self.sceneRect())

    def _prepare_new_under_overlay(self, pm_new: QPixmap) -> None:
        """Swap to the NEW image and finalize layout *before* fading out the frozen overlay."""
        self._base.setPixmap(pm_new)
        # Finalize scene bounds to NEW content
        self.scene().setSceneRect(0, 0, pm_new.width(), pm_new.height())
        self._resize_overlays_to_scene()
        self._base.setScale(1.0)
        self._base.setPos(0, 0)
        self._apply_scale_mode()

    # ---------- QGraphicsView overrides ----------
    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        # Keep overlays correct on every resize
        self._resize_overlays_to_scene()
        if not self._nav_active():
            self._apply_scale_mode()

    def wheelEvent(self, ev):
        if self._nav_active() and (not self._nav_require_ctrl or (ev.modifiers() & Qt.ControlModifier)):
            delta = ev.angleDelta().y()
            step = 1.15 if delta > 0 else (1.0 / 1.15)

            # Compute the zoom we'd have after applying the step
            new_zoom = self._user_zoom * step
            # Clamp and compute the relative factor to apply now
            clamped = max(self._zoom_min, min(self._zoom_max, new_zoom))
            if clamped != self._user_zoom:
                factor = clamped / self._user_zoom
                self._user_zoom = clamped
                super().scale(factor, factor)
            ev.accept()
            return
        self._resize_overlays_to_scene()
        super().wheelEvent(ev)
