from __future__ import annotations

from typing import Iterable

from sqlalchemy import select, func, asc
from sqlalchemy.orm import Session, joinedload

from db.models import Playlist, PlaylistItem, PlaylistType


class PlaylistRepo:
    """Pure data access for playlists and items."""

    # --------- Playlists ----------

    def create(self, s: Session, *, name: str, type_: PlaylistType, image_id: int | None = None, query: dict | None = None) -> Playlist:
        p = Playlist(name=name, type=type_, query=query)
        if image_id is not None:
            p.image_id = image_id
        s.add(p)
        s.flush()
        return p

    def get(self, s: Session, playlist_id: int) -> Playlist | None:
        return s.get(Playlist, playlist_id)

    def list_all(self, s: Session, *, type_: PlaylistType | None = None) -> list[Playlist]:
        q = select(Playlist)
        if type_:
            q = q.where(Playlist.type == type_)
        return s.execute(q.order_by(asc(Playlist.name))).scalars().all()

    def update(self, s: Session, playlist_id: int, **fields) -> Playlist | None:
        p = s.get(Playlist, playlist_id)
        if not p:
            return None
        for k, v in fields.items():
            if hasattr(p, k):
                setattr(p, k, v)
        s.flush()
        return p

    def delete(self, s: Session, playlist_id: int) -> bool:
        p = s.get(Playlist, playlist_id)
        if not p:
            return False
        s.delete(p)
        s.flush()
        return True

    def get_or_create_image_playlist(self, s: Session, *, image_id: int, name: str | None = None) -> Playlist:
        existing = s.execute(
            select(Playlist).where(Playlist.type == PlaylistType.IMAGE, Playlist.image_id == image_id)
        ).scalars().first()
        if existing:
            return existing
        return self.create(s, name=name or f"Image {image_id}", type_=PlaylistType.IMAGE, image_id=image_id)

    # ---------- Items (MANUAL/IMAGE) ----------

    def items(self, s: Session, playlist_id: int) -> list[PlaylistItem]:
        return s.execute(
            select(PlaylistItem)
            .where(PlaylistItem.playlist_id == playlist_id)
            .order_by(PlaylistItem.position.asc())
            .options(joinedload(PlaylistItem.song))
        ).scalars().all()

    def _next_position(self, s: Session, playlist_id: int) -> int:
        last = s.execute(
            select(func.max(PlaylistItem.position)).where(PlaylistItem.playlist_id == playlist_id)
        ).scalar_one()
        return 0 if last is None else int(last) + 1

    def append(self, s: Session, playlist_id: int, song_ids: Iterable[int]) -> list[PlaylistItem]:
        pos = self._next_position(s, playlist_id)
        out: list[PlaylistItem] = []
        for sid in song_ids:
            it = PlaylistItem(playlist_id=playlist_id, song_id=sid, position=pos)
            s.add(it)
            out.append(it)
            pos += 1
        s.flush()
        return out

    def insert_at(self, s: Session, playlist_id: int, position: int, song_ids: Iterable[int]) -> list[PlaylistItem]:
        # shift existing >= position
        s.execute(
            select(PlaylistItem).where(PlaylistItem.playlist_id == playlist_id, PlaylistItem.position >= position)
        )
        to_shift = s.execute(
            select(PlaylistItem).where(PlaylistItem.playlist_id == playlist_id, PlaylistItem.position >= position)
        ).scalars().all()
        for it in to_shift:
            it.position += len(list(song_ids))  # evaluate once
        # insert
        out: list[PlaylistItem] = []
        p = position
        for sid in song_ids:
            it = PlaylistItem(playlist_id=playlist_id, song_id=sid, position=p)
            s.add(it)
            out.append(it)
            p += 1
        s.flush()
        return out

    def reorder(self, s: Session, playlist_id: int, *, item_id: int, new_position: int) -> None:
        items = self.items(s, playlist_id)
        # normalize by list reindex
        ordered = [it for it in items if it.id != item_id]
        target = next(it for it in items if it.id == item_id)
        new_position = max(0, min(new_position, len(ordered)))
        ordered.insert(new_position, target)
        for idx, it in enumerate(ordered):
            if it.position != idx:
                it.position = idx
        s.flush()

    def remove_items(self, s: Session, playlist_id: int, item_ids: Iterable[int]) -> int:
        items = s.execute(
            select(PlaylistItem).where(PlaylistItem.playlist_id == playlist_id, PlaylistItem.id.in_(list(item_ids)))
        ).scalars().all()
        count = len(items)
        for it in items:
            s.delete(it)
        # re-pack positions
        remaining = self.items(s, playlist_id)
        for idx, it in enumerate(remaining):
            if it.position != idx:
                it.position = idx
        s.flush()
        return count

    def remove_songs(self, s: Session, playlist_id: int, song_ids: Iterable[int]) -> int:
        items = s.execute(
            select(PlaylistItem).where(PlaylistItem.playlist_id == playlist_id, PlaylistItem.song_id.in_(list(song_ids)))
        ).scalars().all()
        count = len(items)
        for it in items:
            s.delete(it)
        remaining = self.items(s, playlist_id)
        for idx, it in enumerate(remaining):
            if it.position != idx:
                it.position = idx
        s.flush()
        return count
