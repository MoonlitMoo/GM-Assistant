import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import itertools


@dataclass
class Combatant:
    id: int
    name: str
    initiative: int
    is_revealed: bool = False


class InitiativeController:
    """Owns the canonical list and the cursor. No DB. Sort only on insert."""
    _id_counter = itertools.count(1)

    def __init__(self):
        self._list: List[Combatant] = []
        self._cursor: Optional[int] = None  # index into _list
        self._running: bool = False
        self._round: int = 0

    # ------------------ read ------------------
    def round(self) -> int:
        return self._round

    def list(self) -> List[Combatant]:
        return self._list

    def cursor_index(self) -> Optional[int]:
        return self._cursor

    def is_running(self) -> bool:
        return self._running

    # ------------------ mutations ------------------
    def add(self, name: str, initiative: int) -> Combatant:
        c = Combatant(next(self._id_counter), name.strip(), int(initiative))
        # sort-on-insert: find first position with lower initiative; insert before it
        pos = 0
        while pos < len(self._list) and self._list[pos].initiative >= c.initiative:
            pos += 1
        self._list.insert(pos, c)

        # TODO: If running update the cursor.
        return c

    def remove_by_index(self, index: int) -> None:
        if 0 <= index < len(self._list):
            was_current = (index == self._cursor)
            del self._list[index]
            if self._cursor is not None:
                if was_current:
                    # advance to same index (now next item) if possible
                    if index >= len(self._list):
                        self._cursor = len(self._list) - 1 if self._list else None
                elif index < self._cursor:
                    self._cursor -= 1
                # if list is empty, stop
                if not self._list:
                    self.end()

    def update_by_index(self, index: int, *, name: Optional[str] = None, initiative: Optional[int] = None) -> None:
        if 0 <= index < len(self._list):
            c = self._list[index]
            if name is not None:
                c.name = name.strip()
            if initiative is not None:
                # reinsert to maintain "sort on insert" semantics for updates
                c.initiative = int(initiative)
                item = self._list.pop(index)
                # find new sorted slot; do not reorder others beyond normal insert
                pos = 0
                while pos < len(self._list) and self._list[pos].initiative >= item.initiative:
                    pos += 1
                self._list.insert(pos, item)
                # keep current item current if it was current
                if self._cursor is not None:
                    if index == self._cursor:
                        self._cursor = pos
                    else:
                        # adjust cursor if moved across it
                        if index < self._cursor <= pos:
                            self._cursor -= 1
                        elif pos <= self._cursor < index:
                            self._cursor += 1

    def move_row(self, src: int, dst: int) -> None:
        """Manual DM override via drag-and-drop; no sorting here."""
        if src == dst or not (0 <= src < len(self._list)) or not (0 <= dst <= len(self._list)):
            return
        item = self._list.pop(src)
        self._list.insert(dst if dst <= len(self._list) else len(self._list), item)
        if self._cursor is not None:
            if src == self._cursor:
                self._cursor = dst if dst < len(self._list) else len(self._list) - 1
            else:
                # shift cursor if needed
                if src < self._cursor <= dst:
                    self._cursor -= 1
                elif dst <= self._cursor < src:
                    self._cursor += 1

    # ------------------ flow ------------------
    def start(self) -> None:
        if not self._list:
            return
        self._running = True
        if self._cursor is None:
            self._cursor = 0
        if self._round == 0:
            self._round = 1
        self._list[self._cursor].is_revealed = True

    def next(self) -> None:
        if not self._running or not self._list:
            return
        prev = self._cursor
        self._cursor = (self._cursor + 1) % len(self._list)
        if prev is not None and self._cursor == 0:
            self._round += 1
        self._list[self._cursor].is_revealed = True

    def back(self) -> None:
        if not self._running or not self._list:
            return
        prev = self._cursor
        self._cursor = (self._cursor - 1 + len(self._list)) % len(self._list)
        if prev is not None and prev == 0:
            # wrapped backwards from top → go to previous round, clamp at 1
            self._round = max(1, self._round - 1)
        self._list[self._cursor].is_revealed = True

    def end(self) -> None:
        self._running = False
        self._cursor = None
        self._round = 0

    # ----- persistence -----
    def snapshot(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "cursor": self._cursor,
            "round": self._round,
            "list": [
                {
                    "id": c.id,
                    "name": c.name,
                    "initiative": c.initiative,
                    "is_revealed": c.is_revealed,
                } for c in self._list
            ],
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        self._list = []
        for d in state.get("list", []):
            self._list.append(Combatant(
                id=int(d["id"]),
                name=str(d["name"]),
                initiative=int(d["initiative"]),
                is_revealed=bool(d.get("is_revealed", False)),
            ))
        self._cursor = state.get("cursor", None)
        self._running = bool(state.get("running", False))
        self._round = int(state.get("round", 0))

        # ensure cursor is valid
        if self._cursor is not None and not (0 <= self._cursor < len(self._list)):
            self._cursor = 0 if self._list else None
        if self._running and self._round == 0 and self._list:
            self._round = 1
