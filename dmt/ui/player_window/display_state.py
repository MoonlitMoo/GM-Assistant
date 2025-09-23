from enum import Enum
from typing import Callable

from PySide6.QtCore import QObject, Signal, QTimer

class TransitionMode(Enum):
    CUT ="cut"
    CROSSFADE = "crossfade"
    FADE_BLACK = "fade black"
    SLIDE_LEFT = "slide left"
    SLIDE_RIGHT = "slide right"
    SLIDE_UP = "slide up"
    SLIDE_DOWN = "slide down"
    BLUR_DISSOLVE = "blur dissolve"


class ScaleMode(Enum):
    FIT = "fit"
    FIT_NAV = "fit nav"
    STRETCH = "stretch"
    ACTUAL = "actual"


def parse_scale_mode(s: str) -> ScaleMode:
    s = (s or "fit").lower()
    return {
        "fit": ScaleMode.FIT,
        "fit nav": ScaleMode.FIT_NAV,
        "stretch": ScaleMode.STRETCH,
        "actual": ScaleMode.ACTUAL,
    }.get(s, ScaleMode.FIT)


class DisplayState(QObject):
    # Signals
    displayIndexChanged = Signal(int)
    windowedChanged = Signal(bool)
    blackoutChanged = Signal(bool)
    scaleModeChanged = Signal(ScaleMode)
    transitionModeChanged = Signal(TransitionMode)

    def __init__(self, *, scale_mode: ScaleMode, transition_mode: TransitionMode, windowed: bool, display_index: int,
                 on_persist: Callable[[dict], None] | None = None, parent: QObject | None = None,
                 autosave_debounce_ms: int = 250,
    ):
        super().__init__(parent)
        self._scale_mode = scale_mode
        self._transition_mode = transition_mode
        self._windowed = windowed
        self._blackout = False
        self._display_index = display_index

        self._on_persist = on_persist
        self._dirty = False
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._flush_persist)
        self._autosave_delay = autosave_debounce_ms

    # --- getters ---
    def scale_mode(self) -> ScaleMode: return self._scale_mode
    def transition_mode(self) -> TransitionMode: return self._transition_mode
    def windowed(self) -> bool: return self._windowed
    def blackout(self) -> bool: return self._blackout
    def display_index(self) -> int: return self._display_index

    # --- setters (emit + schedule persist) ---
    def set_scale_mode(self, mode: ScaleMode) -> None:
        if mode == self._scale_mode: return
        self._scale_mode = mode
        self.scaleModeChanged.emit(mode)
        self._mark_dirty()

    def set_transition_mode(self, mode: TransitionMode) -> None:
        if mode == self._transition_mode: return
        self._transition_mode = mode
        self.transitionModeChanged.emit(mode)

    def set_windowed(self, on: bool) -> None:
        if on == self._windowed: return
        self._windowed = on
        self.windowedChanged.emit(on)
        self._mark_dirty()

    def set_display_index(self, idx: int) -> None:
        if idx == self._display_index: return
        self._display_index = idx
        self.displayIndexChanged.emit(idx)
        self._mark_dirty()

    def set_blackout(self, on: bool):
        self._blackout = on
        self.blackoutChanged.emit(on)

    # --- persistence bridge ---
    def snapshot(self) -> dict:
        return {
            "fitMode": self._scale_mode.value,
            "playerWindowed": self._windowed,
            "playerDisplay": self._display_index,
        }

    def _mark_dirty(self):
        self._dirty = True
        if self._on_persist:
            self._debounce.start(self._autosave_delay)

    def _flush_persist(self):
        if self._on_persist and self._dirty:
            self._on_persist(self.snapshot())
            self._dirty = False
