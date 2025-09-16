from __future__ import annotations

from typing import Any

from sqlalchemy import String, func, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass

Base.metadata.naming_convention = {
            "ix": "ix_%(table_name)s_%(column_0_N_label)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }

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
