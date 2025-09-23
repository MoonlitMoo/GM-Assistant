from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, Optional

from PySide6.QtCore import QEasingCurve, QVariantAnimation, QPointF, QRectF, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsRectItem, QWidget, QGraphicsItem

from .display_state import TransitionMode

@dataclass
class ViewportSnapshot:
    pixmap: QPixmap
    scene_rect: QRectF
    full_rect: QRectF

@dataclass
class TransitionAPI:
    """
    Adapter from DisplayView to the transition system.
    """
    parent: QWidget
    scene: QGraphicsScene
    viewport: Callable[[], ViewportSnapshot]
    get_current: Callable[[], QGraphicsPixmapItem]
    set_current: Callable[[QGraphicsPixmapItem], None]
    prepare_new_under_overlay: Callable[[QPixmap], None]
    on_finish: Callable[[], None] | None = None


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
    """
    1) Freeze the current viewport as a pixmap overlay above the scene
    2) Prepare the new image underneath with `prepare_new_under_overlay`
    3) Animate the overlay’s opacity from 1 → 0, fading out the old image to reveal the new
    4) Remove the overlay once fully transparent
    """
    snap = api.viewport().pixmap
    api.prepare_new_under_overlay(pm_new)

    overlay = QGraphicsPixmapItem(snap)
    overlay.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
    overlay.setOpacity(1.0)
    overlay.setZValue(api.get_current().zValue() + 100)  # well above base
    overlay.setPos(api.viewport().scene_rect.topLeft())
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
    """
    1) Fade a full-scene black rect in (0→1)
    2) Swap to the new image under the cover
    3) Fade the black rect out (1→0)
    """
    snap = api.viewport()
    # Full-scene black cover so it hides any scene-rect resize/jump
    cover = QGraphicsRectItem(snap.full_rect)
    cover.setBrush(Qt.black)
    cover.setPen(Qt.NoPen)
    cover.setOpacity(0.0)
    cover.setZValue(api.get_current().zValue() + 100)  # above base
    api.scene.addItem(cover)

    anim = QVariantAnimation(api.parent)
    anim.setDuration(max(0, int(duration_ms)))
    anim.setEasingCurve(QEasingCurve.InOutQuad)

    # Add a sync to reset the cover on a scene size change
    def _sync_cover_rect(r: QRectF):
        cover.setRect(r)
    api.scene.sceneRectChanged.connect(_sync_cover_rect)

    swapped = {"done": False}
    def tick(v: float, cover=cover):
        # v in [0,1]; first half fade-in, second half fade-out
        if v < 0.5:
            cover.setOpacity(v * 2.0)
        else:
            if not swapped["done"]:
                # Swap/new layout happens while fully covered
                api.prepare_new_under_overlay(pm_new)
                swapped["done"] = True
            cover.setOpacity((1.0 - v) * 2.0)

    def done(cover=cover):
        api.scene.sceneRectChanged.disconnect(_sync_cover_rect)
        api.scene.removeItem(cover)
        if api.on_finish:
            api.on_finish()

    anim.valueChanged.connect(tick)
    anim.finished.connect(done)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.start()


def do_slide_cover(api: TransitionAPI, pm_new: QPixmap, direction: str = "left", duration_ms: int = 300) -> None:
    """
    Freeze the current viewport as a cover, prepare the new image underneath,
    then slide the frozen cover off-screen in the given direction.
    """
    snap = api.viewport()

    # Prepare the new image *underneath* the overlay before we move it
    api.prepare_new_under_overlay(pm_new)

    overlay = QGraphicsPixmapItem(snap.pixmap)
    overlay.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
    overlay.setOpacity(1.0)
    overlay.setZValue(api.get_current().zValue() + 100)
    new_snap = api.viewport()
    start_pos: QPointF = new_snap.scene_rect.topLeft()
    overlay.setPos(start_pos)
    api.scene.addItem(overlay)

    w = new_snap.scene_rect.width()
    h = new_snap.scene_rect.height()

    if direction == "left":
        delta = QPointF(-w, 0)
    elif direction == "right":
        delta = QPointF(+w, 0)
    elif direction == "up":
        delta = QPointF(0, -h)
    else:  # "down"
        delta = QPointF(0, +h)

    anim = QVariantAnimation(api.parent)
    anim.setDuration(max(0, int(duration_ms)))
    anim.setEasingCurve(QEasingCurve.InOutQuad)

    def tick(t: float, overlay=overlay, start_pos=start_pos, delta=delta):
        # t in [0,1]: linear interpolation of position
        overlay.setPos(start_pos + delta * float(t))

    def done(overlay=overlay):
        api.scene.removeItem(overlay)
        if api.on_finish:
            api.on_finish()

    anim.valueChanged.connect(tick)
    anim.finished.connect(done)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.start()



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
