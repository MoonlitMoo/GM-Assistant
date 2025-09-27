from sqlalchemy import Column, ForeignKey, Integer, String, Enum, JSON
from sqlalchemy.orm import relationship
import enum

from db.models.mixins import Base


class PlaylistType(enum.Enum):
    MANUAL = "manual"
    SMART = "smart"
    IMAGE = "image"


class Playlist(Base):
    __tablename__ = "playlist"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(Enum(PlaylistType), nullable=False, default=PlaylistType.MANUAL)

    # For smart playlists, stores tag query expression as JSON
    query = Column(JSON)
    # For IMAGE playlists, this links to an image in your existing image table
    image_id = Column(Integer, ForeignKey("image.id", ondelete="CASCADE"))

    # relationships
    items = relationship("PlaylistItem", back_populates="playlist", cascade="all, delete-orphan")


class PlaylistItem(Base):
    __tablename__ = "playlist_item"

    id = Column(Integer, primary_key=True)
    playlist_id = Column(Integer, ForeignKey("playlist.id", ondelete="CASCADE"), nullable=False)
    song_id = Column(Integer, ForeignKey("song.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, nullable=False)

    playlist = relationship("Playlist", back_populates="items")
    song = relationship("Song", back_populates="playlist_items")
