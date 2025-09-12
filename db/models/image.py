from __future__ import annotations
from typing import List, Optional
from sqlalchemy import (
    String, Integer, Text, ForeignKey, Index, func, LargeBinary
)
from sqlalchemy.orm import (
    Mapped, mapped_column, relationship, deferred
)
from sqlalchemy.types import JSON

from .mixins import Base, TimestampMixin, SoftDeleteMixin


class Image(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "image"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uri: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # now optional
    hash_sha256: Mapped[Optional[str]] = mapped_column(String, nullable=True, unique=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    width_px: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height_px: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bytes_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    taken_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    has_data: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0/1

    collection_links: Mapped[List["CollectionImage"]] = relationship(
        back_populates="image", cascade="all, delete-orphan"
    )

    # one-to-one payload; not loaded unless you access .data
    data: Mapped[Optional["ImageData"]] = relationship(
        back_populates="image", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (Index("idx_image_uri", "uri"),)

    def __repr__(self) -> str:
        return f"<Image id={self.id} uri='{self.uri}' has_data={self.has_data}>"


class CollectionImage(Base):
    """
    Association object for ordered membership of images in a collection.
    """
    __tablename__ = "collection_image"

    collection_id: Mapped[int] = mapped_column(
        ForeignKey("collection.id", ondelete="CASCADE"), primary_key=True
    )
    image_id: Mapped[int] = mapped_column(
        ForeignKey("image.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    added_at: Mapped[str] = mapped_column(
        String, server_default=func.current_timestamp(), nullable=False
    )

    collection: Mapped["Collection"] = relationship(back_populates="collection_images")
    image: Mapped[Image] = relationship(back_populates="collection_links")

    __table_args__ = (
        Index("idx_collimg_collection_pos", "collection_id", "position"),
        Index("idx_collimg_image", "image_id"),
    )

    def __repr__(self) -> str:
        return f"<CollectionImage coll={self.collection_id} img={self.image_id} pos={self.position}>"


class ImageData(Base):
    """
    Binary payloads for Image.
    Use deferred() so queries don't fetch large blobs unless explicitly accessed.
    """
    __tablename__ = "image_data"

    image_id: Mapped[int] = mapped_column(
        ForeignKey("image.id", ondelete="CASCADE"), primary_key=True
    )

    # Full original bytes (deferred load)
    bytes: Mapped[bytes] = deferred(
        mapped_column(LargeBinary, nullable=False)
    )

    # Optional, fast UI thumb (keep small: e.g., JPEG/WebP 256px)
    thumb_bytes: Mapped[Optional[bytes]] = deferred(
        mapped_column(LargeBinary, nullable=True)
    )

    # Optional extra info about encoded formats of the blobs
    bytes_format: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # e.g. 'PNG','JPEG','WEBP'
    thumb_format: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    image: Mapped["Image"] = relationship(back_populates="data")

    def __repr__(self) -> str:
        sz = "?" if self.bytes is None else "set"
        return f"<ImageData image_id={self.image_id} bytes={sz}>"
