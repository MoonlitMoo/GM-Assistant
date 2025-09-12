from __future__ import annotations

from sqlalchemy import String, func, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[str] = mapped_column(
        String, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[str] = mapped_column(
        String,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )


class SoftDeleteMixin:
    is_deleted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
