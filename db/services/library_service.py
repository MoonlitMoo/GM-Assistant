from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence, Optional, Iterable
from sqlalchemy import select, func, update, union_all, delete
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
            pos = position if position is not None else self._next_child_position(s, parent_id)
            f = Folder(parent_id=parent_id, name=name, position=pos)
            s.add(f)
            s.flush()
        return f.id

    def create_album(self, parent_id: int, name: str, position: int = None) -> int:
        with self.db.session() as s:
            pos = position if position is not None else self._next_child_position(s, parent_id)
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
        w : int
            The width of the image in pixels
        h : int
            The height of the image in pixels
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

    def move_node(self, target_id: int, target_type: str, new_parent_id: int, position: Optional[int]) -> None:
        """ We shift the target to the new parent and set the position.
        Also updates position of new siblings, shifting old siblings down, new siblings up.

        Parameters
        ----------
        target_id : int
            The node (Folder/Album) to move
        target_type : str
            What type of object to move
        new_parent_id : int
            The new parent target
        position : int, optional
            The position to insert at.
        """
        with self.db.session() as s:
            match target_type:
                case "folder":
                    f = s.get(Folder, target_id)
                case "album":
                    f = s.get(Album, target_id)
                case _:
                    raise ValueError(f"Unknown target_type {target_type}")

            if not f:
                return

            old_parent, old_pos = f.parent_id, f.position

            # Reorder within the same parent
            if new_parent_id == old_parent:
                # clamp to valid range [0, child_count-1]
                max_pos = self._next_child_position(s, new_parent_id)
                new_pos = max(0, min(position if position is not None else old_pos, max_pos))
                if new_pos != old_pos:
                    self._reorder_within_parent(s, old_parent, old_pos, new_pos)
                    f.position = new_pos
                return

            self._shift_down_after(s, old_parent, old_pos)
            insert_pos = position if position is not None else self._next_child_position(s, new_parent_id)
            self._shift_up_from(s, new_parent_id, insert_pos)
            f.parent_id = new_parent_id
            f.position = insert_pos

    def move_image(self, image_id: int, new_album_id: int, position: Optional[int] = None) -> None:
        """Move one image to a new album (or reorder within the same album), preserving sibling positions.
        Same as move_node but shifted since images stored differently.

        Parameters
        ----------
        image_id : int
            The image to shift
        new_album_id : int
            Destination album
        position : int
            Position in album to put.
        """
        with self.db.session() as s:
            # fetch the association row; image belongs to exactly one album via AlbumImage
            ai = s.execute(
                select(AlbumImage).where(AlbumImage.image_id == image_id)
            ).scalar_one_or_none()
            if ai is None:
                return

            old_album_id = ai.album_id
            old_pos = ai.position

            # normalize target position bounds using current counts
            def _album_size(album_id: int) -> int:
                q = select(func.count()).select_from(AlbumImage).where(AlbumImage.album_id == album_id)
                return s.execute(q).scalar_one()

            if new_album_id == old_album_id:
                # Reorder within same album
                size = _album_size(old_album_id)
                max_pos = max(0, size - 1)
                new_pos = old_pos if position is None else max(0, min(position, max_pos))
                if new_pos != old_pos:
                    self._ai_reorder_within_album(s, old_album_id, old_pos, new_pos)
                    ai.position = new_pos
                return

            self._ai_shift_down_after(s, old_album_id, old_pos)
            size_dest = _album_size(new_album_id)
            insert_pos = size_dest if position is None else max(0, min(position, size_dest))
            self._ai_shift_up_from(s, new_album_id, insert_pos)
            ai.album_id = new_album_id
            ai.position = insert_pos

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
            old_parent, old_pos = f.parent_id, f.position
            if hard:
                s.delete(f)
                s.flush()
                self._shift_down_after(s, old_parent, old_pos)
            else:
                f.is_deleted = 1

    def delete_album(self, album_id: int, hard: bool = False) -> None:
        with self.db.session() as s:
            c = s.get(Album, album_id)
            if not c:
                return
            old_parent, old_pos = c.parent_id, c.position
            if hard:
                s.delete(c)
                s.flush()
                self._shift_down_after(s, old_parent, old_pos)
            else:
                c.is_deleted = 1

    # ---------- internals ----------
    def _next_child_position(self, s: Session, parent_id: int) -> int:
        """ Gets position for a new child item in a folder. """
        folder_q = select(Folder.id).where(Folder.parent_id == parent_id)
        album_q = select(Album.id).where(Album.parent_id == parent_id)
        union_q = union_all(folder_q, album_q).subquery()
        return s.execute(select(func.count()).select_from(union_q)).scalar_one()

    def _shift_up_from(self, s: Session, parent_id: Optional[int], from_pos: int) -> None:
        """Make room at from_pos: positions >= from_pos -> +1 (folders + albums)."""
        s.execute(update(Folder).where(Folder.parent_id == parent_id, Folder.position >= from_pos)
                  .values(position=Folder.position + 1))
        s.execute(update(Album).where(Album.parent_id == parent_id, Album.position >= from_pos)
                  .values(position=Album.position + 1))

    def _shift_down_after(self, s: Session, parent_id: Optional[int], from_pos: int) -> None:
        """Close gap after from_pos: positions > from_pos -> -1 (folders + albums)."""
        s.execute(update(Folder).where(Folder.parent_id == parent_id, Folder.position > from_pos)
                  .values(position=Folder.position - 1))
        s.execute(update(Album).where(Album.parent_id == parent_id, Album.position > from_pos)
                  .values(position=Album.position - 1))

    def _reorder_within_parent(self, s: Session, parent_id: Optional[int], old_pos: int, new_pos: int) -> None:
        """Shift a contiguous block within the same parent to move one item from old_pos -> new_pos."""
        if new_pos == old_pos:
            return
        if new_pos > old_pos:
            # moving down: items in (old_pos, new_pos] shift up (-1)
            s.execute(update(Folder).where(Folder.parent_id == parent_id,
                                           Folder.position > old_pos, Folder.position <= new_pos)
                      .values(position=Folder.position - 1))
            s.execute(update(Album).where(Album.parent_id == parent_id,
                                          Album.position > old_pos, Album.position <= new_pos)
                      .values(position=Album.position - 1))
        else:
            # moving up: items in [new_pos, old_pos) shift down (+1)
            s.execute(update(Folder).where(Folder.parent_id == parent_id,
                                           Folder.position >= new_pos, Folder.position < old_pos)
                      .values(position=Folder.position + 1))
            s.execute(update(Album).where(Album.parent_id == parent_id,
                                          Album.position >= new_pos, Album.position < old_pos)
                      .values(position=Album.position + 1))

    def _ai_shift_up_from(self, s: Session, album_id: int, from_pos: int) -> None:
        """Make room starting at from_pos in AlbumImage: positions >= from_pos → +1."""
        s.execute(
            update(AlbumImage)
            .where(AlbumImage.album_id == album_id, AlbumImage.position >= from_pos)
            .values(position=AlbumImage.position + 1)
        )

    def _ai_shift_down_after(self, s: Session, album_id: int, from_pos: int) -> None:
        """Close gap after from_pos in AlbumImage: positions > from_pos → -1."""
        s.execute(
            update(AlbumImage)
            .where(AlbumImage.album_id == album_id, AlbumImage.position > from_pos)
            .values(position=AlbumImage.position - 1)
        )

    def _ai_reorder_within_album(self, s: Session, album_id: int, old_pos: int, new_pos: int) -> None:
        """Shift a contiguous block within the same album to move one item old_pos → new_pos."""
        if new_pos == old_pos:
            return
        if new_pos > old_pos:
            # moving down: items in (old_pos, new_pos] shift up (-1)
            s.execute(
                update(AlbumImage)
                .where(AlbumImage.album_id == album_id,
                       AlbumImage.position > old_pos,
                       AlbumImage.position <= new_pos)
                .values(position=AlbumImage.position - 1)
            )
        else:
            # moving up: items in [new_pos, old_pos) shift down (+1)
            s.execute(
                update(AlbumImage)
                .where(AlbumImage.album_id == album_id,
                       AlbumImage.position >= new_pos,
                       AlbumImage.position < old_pos)
                .values(position=AlbumImage.position + 1)
            )
    def _next_album_image_position(self, s: Session, album_id: int) -> int:
        q = select(func.coalesce(func.max(AlbumImage.position), -1)).where(
            AlbumImage.album_id == album_id
        )
        return s.execute(q).scalar_one() + 1

    # -------- ImageTab --------
    # ---- Thumbnails / Image bytes helpers ----
    from sqlalchemy import select, delete
    from sqlalchemy.orm import joinedload
    from typing import Iterable, Optional

    THUMB_PX = 256

    def get_image_thumb_bytes(self, image_id: int) -> Optional[bytes]:
        """Return the stored thumbnail bytes for an image; lazily synthesize from full bytes if missing."""
        with self.db.session() as s:
            row = s.execute(
                select(ImageData)
                .where(ImageData.image_id == image_id)
            ).scalar_one_or_none()
            if row is None:
                return None
            if row.thumb_bytes:
                return row.thumb_bytes
            # Fallback: build a small PNG thumb from full bytes (stored back for next time)
            if row.bytes:
                from io import BytesIO
                with PILImage.open(BytesIO(row.bytes)) as im:
                    im = im.copy()
                    im.thumbnail((THUMB_PX, THUMB_PX))
                    buf = BytesIO()
                    im.save(buf, format="PNG")
                    tb = buf.getvalue()
                row.thumb_bytes = tb
                return tb
            return None

    def get_image_full_bytes(self, image_id: int) -> Optional[bytes]:
        """Return original bytes if present."""
        with self.db.session() as s:
            row = s.execute(
                select(ImageData.bytes)
                .where(ImageData.image_id == image_id)
            ).scalar_one_or_none()
            return row

    def set_image_caption(self, image_id: int, caption: str) -> None:
        with self.db.session() as s:
            img = s.get(Image, image_id)
            if not img:
                return
            img.caption = caption

    def remove_images_from_album(self, album_id: int, image_ids: Iterable[int]) -> None:
        """Remove specific images from an album (doesn’t delete the images globally)."""
        with self.db.session() as s:
            s.execute(
                delete(AlbumImage)
                .where(AlbumImage.album_id == album_id, AlbumImage.image_id.in_(list(image_ids)))
            )
            # re-pack positions to 0..N-1
            rows = s.execute(
                select(AlbumImage).where(AlbumImage.album_id == album_id)
            ).scalars().all()
            rows.sort(key=lambda r: r.position)
            for i, r in enumerate(rows):
                r.position = i
