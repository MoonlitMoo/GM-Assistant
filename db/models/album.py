from __future__ import annotations
from typing import List, Optional
from sqlalchemy import (
    String, Integer, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import (
    Mapped, mapped_column, relationship
)

from .mixins import Base, TimestampMixin, SoftDeleteMixin
from .folder import Folder


class Album(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "album"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_id: Mapped[int] = mapped_column(
        ForeignKey("folder.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    color_hint: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    folder: Mapped["Folder"] = relationship(back_populates="albums")

    # keep only the association object as the primary relationship
    album_images: Mapped[List["AlbumImage"]] = relationship(
        back_populates="album",
        cascade="all, delete-orphan",
        order_by="AlbumImage.position",
    )

    # expose images via an association proxy (unordered in SQL, but preserves python list order from album_images)
    images = association_proxy("album_images", "image")

    # or if you prefer an explicit ordered property:
    @property
    def images_ordered(self):
        return [ci.image for ci in self.album_images]

    __table_args__ = (
        UniqueConstraint("parent_id", "name", name="uq_album_folder_name"),
        Index("idx_album_folder", "parent_id"),
        Index("idx_album_folder_pos", "parent_id", "position"),
    )

    def __repr__(self) -> str:
        return f"<Album id={self.id} name='{self.name}' parent={self.parent_id}>"
