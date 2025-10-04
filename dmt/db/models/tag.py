from __future__ import annotations

from sqlalchemy import Integer, Text, UniqueConstraint, Index, CheckConstraint, text, ForeignKey
from sqlalchemy.orm import (
    Mapped, mapped_column, relationship
)
from dmt.db.models.mixins import TimestampMixin, Base


# ---------- Tag ----------
class Tag(Base, TimestampMixin):
    """ Defines a tag. This has a user-defined name alongside a potential colour and kind of tag.
    The tag names are not case-sensitive and colours must be hex codes. There is currently no checks relating to the
    allowed kinds of tags.
    """
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    color_hex: Mapped[str | None] = mapped_column(Text, nullable=True)
    kind: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        # Portable unique (case-sensitive). The functional unique index below enforces case-insensitive uniqueness.
        UniqueConstraint("name", name="uq_tag_name_cs"),
        Index("ix_tag_name", "name"),
        # Functional unique index: UNIQUE(LOWER(name)) → prevents 'Theme' vs 'theme' duplicates.
        Index("uq_tag_name_lower", text("LOWER(name)"), unique=True),
        # CHECK for color_hex: either NULL or 7 chars starting with '#'
        CheckConstraint(
            "(color_hex IS NULL) OR (length(color_hex) = 7 AND substr(color_hex,1,1) = '#')",
            name="ck_tag_color_hex_format",
        ),
    )

    def __repr__(self) -> str:
        return f"<Tag id={self.id} name={self.name!r} color={self.color_hex!r}>"


# ---------- Image tag link ----------
class ImageTagLink(Base, TimestampMixin):
    """ Defines the tags associated with an image. """
    __tablename__ = "image_tag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    image_id: Mapped[int] = mapped_column(
        ForeignKey("image.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tag.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Eager-load tag to simplify UI chip rendering
    tag: Mapped["Tag"] = relationship("Tag", lazy="joined")

    __table_args__ = (
        UniqueConstraint("image_id", "tag_id", name="uq_image_tag_image_tag"),
        Index("ix_image_tag_image_id", "image_id"),
        Index("ix_image_tag_tag_id", "tag_id"),
    )

    def __repr__(self) -> str:
        return f"<ImageTagLink image_id={self.image_id} tag_id={self.tag_id}>"


class SongTagLink(Base, TimestampMixin):
    """Defines the tags associated with a song."""
    __tablename__ = "song_tag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    song_id: Mapped[int] = mapped_column(
        ForeignKey("song.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tag.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Eager-load tag to simplify UI chip rendering
    tag: Mapped["Tag"] = relationship("Tag", lazy="joined")

    __table_args__ = (
        UniqueConstraint("song_id", "tag_id", name="uq_song_tag_song_tag"),
        Index("ix_song_tag_song_id", "song_id"),
        Index("ix_song_tag_tag_id", "tag_id"),
    )
