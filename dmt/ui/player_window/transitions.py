from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, Optional

from PySide6.QtCore import QEasingCurve, QVariantAnimation, QPointF, QRectF
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsRectItem, QWidget, QGraphicsItem

from .display_state import TransitionMode

@dataclass
class TransitionAPI:
    """
    Adapter from DisplayView to the transition system.
    """
    # Basic frame info
    parent: QWidget
    scene: QGraphicsScene
    get_current: Callable[[], QGraphicsPixmapItem]
    set_current: Callable[[QGraphicsPixmapItem], None]
    scene_width: Callable[[], float]
    scene_height: Callable[[], float]
    # Any final clean up
    on_finish: Callable[[], None] | None = None
    # Freeze frame info
    grab_viewport: Optional[Callable[[], QPixmap]] = None
    viewport_scene_topleft: Optional[Callable[[], QPointF]] = None
    prepare_new_under_overlay: Optional[Callable[[QPixmap], None]] = None
    viewport_scene_rect: Optional[Callable[[], QRectF]] = None

# ---- Helpers ----
def _make_new_item(api: TransitionAPI, pm: QPixmap, z: float) -> QGraphicsPixmapItem:
    item = QGraphicsPixmapItem(pm)
    item.setTransformationMode(api.get_current().transformationMode())
    item.setZValue(z)
    api.scene.addItem(item)
    return item

def do_cut(api: TransitionAPI, pm_new: QPixmap, duration_ms: int = 0) -> None:
    old = api.get_current()
    new = _make_new_item(api, pm_new, z=old.zValue() + 1)
    api.set_current(new)
    api.scene.removeItem(old)
    if api.on_finish:
        api.on_finish()


def do_crossfade(api: TransitionAPI, pm_new: QPixmap, duration_ms: int = 240) -> None:
    snap = api.grab_viewport()
    # Swap to NEW content *under* the overlay right now (fit/resize/etc. inside)
    api.prepare_new_under_overlay(pm_new)

    overlay = QGraphicsPixmapItem(snap)
    overlay.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
    overlay.setOpacity(1.0)
    overlay.setZValue(api.get_current().zValue() + 100)  # well above base
    overlay.setPos(api.viewport_scene_topleft())
    api.scene.addItem(overlay)

    anim = QVariantAnimation(api.parent)
    anim.setDuration(duration_ms)
    anim.setEasingCurve(QEasingCurve.InOutQuad)

    def tick(v, overlay=overlay):
        overlay.setOpacity(1.0 - float(v))

    def done(overlay=overlay):
        api.scene.removeItem(overlay)
        if api.on_finish:
            api.on_finish()

    anim.valueChanged.connect(tick)
    anim.finished.connect(done)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.start()


def do_fade_black(api: TransitionAPI, pm_new: QPixmap, duration_ms: int = 220) -> None:
    pass


def do_slide_cover(api: TransitionAPI, pm_new: QPixmap, direction: str = "left", duration_ms: int = 300) -> None:
    pass


# ---- Registry ----
TransitionFunc = Callable[[TransitionAPI, QPixmap, int], None]

REGISTRY: Dict[TransitionMode, TransitionFunc] = {
    TransitionMode.CUT:        do_cut,
    TransitionMode.CROSSFADE:  do_crossfade,
    TransitionMode.FADE_BLACK: do_fade_black,
    TransitionMode.SLIDE_LEFT:  lambda api, pm, d=300: do_slide_cover(api, pm, "left", d),
    TransitionMode.SLIDE_RIGHT: lambda api, pm, d=300: do_slide_cover(api, pm, "right", d),
    TransitionMode.SLIDE_UP:    lambda api, pm, d=300: do_slide_cover(api, pm, "up", d),
    TransitionMode.SLIDE_DOWN:  lambda api, pm, d=300: do_slide_cover(api, pm, "down", d),
}
