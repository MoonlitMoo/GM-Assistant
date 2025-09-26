from __future__ import annotations
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from db.models import Image, ImageData, AlbumImage


class ImageRepo:
    def get(self, s: Session, image_id: int) -> Image | None:
        return s.get(Image, image_id)

    def create(self, s: Session, *, caption: str, mime: str, width: int, height: int, sha256: str,
               full_bytes: bytes, thumb_bytes: bytes, fmt, thumb_fmt) -> Image:
        img = Image(caption=caption, mime_type=mime, width_px=width, height_px=height,
            bytes_size=len(full_bytes), has_data=1, hash_sha256=sha256)
        s.add(img)
        s.flush()
        s.add(ImageData(image_id=img.id, bytes=full_bytes, thumb_bytes=thumb_bytes, bytes_format=fmt,
                        thumb_format=thumb_fmt))
        s.flush()
        return img

    def delete(self, s: Session, image_id: int) -> None:
        img = s.get(Image, image_id)
        if img: s.delete(img)

    def find_by_sha256(self, s: Session, sha256: str) -> Image | None:
        return s.execute(select(Image).where(Image.hash_sha256 == sha256)).scalar_one_or_none()


class AlbumImageRepo:
    def link(self, s: Session, album_id: int, image_id: int, position: int | None = None) -> AlbumImage:
        if position is None:
            max_pos = s.execute(
                select(AlbumImage.position).where(AlbumImage.album_id == album_id).order_by(AlbumImage.position.desc())
            ).scalars().first()
            position = (max_pos if max_pos is not None else -1) + 1
        l = AlbumImage(album_id=album_id, image_id=image_id, position=position)
        s.add(l);
        s.flush()
        return l

    def unlink(self, s: Session, album_id: int, image_id: int) -> None:
        row = s.execute(select(AlbumImage).where(
            AlbumImage.album_id == album_id, AlbumImage.image_id == image_id
        )).scalar_one_or_none()
        if row: s.delete(row)

    def is_linked(self, s, album_id: int, image_id: int) -> bool:
        return s.execute(
            select(AlbumImage).where(AlbumImage.album_id == album_id, AlbumImage.image_id == image_id)
        ).first() is not None

    def links_for_album(self, s: Session, album_id: int) -> list[AlbumImage]:
        return s.execute(select(AlbumImage).where(AlbumImage.album_id == album_id)).scalars().all()

    def delete_all_for_album(self, s: Session, album_id: int) -> None:
        s.execute(delete(AlbumImage).where(AlbumImage.album_id == album_id))
