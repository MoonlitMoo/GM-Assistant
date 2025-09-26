from __future__ import annotations
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from db.models import Tag, ImageTagLink


class TagRepo:
    """Low-level data access for the Tag catalogue."""

    # ---------- reads ----------
    def get(self, s: Session, tag_id: int) -> Optional[Tag]:
        return s.get(Tag, tag_id)

    def get_by_name(self, s: Session, name: str) -> Optional[Tag]:
        stmt = select(Tag).where(func.lower(Tag.name) == name.lower())
        return s.execute(stmt).scalar_one_or_none()

    def list(self, s: Session, query: Optional[str] = None, limit: int = 50, offset: int = 0) -> list[Tag]:
        """ Return list where query is prefix. """
        stmt = select(Tag)
        if query:
            q = query.strip().lower()
            if q:
                stmt = stmt.where(func.lower(Tag.name).like(q + "%"))
        stmt = stmt.order_by(Tag.name).limit(limit).offset(offset)
        return s.execute(stmt).scalars().all()

    def usage_counts(self, s: Session, limit: int = 100) -> list[tuple[Tag, int]]:
        """ Return list of most used tags. """
        from db.models import ImageTagLink
        stmt = (
            select(Tag, func.count())
            .join(ImageTagLink, ImageTagLink.tag_id == Tag.id)
            .group_by(Tag.id)
            .order_by(func.count().desc(), Tag.name)
            .limit(limit)
        )
        return [(t, cnt) for t, cnt in s.execute(stmt).all()]

    # ---------- writes ----------
    def create(self, s: Session, name: str, *, color_hex: str | None = None, kind: str | None = None) -> Tag:
        t = Tag(name=name.strip(), color_hex=color_hex, kind=kind)
        s.add(t)
        s.flush()
        return t

    def rename(self, s: Session, tag: Tag, new_name: str) -> Tag:
        tag.name = new_name.strip()
        s.flush()
        return tag

    def recolor(self, s: Session, tag: Tag, color_hex: str | None) -> Tag:
        tag.color_hex = color_hex
        s.flush()
        return tag

    def retype(self, s: Session, tag: Tag, kind: str | None) -> Tag:
        tag.kind = kind
        s.flush()
        return tag

    def delete(self, s: Session, tag: Tag) -> None:
        s.delete(tag)
        s.flush()


class ImageTagRepo:
    """Data access for image <-> tag links and useful aggregations."""

    # ---------- single-entity ----------
    def get_tags_for_image(self, s: Session, image_id: int) -> list[Tag]:
        """ Gets all tags for the given image. """
        stmt = (
            select(Tag)
            .join(ImageTagLink, ImageTagLink.tag_id == Tag.id)
            .where(ImageTagLink.image_id == image_id)
            .order_by(Tag.name)
        )
        return s.execute(stmt).scalars().all()

    def get_link(self, s: Session, image_id: int, tag_id: int) -> Optional[ImageTagLink]:
        """ Gets the link for the given relation. """
        stmt = select(ImageTagLink).where(
            ImageTagLink.image_id == image_id,
            ImageTagLink.tag_id == tag_id,
        )
        return s.execute(stmt).scalar_one_or_none()

    def add_link(self, s: Session, image_id: int, tag_id: int) -> ImageTagLink:
        lnk = ImageTagLink(image_id=image_id, tag_id=tag_id)
        s.add(lnk)
        s.flush()
        return lnk

    def remove_link(self, s: Session, image_id: int, tag_id: int) -> None:
        lnk = self.get_link(s, image_id, tag_id)
        if lnk:
            s.delete(lnk)
            s.flush()

    def replace_links(self, s: Session, image_id: int, new_tag_ids: set[int]) -> None:
        """Authoritatively set the image's tag set to new_tag_ids."""
        existing = s.execute(
            select(ImageTagLink).where(ImageTagLink.image_id == image_id)
        ).scalars().all()
        existing_ids = {lnk.tag_id for lnk in existing}

        # delete removed
        for lnk in existing:
            if lnk.tag_id not in new_tag_ids:
                s.delete(lnk)

        # add missing
        for tid in new_tag_ids - existing_ids:
            s.add(ImageTagLink(image_id=image_id, tag_id=tid))

        s.flush()

    # ---------- batch (avoid N+1) ----------
    def tags_for_images(self, s: Session, image_ids: list[int]) -> dict[int, list[Tag]]:
        """Return a mapping {image_id: [Tag, ...]} for many images at once."""
        if not image_ids:
            return {}
        stmt = (
            select(ImageTagLink.image_id, Tag)
            .join(Tag, Tag.id == ImageTagLink.tag_id)
            .where(ImageTagLink.image_id.in_(image_ids))
            .order_by(ImageTagLink.image_id, Tag.name)
        )
        out: dict[int, list[Tag]] = {}
        for iid, tag in s.execute(stmt).all():
            out.setdefault(iid, []).append(tag)
        # ensure keys exist even if no tags
        for iid in image_ids:
            out.setdefault(iid, [])
        return out

    # ---------- maintenance for tag merge ----------
    def move_links_to_other_tag(self, s: Session, source_tag_id: int, target_tag_id: int) -> None:
        """
        Repoin t image links from source -> target. Because (image_id, tag_id) is UNIQUE,
        delete conflicts first then update.
        """
        # delete any target duplicates
        dup_iids = [
            iid for (iid,) in s.execute(
                select(ImageTagLink.image_id).where(ImageTagLink.tag_id == source_tag_id)
            ).all()
            if self.get_link(s, iid, target_tag_id) is not None
        ]
        if dup_iids:
            s.query(ImageTagLink).filter(
                ImageTagLink.tag_id == source_tag_id,
                ImageTagLink.image_id.in_(dup_iids)
            ).delete(synchronize_session=False)

        # re-point remaining
        s.query(ImageTagLink).filter(
            ImageTagLink.tag_id == source_tag_id
        ).update({ImageTagLink.tag_id: target_tag_id}, synchronize_session=False)
        s.flush()
