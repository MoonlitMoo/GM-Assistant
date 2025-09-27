from datetime import datetime, UTC

import pytest
from sqlalchemy import event, Engine, create_engine
from sqlalchemy.orm import sessionmaker

from db.models import (
    Base, Folder, Album, Image, ImageData, AlbumImage, PlaylistType, Playlist, PlaylistItem,
    SongSource, Song, Tag, ImageTagLink, SongTagLink
)


# --- SQLite tuning for tests --------------------------------------------------
@event.listens_for(Engine, "connect")
def _sqlite_enable_fk(dbapi_connection, _):
    # Ensure ON DELETE CASCADE and general FK correctness in SQLite
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


# --- Fixtures -----------------------------------------------------------------
@pytest.fixture()
def session():
    """Fresh session per test."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    with session() as s:
        yield s
        s.rollback()  # clean even if the test forgot


# --- Helper fixtures for creating rows ----------------------------------------
@pytest.fixture()
def make_folder(session):
    def _mk(name: str, parent: Folder | None = None, position: int = 0) -> Folder:
        f = Folder(name=name, parent=parent, position=position)
        session.add(f)
        session.flush()
        return f

    return _mk


@pytest.fixture()
def make_album(session):
    def _mk(parent: Folder, name: str, position: int = 0) -> Album:
        c = Album(parent=parent, name=name, position=position)
        session.add(c)
        session.flush()
        return c

    return _mk


@pytest.fixture()
def make_image(session):
    def _mk(
            uri: str | None = None,
            caption: str | None = None,
            *,
            full_bytes: bytes | None = None,
            thumb_bytes: bytes | None = None,
            mime_type: str | None = "image/png",
            width_px: int | None = 64,
            height_px: int | None = 64,
            position_in: Album | None = None,
            position_index: int = 0,
    ) -> Image:
        img = Image(
            uri=uri,
            caption=caption,
            mime_type=mime_type,
            width_px=width_px,
            height_px=height_px,
        )
        session.add(img)
        session.flush()  # get id

        # Attach bytes (BLOBs) via ImageData (deferred columns)
        if full_bytes is not None or thumb_bytes is not None:
            if full_bytes is None:
                full_bytes = b""
            img.bytes_size = len(full_bytes)
            img.has_data = 1
            session.add(
                ImageData(
                    image_id=img.id,
                    bytes=full_bytes,
                    thumb_bytes=thumb_bytes,
                    bytes_format="PNG",
                    thumb_format="PNG" if thumb_bytes else None,
                )
            )

        # Optionally add to a album with an explicit position
        if position_in is not None:
            session.add(
                AlbumImage(
                    album_id=position_in.id,
                    image_id=img.id,
                    position=position_index,
                )
            )

        session.flush()
        return img

    return _mk


@pytest.fixture()
def make_tag(session):
    def _mk(name: str, color_hex: str | None = None, kind: str | None = None) -> Tag:
        t = Tag(name=name, color_hex=color_hex, kind=kind)
        session.add(t)
        session.flush()
        return t

    return _mk


@pytest.fixture()
def make_image_tag_link(session):
    def _mk(image_id: int, tag: Tag) -> ImageTagLink:
        lnk = ImageTagLink(image_id=image_id, tag=tag)
        session.add(lnk)
        session.flush()
        return lnk

    return _mk


@pytest.fixture()
def make_song(session):
    def _make(title: str = "Track", artist: str = "Unknown", source: SongSource = SongSource.LOCAL,
              uri: str = "file:///track.mp3", duration_ms: int = 120_000) -> Song:
        s = Song(
            title=title, artist=artist, source=source, uri=uri, duration_ms=duration_ms,
            date_added=datetime.now(UTC))
        session.add(s)
        session.flush()
        return s

    return _make


@pytest.fixture()
def tag_song(session):
    def _link(song: Song, tag: Tag) -> SongTagLink:
        link = SongTagLink(song_id=song.id, tag_id=tag.id)
        session.add(link)
        session.flush()
        return link

    return _link


@pytest.fixture()
def make_playlist(session):
    def _make(name: str, type_: PlaylistType = PlaylistType.MANUAL, query=None, image: Image | None = None) -> Playlist:
        p = Playlist(name=name, type=type_, query=query)
        if image is not None:
            p.image = image
        session.add(p)
        session.flush()
        return p

    return _make


@pytest.fixture()
def add_playlist_item(session):
    def _add(playlist: Playlist, song: Song, position: int) -> PlaylistItem:
        item = PlaylistItem(playlist_id=playlist.id, song_id=song.id, position=position)
        session.add(item)
        session.flush()
        return item

    return _add
