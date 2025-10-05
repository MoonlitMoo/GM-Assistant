from enum import Enum
from typing import Callable, Dict, Any

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
    initiativeChanged = Signal(list, int, bool)

    def __init__(self, on_persist: Callable[[dict], None] | None = None, parent: QObject | None = None,
                 autosave_debounce_ms: int = 250,
    ):
        super().__init__(parent)
        # General defaults
        self._display_index = 0
        self._windowed = True
        # Overlay defaults
        self._scale_mode = ScaleMode.FIT
        self._transition_mode = TransitionMode.CROSSFADE
        self._blackout = False
        self._initiative_visible = False
        self._initiative_names: list[str] = []
        self._initiative_current: int = -1

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
    def initiative_visible(self) -> bool: return self._initiative_visible
    def initiative_items(self) -> list: return self._initiative_names
    def initiative_index(self) -> int: return self._initiative_current

    # --- Image overlay API ---
    def set_display_index(self, idx: int) -> None:
        if idx == self._display_index: return
        self._display_index = idx
        self.displayIndexChanged.emit(idx)
        self._mark_dirty()

    def set_windowed(self, on: bool) -> None:
        if on == self._windowed: return
        self._windowed = on
        self.windowedChanged.emit(on)
        self._mark_dirty()

    def set_scale_mode(self, mode: ScaleMode) -> None:
        if mode == self._scale_mode: return
        self._scale_mode = mode
        self.scaleModeChanged.emit(mode)
        self._mark_dirty()

    def set_transition_mode(self, mode: TransitionMode) -> None:
        if mode == self._transition_mode: return
        self._transition_mode = mode
        self.transitionModeChanged.emit(mode)

    # ---- Blackout overlay API ----
    def set_blackout(self, on: bool):
        self._blackout = on
        self.blackoutChanged.emit(on)

    # ---- Initiative overlay API ----
    def set_initiative(self, names: list[str], current_idx: int) -> None:
        self._initiative_names = list(names)
        self._initiative_current = int(current_idx) if current_idx is not None else -1
        self._initiative_visible = True
        self.initiativeChanged.emit(self._initiative_names, self._initiative_current, True)

    def update_initiative(self, names: list[str], current_idx: int) -> None:
        self._initiative_names = list(names)
        self._initiative_current = int(current_idx) if current_idx is not None else -1
        self.initiativeChanged.emit(self._initiative_names, self._initiative_current, self._initiative_visible)

    def hide_initiative(self) -> None:
        self._initiative_visible = False
        self.initiativeChanged.emit([], -1, False)

    # --- persistence bridge ---
    def snapshot(self) -> dict:
        return {
            "playerDisplay": self._display_index,
            "playerWindowed": self._windowed,
            "fitMode": self._scale_mode.value,
            "transitionMode": self._transition_mode.value,
            "initiativeVisible": self._initiative_visible,
            "initiativeNames": self._initiative_names,
            "initiativeIndex": self._initiative_current
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        self._display_index = int(state.get("playerDisplay", 0))
        self._windowed = bool(state.get("playerWindowed", True))
        self._scale_mode = ScaleMode(state.get("fitMode", "fit"))
        self._transition_mode = TransitionMode(state.get("transitionMode", "crossfade"))
        self._initiative_visible = state.get("initiativeVisible", False)
        self._initiative_names = state.get("initiativeNames", [])
        self._initiative_current = state.get("initiativeIndex", -1)

    def _mark_dirty(self):
        self._dirty = True
        if self._on_persist:
            self._debounce.start(self._autosave_delay)

    def _flush_persist(self):
        if self._on_persist and self._dirty:
            self._on_persist(self.snapshot())
            self._dirty = False
