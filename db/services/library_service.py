from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Sequence, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from db.manager import DatabaseManager
from db.models import Folder, Album, Image, ImageData, AlbumImage

Kind = Literal["folder", "collection"]


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
    def get_root_folders(self) -> list[Folder]:
        with self.db.session() as s:
            return s.execute(select(Folder).where(Folder.parent_id.is_(None))
                             .order_by(Folder.position)).scalars().all()

    def get_folder_children(self, folder_id: int) -> list[ChildRow]:
        """Merge subfolders and subcollections in display order."""
        with self.db.session() as s:
            f = s.get(Folder, folder_id)
            if not f:
                return []
            # thanks to order_by on relationships, these come sorted by position
            subfolders = [ChildRow("folder", sf.id, sf.name, sf.position) for sf in f.subfolders]
            subcols = [ChildRow("collection", c.id, c.name, c.position) for c in f.albums]
            items = subfolders + subcols
            items.sort(key=lambda t: (t.position, 0 if t.kind == "folder" else 1, t.id))
            return items

    def get_album_images(self, collection_id: int) -> list[tuple[int, str, int]]:
        """Return [(image_id, caption, position)] in UI order."""
        with self.db.session() as s:
            c = s.get(Album, collection_id)
            if not c:
                return []
            return [(ci.image_id, ci.image.caption or "", ci.position) for ci in c.album_images]

    def breadcrumb(self, folder_id: int) -> list[str]:
        """Return ['root', 'Session 1', 'NPCs'] style breadcrumb."""
        with self.db.session() as s:
            names: list[str] = []
            cur = s.get(Folder, folder_id)
            while cur is not None:
                names.append(cur.name)
                cur = cur.parent
            names.reverse()
            return names

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
    def create_folder(self, parent_id: Optional[int], name: str) -> int:
        with self.db.session() as s:
            pos = self._next_folder_position(s, parent_id)
            f = Folder(parent_id=parent_id, name=name, position=pos)
            s.add(f)
            s.flush()
            return f.id

    def create_album(self, folder_id: int, name: str) -> int:
        with self.db.session() as s:
            pos = self._next_collection_position(s, folder_id)
            c = Album(folder_id=folder_id, name=name, position=pos)
            s.add(c)
            s.flush()
            return c.id

    def create_image_and_add(
            self,
            collection_id: int,
            *,
            caption: str | None,
            full_bytes: bytes,
            mime_type: str = "image/png",
            width_px: int | None = None,
            height_px: int | None = None,
            thumb_bytes: bytes | None = None,
            bytes_format: str | None = None,
            thumb_format: str | None = None,
    ) -> int:
        with self.db.session() as s:
            img = Image(
                caption=caption,
                mime_type=mime_type,
                width_px=width_px,
                height_px=height_px,
                bytes_size=len(full_bytes),
                has_data=1,
            )
            s.add(img)
            s.flush()  # get img.id

            s.add(ImageData(
                image_id=img.id,
                bytes=full_bytes,
                thumb_bytes=thumb_bytes,
                bytes_format=bytes_format,
                thumb_format=thumb_format,
            ))

            pos = self._next_collection_image_position(s, collection_id)
            s.add(AlbumImage(collection_id=collection_id, image_id=img.id, position=pos))
            return img.id

    # ---------- Update / Move / Reorder ----------
    def rename_folder(self, folder_id: int, new_name: str) -> None:
        with self.db.session() as s:
            f = s.get(Folder, folder_id)
            if not f:
                return
            f.name = new_name

    def rename_album(self, collection_id: int, new_name: str) -> None:
        with self.db.session() as s:
            c = s.get(Album, collection_id)
            if not c:
                return
            c.name = new_name

    def move_folder(self, folder_id: int, new_parent_id: Optional[int]) -> None:
        with self.db.session() as s:
            f = s.get(Folder, folder_id)
            if not f:
                return
            f.parent_id = new_parent_id
            f.position = self._next_folder_position(s, new_parent_id)

    def move_collection(self, collection_id: int, new_folder_id: int) -> None:
        with self.db.session() as s:
            c = s.get(Album, collection_id)
            if not c:
                return
            c.folder_id = new_folder_id
            c.position = self._next_collection_position(s, new_folder_id)

    def reorder_collection_images(self, collection_id: int, ordered_image_ids: Sequence[int]) -> None:
        with self.db.session() as s:
            rows = s.execute(select(AlbumImage)
                             .where(AlbumImage.album_id == collection_id)).scalars().all()
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

    def delete_album(self, collection_id: int, hard: bool = False) -> None:
        with self.db.session() as s:
            c = s.get(Album, collection_id)
            if not c:
                return
            if hard:
                s.delete(c)
            else:
                c.is_deleted = 1

    # ---------- internals ----------
    def _next_folder_position(self, s: Session, parent_id: Optional[int]) -> int:
        q = select(func.coalesce(func.max(Folder.position), -1)).where(Folder.parent_id == parent_id)
        return s.execute(q).scalar_one() + 1

    def _next_collection_position(self, s: Session, folder_id: int) -> int:
        q = select(func.coalesce(func.max(Album.position), -1)).where(Album.folder_id == folder_id)
        return s.execute(q).scalar_one() + 1

    def _next_collection_image_position(self, s: Session, collection_id: int) -> int:
        q = select(func.coalesce(func.max(AlbumImage.position), -1)).where(
            AlbumImage.album_id == collection_id
        )
        return s.execute(q).scalar_one() + 1
