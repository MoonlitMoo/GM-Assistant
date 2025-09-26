from __future__ import annotations
from typing import Optional, Tuple
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from db.models import Album, AlbumImage, Folder


class AlbumRepo:
    def get(self, s: Session, album_id: int) -> Album | None:
        return s.get(Album, album_id)

    def create(self, s: Session, parent_id: Optional[int], name: str, position: int) -> Album:
        a = Album(parent_id=parent_id, name=name, position=position)
        s.add(a)
        s.flush()
        return a

    def delete(self, s: Session, album_id: int) -> Tuple[int, int]:
        a = s.get(Album, album_id)
        if a:
            ret = a.parent_id, a.position
            s.delete(a)
            return ret
        return None, None

    def image_ids_in_order(self, s: Session, album_id: int) -> list[int]:
        rows = s.execute(
            select(AlbumImage.image_id).where(AlbumImage.album_id == album_id).order_by(AlbumImage.position)
        ).scalars().all()
        return list(rows)

    def reset_image_positions(self, s: Session, album_id: int) -> None:
        links = s.execute(
            select(AlbumImage).where(AlbumImage.album_id == album_id).order_by(AlbumImage.position)
        ).scalars().all()
        for i, l in enumerate(links): l.position = i
