from __future__ import annotations
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
    """In-memory initiative list. Sort on insert; allow manual reorders."""
    _id_counter = itertools.count(1)

    def __init__(self) -> None:
        self._list: List[Combatant] = []
        self._cursor: Optional[int] = None
        self._running: bool = False
        self._round: int = 0  # 0 = not started

    # ---------- reads ----------
    def list(self) -> List[Combatant]:
        return self._list

    def cursor_index(self) -> Optional[int]:
        return self._cursor

    def is_running(self) -> bool:
        return self._running

    def round(self) -> int:
        return self._round

    # ---------- mutations ----------
    def add(self, name: str, initiative: int) -> Combatant:
        c = Combatant(next(self._id_counter), name.strip(), int(initiative), False)
        pos = 0
        while pos < len(self._list) and self._list[pos].initiative >= c.initiative:
            pos += 1
        self._list.insert(pos, c)
        return c

    def remove_by_index(self, index: int) -> None:
        if 0 <= index < len(self._list):
            was_current = (index == self._cursor)
            del self._list[index]
            if not self._list:
                self.end()
                return
            if self._cursor is not None:
                if was_current:
                    self._cursor = min(index, len(self._list) - 1)
                elif index < self._cursor:
                    self._cursor -= 1

    def update_by_index(self, index: int, *, name: Optional[str] = None, initiative: Optional[int] = None) -> None:
        if not (0 <= index < len(self._list)):
            return
        c = self._list[index]
        if name is not None:
            c.name = name.strip()
        if initiative is not None:
            c.initiative = int(initiative)
            item = self._list.pop(index)
            pos = 0
            while pos < len(self._list) and self._list[pos].initiative >= item.initiative:
                pos += 1
            self._list.insert(pos, item)
            if self._cursor is not None:
                if index == self._cursor:
                    self._cursor = pos
                elif index < self._cursor <= pos:
                    self._cursor -= 1
                elif pos <= self._cursor < index:
                    self._cursor += 1

    def set_revealed(self, index: int, revealed: bool) -> None:
        if 0 <= index < len(self._list):
            self._list[index].is_revealed = bool(revealed)

    def move_row(self, src: int, dst: int) -> None:
        if src == dst or not (0 <= src < len(self._list)) or not (0 <= dst <= len(self._list)):
            return
        item = self._list.pop(src)
        self._list.insert(dst, item)
        if self._cursor is not None:
            if src == self._cursor:
                self._cursor = dst
            else:
                if src < self._cursor <= dst:
                    self._cursor -= 1
                elif dst <= self._cursor < src:
                    self._cursor += 1

    # ---------- flow ----------
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
            self._round = max(1, self._round - 1)
        self._list[self._cursor].is_revealed = True

    def end(self) -> None:
        self._running = False
        self._cursor = None
        self._round = 0

    # ---------- resets ----------
    def reset_round_and_visibility(self) -> None:
        self._round = 1
        self._cursor = 0
        for c in self._list:
            c.is_revealed = False
        self._list[0].is_revealed = True

    def clear(self) -> None:
        self._list.clear()
        self._cursor = None
        self._running = False
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
