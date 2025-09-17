from __future__ import annotations
from typing import List, Optional
from sqlalchemy import (
    String, Integer, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import (
    Mapped, mapped_column, relationship
)

from .mixins import Base, TimestampMixin, SoftDeleteMixin


class Folder(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "folder"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("folder.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    parent: Mapped[Optional["Folder"]] = relationship(
        back_populates="subfolders", remote_side="Folder.id"
    )
    subfolders: Mapped[List["Folder"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="Folder.position",
    )
    albums: Mapped[List["Album"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="Album.position",
    )

    __table_args__ = (
        UniqueConstraint("parent_id", "name", name="uq_folder_parent_name"),
        Index("idx_folder_parent", "parent_id"),
        Index("idx_folder_parent_pos", "parent_id", "position"),
    )

    @property
    def children(self):
        """
        Return a merged, stably-sorted list of (kind, obj, position) for UI.
        kind is 'folder' or 'album'.
        """
        items = [("folder", f, f.position) for f in self.subfolders] + \
                [("album", c, c.position) for c in self.albums]
        # tie-break by kind then id for stability
        items.sort(key=lambda t: (t[2], 0 if t[0] == "folder" else 1, getattr(t[1], "id", 0)))
        return items

    def __repr__(self) -> str:
        return f"<Folder id={self.id} name='{self.name}' parent={self.parent_id}>"
