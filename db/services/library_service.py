from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence, Optional, Iterable
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from PIL import Image as PILImage

from db.manager import DatabaseManager
from db.models import Folder, Album, Image, ImageData, AlbumImage

Kind = Literal["folder", "album"]


@dataclass(frozen=True)
class ChildRow:
    kind: Kind
    id: int
    name: str
    position: int


class LibraryService:
    """High-level DB operations for the UI tabs."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    # ---------- Read ----------
    def get_root_items(self) -> list[ChildRow]:
        """Return all items with no parent (folders & albums), sorted by position; folders before albums on ties."""
        return self.get_folder_children(None)

    def get_folder_children(self, folder_id: int) -> list[ChildRow]:
        """ Get the children from a folder id. """
        with self.db.session() as s:
            folders = s.execute(
                select(Folder).where(Folder.parent_id.is_(folder_id))
            ).scalars().all()
            albums = s.execute(
                select(Album).where(Album.parent_id.is_(folder_id))
            ).scalars().all()

        rows: list[ChildRow] = [
                                   ChildRow(kind="folder", id=f.id, name=f.name, position=f.position) for f in folders
                               ] + [
                                   ChildRow(kind="album", id=a.id, name=a.name, position=a.position) for a in albums
                               ]

        # Folders before albums on ties; id as stable tiebreaker
        rows.sort(key=lambda r: (r.position, 0 if r.kind == "folder" else 1, r.id))
        return rows

    def get_album_images(self, album_id: int) -> list[tuple[int, str, int]]:
        """Return [(image_id, caption, position)] in UI order."""
        with self.db.session() as s:
            c = s.get(Album, album_id)
            if not c:
                return []
            return [(ci.image_id, ci.image.caption or "", ci.position) for ci in c.album_images]

    def breadcrumb(self, album_id: int) -> list[str]:
        """ Return ['root', 'Session 1', 'NPCs'] style breadcrumb. """
        with self.db.session() as s:
            names: list[str] = []
            cur = s.get(Album, album_id)
            while cur is not None:
                names.append(cur.name)
                cur = cur.parent
            names.reverse()
            return names

    def get_folder(self, folder_id: int):
        with self.db.session() as s:
            return s.get(Folder, folder_id)

    def get_album(self, album_id: int):
        with self.db.session() as s:
            return s.get(Album, album_id)

    # ---------- Check -----------
    def is_folder(self, folder_id: int):
        """ Returns if folder exists """
        with self.db.session() as s:
            return s.get(Folder, folder_id)

    def is_album(self, album_id: int):
        """ Returns if folder exists """
        with self.db.session() as s:
            return s.get(Album, album_id)

    # ---------- Create ----------
    def create_folder(self, parent_id: Optional[int], name: str, position: int = None) -> int:
        with self.db.session() as s:
            pos = position if position is not None else self._next_folder_position(s, parent_id)
            f = Folder(parent_id=parent_id, name=name, position=pos)
            s.add(f)
            s.flush()
        return f.id

    def create_album(self, parent_id: int, name: str, position: int = None) -> int:
        with self.db.session() as s:
            pos = position if position is not None else self._next_album_position(s, parent_id)
            c = Album(parent_id=parent_id, name=name, position=pos)
            s.add(c)
            s.flush()
        return c.id

    def _guess_mime(self, path: str, fallback: Optional[str] = None) -> str:
        mime, _ = mimetypes.guess_type(path)
        return mime or fallback or "application/octet-stream"

    def _read_image_and_thumb(self, path: str, thumb_px: int = 256):
        """ Read the image and get the raw data and metadata we need for the DB

        Parameters
        ----------
        path : str
            The filesystem path of the new image
        thumb_px: int, default 256
            The maximal size of the thumbnail.

        Returns
        -------
        full_bytes : bytearray
            The raw bytes of the image
        w, h : int, int
            The width and height of the image in pixels
        fmt : str
            The format of the image
        thumb_bytes : bytearray
            The raw bytes of the thumbnail of the image
        fmt_thumb : str, "PNG"
            The format of the thumbnail
        """
        with PILImage.open(path) as im:
            w, h = im.size
            fmt = (im.format or "PNG").upper()
            # full bytes
            with open(path, "rb") as f:
                full_bytes = f.read()
            # thumb bytes
            im_copy = im.copy()
            im_copy.thumbnail((thumb_px, thumb_px))
            from io import BytesIO
            buf = BytesIO()
            im_copy.save(buf, format="PNG")  # store thumbs as PNG (simple & lossless)
            thumb_bytes = buf.getvalue()
        return full_bytes, w, h, fmt, thumb_bytes, "PNG"

    def add_images_from_paths(self, album_id: int, paths: Iterable[str]) -> list:
        """Atomic, batched ingest of images into one album.
        Gets the position to insert the image to, then creates the DB items and adds them for each image.

        Parameters
        ----------
        album_id : int
            The DB id of the album
        paths : list of str
            The filesystem paths of the images to add.

        Returns
        -------
        results : list
            A list of (image_id, caption, album_position)
        """
        results = []
        with self.db.session() as s:
            # prefetch next position once and increment locally for speed
            base_pos = self._next_album_image_position(s, album_id)
            next_pos = base_pos
            for p in paths:
                p_str = str(p)
                caption = Path(p_str).stem
                full_bytes, w, h, fmt, thumb_bytes, thumb_fmt = self._read_image_and_thumb(p_str)
                mime = self._guess_mime(p_str, f"image/{fmt.lower()}")

                img = Image(
                    caption=caption, mime_type=mime, width_px=w, height_px=h,
                    bytes_size=len(full_bytes), has_data=1,
                )
                s.add(img)
                s.flush()

                s.add(ImageData(
                    image_id=img.id,
                    bytes=full_bytes,
                    thumb_bytes=thumb_bytes,
                    bytes_format=fmt,
                    thumb_format=thumb_fmt,
                ))

                s.add(AlbumImage(album_id=album_id, image_id=img.id, position=next_pos))
                results.append((img.id, caption, next_pos))
                next_pos += 1
        return results

    # ---------- Update / Move / Reorder ----------
    def rename_folder(self, folder_id: int, new_name: str) -> None:
        with self.db.session() as s:
            f = s.get(Folder, folder_id)
            if not f:
                return
            f.name = new_name

    def rename_album(self, album_id: int, new_name: str) -> None:
        with self.db.session() as s:
            c = s.get(Album, album_id)
            if not c:
                return
            c.name = new_name

    def move_folder(self, folder_id: int, new_parent_id: Optional[int], position: Optional[int]) -> None:
        with self.db.session() as s:
            f = s.get(Folder, folder_id)
            if not f:
                return
            f.parent_id = new_parent_id
            f.position = position if position is not None else self._next_folder_position(s, new_parent_id)

    def move_album(self, album_id: int, new_parent_id: Optional[int], position: Optional[int]) -> None:
        with self.db.session() as s:
            c = s.get(Album, album_id)
            if not c:
                return
            c.parent_id = new_parent_id
            c.position = position if position is not None else self._next_album_position(s, new_parent_id)

    def reorder_album_images(self, album_id: int, ordered_image_ids: Sequence[int]) -> None:
        with self.db.session() as s:
            rows = s.execute(select(AlbumImage)
                             .where(AlbumImage.album_id == album_id)).scalars().all()
            by_img = {r.image_id: r for r in rows}
            for idx, img_id in enumerate(ordered_image_ids):
                if img_id in by_img:
                    by_img[img_id].position = idx

    # ---------- Delete (soft by default) ----------
    def delete_folder(self, folder_id: int, hard: bool = False) -> None:
        with self.db.session() as s:
            f = s.get(Folder, folder_id)
            if not f:
                return
            if hard:
                s.delete(f)
            else:
                f.is_deleted = 1
            s.flush()

    def delete_album(self, album_id: int, hard: bool = False) -> None:
        with self.db.session() as s:
            c = s.get(Album, album_id)
            if not c:
                return
            if hard:
                s.delete(c)
            else:
                c.is_deleted = 1
            s.flush()

    # ---------- internals ----------
    def _next_folder_position(self, s: Session, parent_id: Optional[int]) -> int:
        q = select(func.coalesce(func.max(Folder.position), -1)).where(Folder.parent_id == parent_id)
        return s.execute(q).scalar_one() + 1

    def _next_album_position(self, s: Session, folder_id: int) -> int:
        q = select(func.coalesce(func.max(Album.position), -1)).where(Album.parent_id == folder_id)
        return s.execute(q).scalar_one() + 1

    def _next_album_image_position(self, s: Session, album_id: int) -> int:
        q = select(func.coalesce(func.max(AlbumImage.position), -1)).where(
            AlbumImage.album_id == album_id
        )
        return s.execute(q).scalar_one() + 1
