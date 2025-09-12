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


class Collection(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "collection"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folder_id: Mapped[int] = mapped_column(
        ForeignKey("folder.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    color_hint: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    folder: Mapped["Folder"] = relationship(back_populates="subcollections")

    # keep only the association object as the primary relationship
    collection_images: Mapped[List["CollectionImage"]] = relationship(
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="CollectionImage.position",
    )

    # expose images via an association proxy (unordered in SQL, but preserves python list order from collection_images)
    images = association_proxy("collection_images", "image")

    # or if you prefer an explicit ordered property:
    @property
    def images_ordered(self):
        return [ci.image for ci in self.collection_images]

    __table_args__ = (
        UniqueConstraint("folder_id", "name", name="uq_collection_folder_name"),
        Index("idx_collection_folder", "folder_id"),
        Index("idx_collection_folder_pos", "folder_id", "position"),
    )
