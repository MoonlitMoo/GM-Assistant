from __future__ import annotations
from typing import Optional, Iterable, Tuple
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session
from dmt.db.models import Folder, Album


class FolderRepo:
    def get(self, s: Session, folder_id: int) -> Folder | None:
        return s.get(Folder, folder_id)

    def create(self, s: Session, parent_id: Optional[int], name: str, position: int) -> Folder:
        f = Folder(parent_id=parent_id, name=name, position=position)
        s.add(f)
        s.flush()
        return f

    def delete(self, s: Session, folder_id: int) -> Tuple[int, int]:
        """ Returns the old parent if and position"""
        f = s.get(Folder, folder_id)
        if f:
            ret = f.parent_id, f.position
            s.delete(f)
            return ret
        return None, None

    def next_child_position(self, s: Session, parent_id: Optional[int]) -> int:
        # Max position among siblings (folders + albums)
        max_pos_folder = s.execute(
            select(func.max(Folder.position)).where(Folder.parent_id.is_(parent_id))
        ).scalar() or -1
        max_pos_album = s.execute(
            select(func.max(Album.position)).where(Album.parent_id.is_(parent_id))
        ).scalar() or -1
        return max(max_pos_folder, max_pos_album) + 1

    def children_flat(self, s: Session, parent_id: Optional[int]) -> tuple:
        if parent_id is not None:
            f = self.get(s, parent_id)
            return f.children
        folders = s.execute(select(Folder).where(Folder.parent_id.is_(parent_id))).scalars().all()
        albums = s.execute(select(Album).where(Album.parent_id.is_(parent_id))).scalars().all()
        items = [("folder", f, f.position) for f in folders] + [("album", c, c.position) for c in albums]
        # tie-break by kind then id for stability
        items.sort(key=lambda t: (t[2], 0 if t[0] == "folder" else 1, getattr(t[1], "id", 0)))
        return items

    def reorder_within_parent(self, s: Session, parent_id: Optional[int], old_pos: int, new_pos: int) -> None:
        """Shift a contiguous block within the same parent to move one item from old_pos -> new_pos."""
        if new_pos == old_pos:
            return
        if new_pos > old_pos:
            # 1) Close the gap left at old_pos by shifting everything AFTER it up (-1)
            self.shift_down_after(s, parent_id, old_pos)
            # 2) Restore positions of items strictly beyond the target window by making room at new_pos (+1)
            #    This pushes back items at/after new_pos, leaving exactly one slot at new_pos.
            self.shift_up_from(s, parent_id, new_pos)
        else:
            # 1) Make room at new_pos by shifting everything at/after new_pos down the list (+1)
            self.shift_up_from(s, parent_id, new_pos)
            # 2) Close the gap that appears AFTER old_pos once the moving item vacates it (-1)
            self.shift_down_after(s, parent_id, old_pos)

    def shift_down_after(self, s: Session, parent_id: int | None, old_pos: int) -> None:
        """Decrement positions of siblings after old_pos (folders + albums under same parent)."""
        s.execute(update(Folder).where(Folder.parent_id.is_(parent_id), Folder.position > old_pos)
            .values(position=Folder.position - 1))
        s.execute(update(Album).where(Album.parent_id.is_(parent_id), Album.position > old_pos)
            .values(position=Album.position - 1))

    def shift_up_from(self, s: Session, parent_id: Optional[int], from_pos: int) -> None:
        """Make room at from_pos: positions >= from_pos -> +1 (folders + albums)."""
        s.execute(update(Folder).where(Folder.parent_id == parent_id, Folder.position >= from_pos)
                  .values(position=Folder.position + 1))
        s.execute(update(Album).where(Album.parent_id == parent_id, Album.position >= from_pos)
                  .values(position=Album.position + 1))
