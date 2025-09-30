from __future__ import annotations
from typing import Iterable
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dmt.db.manager import DatabaseManager
from dmt.db.models import Tag
from dmt.db.repositories import TagRepo, ImageTagRepo

# Domain errors
class TagNotFound(Exception): ...
class TagNameConflict(Exception): ...

class TaggingService:
    """Business logic for Tag catalogue and Image↔Tag associations."""
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.tag_repo = TagRepo()
        self.image_tag_repo = ImageTagRepo()

    # ---------- Tag catalogue ----------
    def list_tags(self, query: str | None = None, limit: int = 50, offset: int = 0) -> list[Tag]:
        with self.db.session() as s:
            return self.tag_repo.list(s, query=query, limit=limit, offset=offset)

    def get_tag_by_name(self, name: str) -> Tag | None:
        with self.db.session() as s:
            return self.tag_repo.get_by_name(s, name)

    def create_tag(self, name: str, *, color_hex: str | None = None, kind: str | None = None) -> Tag:
        nm = name.strip()
        if not nm:
            raise ValueError("Tag name must not be empty")
        with self.db.session() as s:
            existing = self.tag_repo.get_by_name(s, nm)
            if existing:
                return existing
            try:
                return self.tag_repo.create(s, nm, color_hex=color_hex, kind=kind)
            except IntegrityError as e:
                # race with another create; surface as conflict
                raise TagNameConflict(str(e)) from e

    def update_tag(self, name_or_id: str | int, *, new_name: str | None = None,
                   color_hex: str | None = None, kind: str | None = None) -> Tag:
        with self.db.session() as s:
            tag = self._resolve_tag(s, name_or_id)
            if new_name is not None:
                nm = new_name.strip()
                if not nm:
                    raise ValueError("Tag name must not be empty")
                other = self.tag_repo.get_by_name(s, nm)
                if other and other.id != tag.id:
                    raise TagNameConflict(f"'{nm}' already exists")
                self.tag_repo.rename(s, tag, nm)
            if color_hex is not None:
                self.tag_repo.recolor(s, tag, color_hex)
            if kind is not None:
                self.tag_repo.retype(s, tag, kind)
            return tag

    def delete_tag(self, name_or_id: str | int, *, force: bool = False) -> bool:
        """Delete a tag. If force=False and tag is in use, return False."""
        from dmt.db.models import ImageTagLink
        with self.db.session() as s:
            tag = self._resolve_tag(s, name_or_id)
            in_use = s.query(ImageTagLink.id).filter(ImageTagLink.tag_id == tag.id).first() is not None
            if in_use and not force:
                return False
            if force:
                s.query(ImageTagLink).filter(ImageTagLink.tag_id == tag.id).delete(synchronize_session=False)
            self.tag_repo.delete(s, tag)
            return True

    def cleanup_unused_tags(self) -> int:
        """Remove tags that are not linked to any image. Returns count deleted."""
        with self.db.session() as s:
            return self.tag_repo.delete_unused_for_images(s)

    def tag_usage_map_for_images(self) -> dict[int, int]:
        with self.db.session() as s:
            pairs = self.tag_repo.usage_counts(s, limit=1_000_000)
            return {t.id: cnt for (t, cnt) in pairs}

    # ---------- Image associations ----------
    def get_tags_for_image(self, image_id: int) -> list[Tag]:
        with self.db.session() as s:
            return self.image_tag_repo.get_tags_for_image(s, image_id)

    def get_tags_for_images(self, image_ids: list[int]) -> dict[int, list[Tag]]:
        with self.db.session() as s:
            return self.image_tag_repo.tags_for_images(s, image_ids)

    def add_tags_to_image(self, image_id: int, names: Iterable[str]) -> list[Tag]:
        names_norm = [n.strip() for n in names if n and n.strip()]
        if not names_norm:
            return []
        created_or_found: list[Tag] = []
        with self.db.session() as s:
            for name in names_norm:
                tag = self.tag_repo.get_by_name(s, name)
                if not tag:
                    try:
                        tag = self.tag_repo.create(s, name)
                    except IntegrityError:
                        # race: someone else created it; get it now
                        tag = self.tag_repo.get_by_name(s, name)  # now must exist
                # idempotent link: rely on UNIQUE(image_id, tag_id)
                try:
                    self.image_tag_repo.add_link(s, image_id, tag.id)
                except IntegrityError:
                    s.rollback()  # rollback failed insert only; link already exists
                created_or_found.append(tag)
            return sorted(created_or_found, key=lambda t: t.name.lower())

    def remove_tags_from_image(self, image_id: int, names: Iterable[str]) -> None:
        names_norm = [n.strip() for n in names if n and n.strip()]
        if not names_norm:
            return
        with self.db.session() as s:
            for name in names_norm:
                tag = self.tag_repo.get_by_name(s, name)
                if tag:
                    self.image_tag_repo.remove_link(s, image_id, tag.id)

    def set_tags_for_image(self, image_id: int, names: Iterable[str]) -> list[Tag]:
        names_norm = [n.strip() for n in names if n and n.strip()]
        with self.db.session() as s:
            wanted: list[Tag] = []
            for name in names_norm:
                tag = self.tag_repo.get_by_name(s, name)
                if not tag:
                    try:
                        tag = self.tag_repo.create(s, name)
                    except IntegrityError:
                        tag = self.tag_repo.get_by_name(s, name)
                wanted.append(tag)
            self.image_tag_repo.replace_links(s, image_id, {t.id for t in wanted})
            return sorted(wanted, key=lambda t: t.name.lower())

    def suggest_tags_for_image(self, image_id: int, limit: int = 10) -> list[Tag]:
        """Simple heuristic: most-used globally, excluding already-linked."""
        with self.db.session() as s:
            have = {t.id for t in self.image_tag_repo.get_tags_for_image(s, image_id)}
            ranked = self.tag_repo.usage_counts(s, limit=limit * 2)
            out = [t for (t, _) in ranked if t.id not in have]
            return out[:limit]

    # ---------- helpers ----------
    def _resolve_tag(self, s: Session, name_or_id: str | int) -> Tag:
        if isinstance(name_or_id, int):
            t = self.tag_repo.get(s, name_or_id)
        else:
            t = self.tag_repo.get_by_name(s, name_or_id)
        if not t:
            raise TagNotFound(str(name_or_id))
        return t
