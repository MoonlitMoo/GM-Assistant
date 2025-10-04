from __future__ import annotations
from datetime import datetime, UTC
from enum import Enum
from typing import Optional

from sqlalchemy import (
    String, Integer, DateTime, Enum as SAEnum,
    UniqueConstraint, CheckConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .mixins import Base


# ---- Enums -------------------------------------------------------------------
class SongSource(str, Enum):
    spotify = "spotify"
    file = "file"        # local path on disk
    url = "url"          # generic stream / http(s)


# ---- Tables ------------------------------------------------------------------
class Song(Base):
    __tablename__ = "song"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Display/browse fields
    title: Mapped[str] = mapped_column(String(255), index=True)
    artist: Mapped[str] = mapped_column(String(255), index=True)            # e.g. "Artist feat. Other"
    album: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Source identity
    source: Mapped[SongSource] = mapped_column(SAEnum(SongSource), index=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)   # spotify track id, etc.
    source_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # open.spotify.com/...

    # Playback hints / metadata
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)

    # Local file support (when source == file)
    local_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # App metadata
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC))
    play_count: Mapped[int] = mapped_column(Integer, default=0)
    last_played_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        # Unique per external source id (when provided)
        UniqueConstraint("source", "source_id", name="uq_song_source_sourceid"),
        # Local files must have a path; non-files must not require it
        CheckConstraint("(source != 'file') OR (local_path IS NOT NULL)", name="ck_song_file_has_path"),
        # Duration sanity
        CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="ck_song_duration_nonneg"),
        # Common browse composite index
        Index("ix_song_title_artist", "title", "artist"),
    )
