import pytest
from PySide6.QtWidgets import QInputDialog
from sqlalchemy import event, Engine, create_engine
from sqlalchemy.orm import sessionmaker

from dmt.db.models import Base, Folder, Album, Image, ImageData, AlbumImage
from dmt.db.models import Tag, ImageTagLink


# --- SQLite tuning for tests --------------------------------------------------
@event.listens_for(Engine, "connect")
def _sqlite_enable_fk(dbapi_connection, _):
    # Ensure ON DELETE CASCADE and general FK correctness in SQLite
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


# --- Database Fixtures -----------------------------------------------------------------
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


# --- UI patching fixtures ------------------
class _FakeContextMenu:
    """ Fake context menu with decision preselected. """
    decision = "Delete"

    def __init__(self, *args, **kwargs):
        self._actions = []
        self._chosen = None

    def addAction(self, text):
        # Create a tiny action stub with identity semantics
        act = type("Act", (), {})()
        act.text = text
        self._actions.append(act)
        # Preselect decision
        if text == self.decision:
            self._chosen = act
        return act

    def actions(self):
        return list(self._actions)

    # Mimic QMenu.exec(...) API and return the “clicked” action
    def exec(self, *args, **kwargs):
        return self._chosen


@pytest.fixture()
def set_context_menu(monkeypatch):
    """ Sets the context menu option to return the given decision. """
    def _set_menu(src, decision):
        monkeypatch.setattr(_FakeContextMenu, "decision", decision)
        monkeypatch.setattr(src, "QMenu", _FakeContextMenu)

    return _set_menu


@pytest.fixture()
def set_dialog_text(monkeypatch):
    """ Set the text for the next item in the dialog entry box. """

    def set_text(name):
        def get_text_cycle(*args, **kwargs):
            return name, True

        monkeypatch.setattr(QInputDialog, "getText", staticmethod(get_text_cycle))

    return set_text
