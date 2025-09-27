from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.orm import relationship
import enum

from db.models.mixins import Base


class SongSource(enum.Enum):
    LOCAL = "local"
    SPOTIFY = "spotify"
    YOUTUBE = "youtube"


class Song(Base):
    __tablename__ = "song"

    id = Column(Integer, primary_key=True)
    source = Column(Enum(SongSource), nullable=False)
    uri = Column(String, nullable=False, unique=True)

    title = Column(String, nullable=False)
    artist = Column(String)
    album = Column(String)
    duration_ms = Column(Integer)

    date_added = Column(DateTime)
    play_count = Column(Integer, default=0)
    last_played = Column(DateTime)

    # relationships
    tags = relationship("SongTagLink", cascade="all, delete-orphan")
    playlist_items = relationship("PlaylistItem", back_populates="song", cascade="all, delete-orphan")
