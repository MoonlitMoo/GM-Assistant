import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from db.models import (
    Base,
    Folder,
    Album,
    Image,
    ImageData,
    AlbumImage,
)


# --- SQLite tuning for tests --------------------------------------------------
@event.listens_for(Engine, "connect")
def _sqlite_enable_fk(dbapi_connection, _):
    # Ensure ON DELETE CASCADE and general FK correctness in SQLite
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()
pass

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


# Small helpers to create rows succinctly

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


# --- Tests: inserts & constraints --------------------------------------------

def test_add_folders_and_uniqueness(session, make_folder):
    root = make_folder("root", parent=None, position=0)
    npc_a = make_folder("NPCs", parent=root, position=0)

    # Same name under different parent -> allowed
    loc_a = make_folder("Locations", parent=root, position=1)
    other_parent = make_folder("Session 2", parent=root, position=2)
    npc_b = make_folder("NPCs", parent=other_parent, position=0)  # OK
    session.commit()

    # Basic shape sanity
    assert npc_a.parent_id == root.id
    assert npc_b.parent_id == other_parent.id

    # Same name under same parent -> should violate UNIQUE(parent_id, name)
    with pytest.raises(IntegrityError):
        dup = make_folder("NPCs", parent=root, position=1)
        session.commit()


def test_add_albums_and_uniqueness(session, make_folder, make_album):
    root = make_folder("root")
    f1 = make_folder("Session 1", parent=root)
    f2 = make_folder("Session 2", parent=root)

    c1 = make_album(f1, "NPCs", position=0)

    # Same name in different folder -> OK
    c2 = make_album(f2, "NPCs", position=5)
    session.commit()
    assert c1.parent_id != c2.parent_id

    # Same name in same folder -> UNIQUE(folder_id, name) violation
    with pytest.raises(IntegrityError):
        make_album(f1, "NPCs", position=1)
        session.commit()


def test_add_image_with_blob_data(session, make_image):
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # pretend PNG bytes
    thumb = b"THUMB" * 10

    img = make_image(
        uri="library/foo.png",
        caption="foo",
        full_bytes=data,
        thumb_bytes=thumb,
        mime_type="image/png",
        width_px=128,
        height_px=64,
    )
    session.commit()

    fetched = session.get(Image, img.id)
    assert fetched is not None
    assert fetched.has_data == 1
    assert fetched.bytes_size == len(data)

    # Access deferred bytes via relationship
    assert fetched.data is not None
    assert fetched.data.bytes[:8] == b"\x89PNG\r\n\x1a\n"
    assert fetched.data.thumb_bytes is not None


# --- Tests: ordering of children ---------------------------------------------

def test_folder_display_children_order(session, make_folder, make_album):
    """
    Folder.display_children should merge subfolders + subalbums and sort by:
    position, then kind ('folder' before 'album'), then id (stable).
    """
    root = make_folder("root")
    # positions interleaved on purpose
    f_sub1 = make_folder("A_subfolder", parent=root, position=1)
    c1 = make_album(root, "A_album", position=0)
    f_sub2 = make_folder("B_subfolder", parent=root, position=2)
    c2 = make_album(root, "B_album", position=2)  # same pos as f_sub2

    session.commit()

    order = [(kind, obj.name, pos) for kind, obj, pos in root.children]
    # Expected:
    # pos 0 -> album 'A_album'
    # pos 1 -> folder    'A_subfolder'
    # pos 2 -> folder 'B_subfolder' (folder before album at same position)
    # pos 2 -> album 'B_album'
    assert order[0] == ("album", "A_album", 0)
    assert order[1] == ("folder", "A_subfolder", 1)
    assert order[2][0] == "folder" and order[2][2] == 2
    assert order[3][0] == "album" and order[3][2] == 2


def test_album_images_order(session, make_folder, make_album, make_image):
    root = make_folder("root")
    coll = make_album(root, "NPCs", position=0)

    # Add images with scrambled AlbumImage.position
    i2 = make_image(caption="img2", full_bytes=b"2", position_in=coll, position_index=2)
    i0 = make_image(caption="img0", full_bytes=b"0", position_in=coll, position_index=0)
    i1 = make_image(caption="img1", full_bytes=b"1", position_in=coll, position_index=1)
    session.commit()

    # Relationship .album_images should be ordered by position: 0,1,2
    positions = [ci.position for ci in coll.album_images]
    captions = [ci.image.caption for ci in coll.album_images]
    assert positions == [0, 1, 2]
    assert captions == ["img0", "img1", "img2"]

    # association_proxy 'images' should follow the same order:
    assert [img.caption for img in coll.images] == ["img0", "img1", "img2"]
