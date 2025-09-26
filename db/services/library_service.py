from __future__ import annotations
import hashlib, mimetypes
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional, Iterable
from PIL import Image as PILImage
from sqlalchemy import select

from db.manager import DatabaseManager
from db.models import AlbumImage, Image
from db.repositories import FolderRepo, AlbumRepo, ImageRepo, AlbumImageRepo


@dataclass
class ChildRow:
    id: int
    name: str
    kind: str
    position: int


class LibraryService:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.folder_repo = FolderRepo()
        self.album_repo = AlbumRepo()
        self.image_repo = ImageRepo()
        self.album_img_repo = AlbumImageRepo()

    # ---------- Folders / Albums ----------
    # --- Getters
    def get_folder(self, f_id: int):
        with self.db.session() as s:
            return self.folder_repo.get(s, f_id)

    def get_album(self, a_id: int):
        with self.db.session() as s:
            return self.album_repo.get(s, a_id)

    def get_root_items(self):
        return self.get_children(None)

    def get_children(self, parent_id: Optional[int]):
        """Return merged, position-sorted (folders then albums) children."""
        with self.db.session() as s:
            items = self.folder_repo.children_flat(s, parent_id)
            rows = [ChildRow(kind=i[0], id=i[1].id, name=i[1].name, position=i[2]) for i in items]
            rows.sort(key=lambda r: (r.position, 0 if r.kind == "folder" else r.position, 1))
            return rows

    def breadcrumb(self, album_id: int) -> list[str]:
        """ Return ['root', 'Session 1', 'NPCs'] style breadcrumb. """
        with self.db.session() as s:
            names: list[str] = []
            cur = self.album_repo.get(s, album_id)
            while cur is not None:
                names.append(cur.name)
                cur = cur.parent
            names.reverse()
            return names

    # --- Create / Rename / Move
    def create_folder(self, parent_id: Optional[int], name: str, position: Optional[int] = None) -> int:
        with self.db.session() as s:
            pos = position if position is not None else self.folder_repo.next_child_position(s, parent_id)
            f = self.folder_repo.create(s, parent_id, name, pos)
            return f.id

    def create_album(self, parent_id: Optional[int], name: str, position: Optional[int] = None) -> int:
        with self.db.session() as s:
            pos = position if position is not None else self.folder_repo.next_child_position(s, parent_id)
            a = self.album_repo.create(s, parent_id, name, pos)
            return a.id

    def rename_folder(self, folder_id: int, new_name: str) -> None:
        with self.db.session() as s:
            f = self.folder_repo.get(s, folder_id)
            if not f:
                return
            f.name = new_name

    def rename_album(self, album_id: int, new_name: str) -> None:
        with self.db.session() as s:
            f = self.album_repo.get(s, album_id)
            if not f:
                return
            f.name = new_name

    def move_node(self, target_id: int, target_type: str, new_parent_id: int, position: Optional[int]):
        match target_type:
            case "folder":
                self.move_folder(target_id, new_parent_id, position)
            case "album":
                self.move_album(target_id, new_parent_id, position)
            case _:
                raise ValueError(f"Unknown target_type {target_type}")

    def move_folder(self, folder_id: int, new_parent_id: Optional[int], position: Optional[int]) -> None:
        with self.db.session() as s:
            f = self.folder_repo.get(s, folder_id)
            if not f:
                return
            self._move_entity(s, obj=f, new_parent_id=new_parent_id, position=position)

    def move_album(self, album_id: int, new_parent_id: Optional[int], position: Optional[int]) -> None:
        with self.db.session() as s:
            a = self.album_repo.get(s, album_id)
            if not a:
                return
            self._move_entity(s, obj=a, new_parent_id=new_parent_id, position=position)

    def _move_entity(self, s, obj, new_parent_id: Optional[int], position: Optional[int]) -> None:
        old_parent, old_pos = obj.parent_id, obj.position

        # Reorder within the same parent
        if new_parent_id == old_parent:
            # clamp to valid range [0, last_index]
            last_index = self.folder_repo.next_child_position(s, new_parent_id) - 1
            desired = position if position is not None else old_pos
            new_pos = max(0, min(desired, last_index if last_index >= 0 else 0))
            if new_pos != old_pos:
                self.folder_repo.reorder_within_parent(s, old_parent, old_pos, new_pos)
                obj.position = new_pos
            return

        # Moving across parents
        self.folder_repo.shift_down_after(s, old_parent, old_pos)  # close gap in old parent

        insert_pos = (
            position
            if position is not None
            else self.folder_repo.next_child_position(s, new_parent_id)
        )
        self.folder_repo.shift_up_from(s, new_parent_id, insert_pos)  # make room in new parent
        obj.parent_id = new_parent_id
        obj.position = insert_pos

    # --- Deletion
    def delete_folder(self, folder_id: int, hard: bool = False) -> None:
        with self.db.session() as s:
            f = self.folder_repo.get(s, folder_id)
            if not f:
                return
            if not hard:
                raise NotImplementedError("Soft delete isn't implemented yet, used hard delete")
            parent_id, old_pos = self.folder_repo.delete(s, folder_id)
            if old_pos is not None:
                self.folder_repo.shift_down_after(s, parent_id, old_pos)

    def delete_album(self, album_id: int, hard: bool = False) -> None:
        with self.db.session() as s:
            a = self.album_repo.get(s, album_id)
            if not a:
                return
            if not hard:
                raise NotImplementedError("Soft delete isn't implemented yet, used hard delete")
            parent_id, old_pos = self.album_repo.delete(s, album_id)
            if old_pos is not None:
                self.folder_repo.shift_down_after(s, parent_id, old_pos)

    # ---------- Images & Album links ----------
    # --- Create / Add
    def add_images_from_paths(self, album_id: int, paths: list[str | Path]) -> list[tuple[int, str, int]]:
        """
        Ingest images by path:
          - de-dupe by content hash (reuse existing Image rows),
          - create Image + ImageData for new content,
          - link (append) to the album,
          - return (image_id, caption, position) for each added/linked image.

        Uses repositories for all DB I/O.
        """
        results: list[tuple[int, str, int]] = []

        with self.db.session() as s:
            for p in paths:
                p_str = str(p)
                caption_from_path = Path(p_str).stem

                # Read raw bytes once; hash immediately.
                full_bytes = Path(p_str).read_bytes()
                sha = hashlib.sha256(full_bytes).hexdigest()

                # Reuse existing image by content hash
                existing = self.image_repo.find_by_sha256(s, sha)
                if existing is not None:
                    # Avoid duplicate association in the same album
                    if not self.album_img_repo.is_linked(s, album_id, existing.id):
                        lnk = self.album_img_repo.link(s, album_id, existing.id, position=None)
                        results.append((existing.id, existing.caption or caption_from_path, lnk.position))
                    continue

                # New image → decode once to get dims and make thumbnail
                with PILImage.open(p_str) as im:
                    w, h = im.size
                    fmt = (im.format or "PNG").upper()

                    im_copy = im.copy()
                    im_copy.thumbnail((256, 256))
                    buf = BytesIO()
                    im_copy.save(buf, format="PNG")
                    thumb_bytes = buf.getvalue()
                    thumb_fmt = "PNG"

                mime = mimetypes.guess_type(p_str)[0] or f"image/{fmt.lower()}"

                img = self.image_repo.create(
                    s,
                    caption=caption_from_path,
                    mime=mime,
                    width=w,
                    height=h,
                    sha256=sha,
                    full_bytes=full_bytes,
                    thumb_bytes=thumb_bytes,
                    fmt=fmt,
                    thumb_fmt=thumb_fmt,
                )

                lnk = self.album_img_repo.link(s, album_id, img.id, position=None)
                results.append((img.id, caption_from_path, lnk.position))

        return results

    # --- Getters
    def get_image(self, image_id: int):
        with self.db.session() as s:
            return self.image_repo.get(s, image_id)

    def get_album_images(self, album_id: int) -> list[tuple[int, str, int]]:
        """Return (image_id, path, position)."""
        with self.db.session() as s:
            ids = self.album_repo.image_ids_in_order(s, album_id)
            out = []
            for pos, iid in enumerate(ids):
                img = s.get(Image, iid)
                if img:
                    out.append((img.id, img.caption, pos))
            return out

    def get_image_thumb_bytes(self, image_id: int) -> Optional[bytes]:
        """Return the stored thumbnail bytes for an image; lazily synthesize from full bytes if missing."""
        with self.db.session() as s:
            row = self.image_repo.get(s, image_id).data
            if row is None:
                return None
            if row.thumb_bytes:
                return row.thumb_bytes
            # Fallback: build a small PNG thumb from full bytes (stored back for next time)
            if row.bytes:
                from io import BytesIO
                with PILImage.open(BytesIO(row.bytes)) as im:
                    im = im.copy()
                    im.thumbnail((256, 256))
                    buf = BytesIO()
                    im.save(buf, format="PNG")
                    tb = buf.getvalue()
                row.thumb_bytes = tb
                return tb
            return None

    def get_image_full_bytes(self, image_id: int) -> Optional[bytes]:
        """Return original bytes if present."""
        with self.db.session() as s:
            return self.image_repo.get(s, image_id).data.bytes

    # --- Rename / Move
    def rename_image(self, image_id: int, new_name: str) -> None:
        with self.db.session() as s:
            c = self.image_repo.get(s, image_id)
            if not c:
                return
            c.caption = new_name

    def reorder_album_images(self, album_id: int, image_ids_in_order: list[int]) -> None:
        """Set an album's image order to image_ids_in_order."""
        with self.db.session() as s:
            links = self.album_img_repo.links_for_album(s, album_id)
            by_img = {l.image_id: l for l in links}
            for pos, iid in enumerate(image_ids_in_order):
                if iid in by_img:
                    by_img[iid].position = pos
            # Keep any stragglers (not present in the passed list) after the end, position-stable
            tail = [l for l in links if l.image_id not in by_img or l.image_id not in set(image_ids_in_order)]
            base = len(image_ids_in_order)
            for i, l in enumerate(sorted(tail, key=lambda x: x.position)):
                l.position = base + i
            self.album_repo.reset_image_positions(s, album_id)

    def delete_image_from_album(self, album_id: int, image_id: int, *, delete_orphan_image: bool = True) -> None:
        with self.db.session() as s:
            self.album_img_repo.unlink(s, album_id, image_id)
            self.album_repo.reset_image_positions(s, album_id)
            if delete_orphan_image:
                still = s.execute(
                    select(AlbumImage).where(AlbumImage.image_id == image_id)
                ).first()
                if not still:
                    self.image_repo.delete(s, image_id)
