from dataclasses import dataclass
from typing import List, Optional
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

    # ------------------ read ------------------
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
        # mark first as revealed for future Player window logic (no UI here)
        self._list[self._cursor].is_revealed = True

    def next(self) -> None:
        if not self._running or not self._list:
            return
        self._cursor = (self._cursor + 1) % len(self._list)
        self._list[self._cursor].is_revealed = True

    def back(self) -> None:
        if not self._running or not self._list:
            return
        self._cursor = (self._cursor - 1 + len(self._list)) % len(self._list)
        self._list[self._cursor].is_revealed = True

    def end(self) -> None:
        self._running = False
        self._cursor = None
