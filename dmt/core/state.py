from enum import Enum
from functools import wraps
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


def remote_op(method):
    """
    Decorator for remote operation methods of the display state.
    Automatically yoinks the data and sends over configured socket.
    - If self.is_receiver is False: send {"op": <method name>, "args": args, "kwargs": kwargs?} over self.socket.
        Then execute locally to sync
    - If True: execute the method locally.
    """
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if getattr(self, "is_receiver", False):
            # Receiver side: execute the operation locally
            return method(self, *args, **kwargs)

        # Sender side: setup call and sanitise enums
        n_args = []
        for i, a in enumerate(args):
            if isinstance(a, (TransitionMode, ScaleMode)):
                n_args.append(a.value)
            else:
                n_args.append(a)
        args = tuple(n_args)

        payload = {"op": method.__name__, "args": args, "kwargs": kwargs}

        # Get the player controller to send with
        sender = getattr(self, "sender", None)
        if sender is None:
            raise RuntimeError("remote_op: instance has no 'sender' to send on")

        try:
            sender.send(obj=payload)
        except Exception as e:
            raise RuntimeError("remote_op failed") from e
        return method(self, *args, **kwargs)

    return wrapper



class DisplayState(QObject):
    """ The display state for driving the player window. Since we run the player window as a separate process it can be
    configured as the receiver or sender. If sender, then remote_op decorated functions are sent via the sender.send(),
    before being run locally.
    As such a command done to the main window display state will be propagated to the player window process, with signals
    emitted in both processes for syncing of state.
    """
    # General Signals
    displayIndexChanged = Signal(int)
    windowedChanged = Signal(bool)
    bringToFront = Signal()
    # Blackout signal
    blackoutChanged = Signal(bool)
    # Image signals
    scaleModeChanged = Signal(ScaleMode)
    imageChanged = Signal(Any)
    transitionModeChanged = Signal(TransitionMode)
    # initiative overlay signals
    initiativeChanged = Signal(list, int, int, bool)
    initiativeOverlayChanged = Signal(int, str, int)

    def __init__(self, on_persist: Callable[[dict], None] | None = None, is_receiver: bool = False,
                 parent: QObject | None = None, autosave_debounce_ms: int = 250,
                 ):
        super().__init__(parent)
        # Remote operation vars
        self.is_receiver = is_receiver
        self.sender = None
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
        self._initiative_round: int = 0
        self._initiative_margin: int = 24
        self._initiative_alignment: str = "top-right"
        self._initiative_scale: float = 100

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
    def initiative_round(self) -> int: return self._initiative_round
    def initiative_margin(self) -> int: return self._initiative_margin
    def initiative_alignment(self) -> str: return self._initiative_alignment
    def initiative_scale(self) -> float: return self._initiative_scale

    # --- Image overlay API ---
    @remote_op
    def set_display_index(self, idx: int) -> None:
        if idx == self._display_index: return
        self._display_index = idx
        self.displayIndexChanged.emit(idx)
        self._mark_dirty()

    @remote_op
    def set_windowed(self, on: bool) -> None:
        if on == self._windowed: return
        self._windowed = on
        self.windowedChanged.emit(on)
        self._mark_dirty()

    @remote_op
    def set_scale_mode(self, mode: ScaleMode | str) -> None:
        if isinstance(mode, str):
            mode = ScaleMode(mode)
        if mode == self._scale_mode: return
        self._scale_mode = mode
        self.scaleModeChanged.emit(mode)
        self._mark_dirty()

    @remote_op
    def set_transition_mode(self, mode: TransitionMode | str) -> None:
        if isinstance(mode, str):
            mode = TransitionMode(mode)
        if mode == self._transition_mode: return
        self._transition_mode = mode
        self.transitionModeChanged.emit(mode)

    @remote_op
    def set_image(self, *a, **k):
        self.imageChanged.emit(*a, **k)

    # ---- Blackout overlay API ----
    @remote_op
    def set_blackout(self, on: bool):
        self._blackout = on
        self.blackoutChanged.emit(on)

    # ---- Initiative overlay API ----
    @remote_op
    def set_initiative(self, names: list[str], current_idx: int, round: int) -> None:
        self._initiative_names = list(names)
        self._initiative_current = int(current_idx) if current_idx is not None else -1
        self._initiative_visible = True
        self._initiative_round = True
        self.initiativeChanged.emit(self._initiative_names, self._initiative_current, round, True)

    @remote_op
    def hide_initiative(self) -> None:
        self._initiative_visible = False
        self.initiativeChanged.emit([], -1, 0, False)

    @remote_op
    def set_initiative_overlay_params(self, margin: int, alignment: str, scale: int):
        self._initiative_margin = margin
        self._initiative_alignment = alignment
        self._initiative_scale = scale
        self.initiativeOverlayChanged.emit(margin, alignment, scale)

    # --- persistence bridge ---
    def snapshot(self) -> dict:
        return {
            "playerDisplay": self._display_index,
            "playerWindowed": self._windowed,
            "fitMode": self._scale_mode.value,
            "transitionMode": self._transition_mode.value,
            "initiativeVisible": self._initiative_visible,
            "initiativeNames": self._initiative_names,
            "initiativeIndex": self._initiative_current,
            "initiativeRound": self._initiative_round,
            "initiativeMargin": self._initiative_margin,
            "initiativeAlignment": self._initiative_alignment,
            "initiativeScale": self._initiative_scale,
        }

    # --- general api ---
    @remote_op
    def bring_to_front(self):
        self.bringToFront.emit()

    @remote_op
    def load_state(self, state: Dict[str, Any]) -> None:
        self.set_display_index(int(state.get("playerDisplay", 0)))
        self.set_windowed(bool(state.get("playerWindowed", True)))
        self.set_scale_mode(ScaleMode(state.get("fitMode", "fit")))
        self.set_transition_mode(TransitionMode(state.get("transitionMode", "crossfade")))
        self._initiative_visible = state.get("initiativeVisible", False)
        if self.initiative_visible():
            self.set_initiative(
                state.get("initiativeNames", []), state.get("initiativeIndex", -1), state.get("initiativeRound", 0)
            )
        else:
            self._initiative_names = state.get("initiativeNames", [])
            self._initiative_current = state.get("initiativeIndex", -1)
            self._initiative_round = state.get("initiativeRound", 0)
        self.set_initiative_overlay_params(
            state.get("initiativeMargin", 24), state.get("initiativeAlignment", 'top-right'), state.get("initiativeScale", 100))

    def _mark_dirty(self):
        self._dirty = True
        if self._on_persist:
            self._debounce.start(self._autosave_delay)

    def _flush_persist(self):
        if self._on_persist and self._dirty:
            self._on_persist(self.snapshot())
            self._dirty = False
