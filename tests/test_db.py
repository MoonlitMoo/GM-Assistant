import time

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db.models import Image, Tag, ImageTagLink
from tests.db_fixtures import session, make_folder, make_album, make_image, make_tag, make_image_tag_link


# --- Folder/Album/Image: inserts & constraints

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


# --- Folder/Album/Image: ordering of children

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


# --- Tag: inserts & constraints
def test_tag_create_minimal_and_timestamp(session, make_tag):
    t = make_tag("Theme")
    session.commit()

    fetched = session.get(Tag, t.id)
    assert fetched is not None
    assert fetched.created_at is not None
    assert fetched.updated_at is not None
    # updated_at should be >= created_at; allow equality (same-second commits)
    assert fetched.updated_at >= fetched.created_at


def test_tag_color_hex(session, make_tag):
    ok = make_tag("Greenish", color_hex="#A1B2C3")
    session.commit()
    assert session.get(Tag, ok.id).color_hex == "#A1B2C3"

@pytest.mark.parametrize("hex", ["#123", "A1B2C3", "A1B2C3#"])
def test_tag_color_hex_check(session, make_tag, hex):
    with pytest.raises(IntegrityError):
        make_tag("BadTag", color_hex=hex)
        session.commit()


def test_tag_case_insensitive_uniqueness(session, make_tag):
    _ = make_tag("Theme")
    session.commit()

    # Same spelling, different case → should violate UNIQUE(LOWER(name))
    with pytest.raises(IntegrityError):
        make_tag("theme")
        session.commit()


def test_tag_updated_at_changes_on_update(session, make_tag):
    t = make_tag("RecolorMe", color_hex="#112233")
    session.commit()
    before = session.get(Tag, t.id).updated_at
    # Ensure time > timestamp resolution (1 second) has passed
    time.sleep(1)
    # Update a field to trigger onupdate CURRENT_TIMESTAMP
    t.color_hex = "#445566"
    session.commit()
    after = session.get(Tag, t.id).updated_at

    assert after > before


# --- ImageTagLink: inserts, uniqueness & cascade -------------------------------
def test_image_tag_link_create_and_uniqueness(session, make_image, make_tag, make_image_tag_link):
    img = make_image(caption="tag-me", full_bytes=b"X")
    tag = make_tag("NPC")
    lnk = make_image_tag_link(img.id, tag)
    session.commit()

    fetched = session.get(ImageTagLink, lnk.id)
    assert fetched is not None
    assert fetched.image_id == img.id
    assert fetched.tag_id == tag.id
    assert fetched.tag.name == "NPC"  # eager-joined via relationship
    assert fetched.created_at is not None and fetched.updated_at is not None

    # Duplicate link should violate UNIQUE(image_id, tag_id)
    with pytest.raises(IntegrityError):
        make_image_tag_link(img.id, tag)
        session.commit()


def test_image_tag_link_deleted_on_image_delete(session, make_image, make_tag, make_image_tag_link):
    img = make_image(caption="to-delete", full_bytes=b"Y")
    t1 = make_tag("Prop")
    t2 = make_tag("Scene")

    l1 = make_image_tag_link(img.id, t1)
    l2 = make_image_tag_link(img.id, t2)
    session.commit()

    # Sanity
    ids = [l1.id, l2.id]
    rows = session.execute(select(ImageTagLink).where(ImageTagLink.id.in_(ids))).scalars().all()
    assert len(rows) == 2

    # Deleting the image should cascade to links
    session.delete(img)
    session.commit()

    gone = session.execute(select(ImageTagLink).where(ImageTagLink.id.in_(ids))).scalars().all()
    assert gone == []
