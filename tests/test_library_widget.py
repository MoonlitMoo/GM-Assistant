from contextlib import contextmanager

import pytest
from PySide6.QtWidgets import QInputDialog, QMessageBox, QAbstractItemView

from db.manager import DatabaseManager
from db.services.library_service import LibraryService
from dmt.ui.library_items import FolderItem, AlbumItem
from dmt.ui.library_widget import LibraryWidget

from tests.test_db import session, make_folder, make_album, make_image


class FakeContextMenu:
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
def simple_db(session, make_folder, make_album, make_image):
    # Root folders
    s1 = make_folder("Session 1", parent=None, position=0)
    s2 = make_folder("Session 2", parent=None, position=1)
    # Session 1 folder and album
    sf1 = make_folder("Locations", parent=s1, position=0)
    a1 = make_album(parent=s1, name="NPCs", position=0)
    # Session 2 folder and album
    sf2 = make_folder("Locations2", parent=s2, position=0)
    a2 = make_album(parent=s2, name="NPCs2", position=0)
    session.commit()
    return session


@pytest.fixture()
def widget(simple_db, qtbot, monkeypatch):
    # Auto-accept dialogs: name prompts + delete confirms
    def fake_get_text(*args, **kwargs):
        default = kwargs.get("text", "") or kwargs.get("default", "") or "New Name"
        return default, True

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(fake_get_text))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))

    @contextmanager
    def fake_session(self):
        yield simple_db

    dmb = DatabaseManager()
    monkeypatch.setattr(DatabaseManager, "session", fake_session)
    w = LibraryWidget(service=LibraryService(dmb))
    qtbot.addWidget(w)
    return w

@pytest.fixture()
def set_dialog_text(monkeypatch):
    """ Set the text for the next item in the dialog entry box. """
    def set_text(name):
        def get_text_cycle(*args, **kwargs):
            return name, True
        monkeypatch.setattr(QInputDialog, "getText", staticmethod(get_text_cycle))
    return set_text

@pytest.fixture()
def create_tree_item(monkeypatch, widget, set_dialog_text):
    """ Function to pass tree path and item type to create an item in the tree via the simulated UI. """
    def _create_tree_item(path, item_type):
        set_dialog_text(path[-1])
        assert item_type in ["folder", "album"]
        _select_by_path(widget.tree, path[:-1])
        widget._create_node(make_album=False if item_type == "folder" else True)
        item = _find_item_by_path(widget.tree, path)
        assert item is not None
        return item

    return _create_tree_item

@pytest.fixture()
def set_context_menu(monkeypatch):
    """ Sets the context menu option to return the given decision. """
    import dmt.ui.library_widget as lw
    def _set_menu(decision):
        monkeypatch.setattr(FakeContextMenu, "decision", decision)
        monkeypatch.setattr(lw, "QMenu", FakeContextMenu)
    return _set_menu

# ---- Helper functions ----
def _find_item_by_path(tree, labels):
    """Find item by a path of labels starting under the visible root."""
    item = tree.topLevelItem(0)  # visible root
    for label in labels:
        found = None
        for i in range(item.childCount()):
            ch = item.child(i)
            if ch.text(0) == label:
                found = ch
                break
        if not found:
            return None
        item = found
    return item

def _select_by_path(tree, labels):
    """ Go through the tree and select the item at the end of the path """
    item = tree.topLevelItem(0)  # visible root
    if not labels:
        tree.setCurrentItem(item)
        return True
    for label in labels:
        for i in range(item.childCount()):
            ch = item.child(i)
            if ch.text(0) == label:
                tree.setCurrentItem(ch)
                return True
    return False

# ---- Tests ----

def test_add_folder_and_album(widget, create_tree_item):
    # Add Folder at root
    folder_item = create_tree_item(["My Folder"], "folder")
    assert isinstance(folder_item, FolderItem)
    assert folder_item.label == "My Folder"
    assert widget.service.is_folder(folder_item.id)

    # Add Album at root
    album_item = create_tree_item(["My Album"], "album")
    assert isinstance(album_item, AlbumItem)
    assert album_item.label == "My Album"
    assert widget.service.is_album(album_item.id)

    # Add Folder in subfolder
    folder_item = create_tree_item(["Session 1", "My Subfolder"], "folder")
    assert isinstance(folder_item, FolderItem)
    assert widget.service.is_folder(folder_item.id)

    # Add Album in subfolder
    album_item = create_tree_item(["Session 2", "My Subalbum"], "album")
    assert isinstance(album_item, AlbumItem)
    assert widget.service.is_album(album_item.id)

def test_root_protected_from_delete(widget, monkeypatch):
    root = widget.tree.topLevelItem(0)
    pos_folder = widget.tree.visualItemRect(root).center()
    widget._on_tree_context_menu(pos_folder)
    assert widget.tree.topLevelItem(0)


def test_remove_folder_and_album(widget, create_tree_item, set_context_menu):
    set_context_menu("Delete")

    # Add the test nodes at root
    folder_item = create_tree_item(["Temp Folder"], "folder")
    album_item = create_tree_item(["Temp Album"], "album")

    # Delete temp folder
    pos_folder = widget.tree.visualItemRect(folder_item).center()
    widget._on_tree_context_menu(pos_folder)
    assert _find_item_by_path(widget.tree, ["Temp Folder"]) is None
    assert widget.service.get_folder(folder_item.id) is None

    # Delete temp album
    pos_album = widget.tree.visualItemRect(album_item).center()
    widget._on_tree_context_menu(pos_album)
    assert _find_item_by_path(widget.tree, ["Temp Album"]) is None
    assert widget.service.get_album(album_item.id) is None

    # Select subfolder and create temp files
    folder_item = create_tree_item(["Session 1", "Temp Subfolder"], "folder")
    album_item = create_tree_item(["Session 1", "Temp Subalbum"], "album")

    # Delete temp subfolder
    pos_folder = widget.tree.visualItemRect(folder_item).center()
    widget._on_tree_context_menu(pos_folder)
    assert _find_item_by_path(widget.tree, ["Session 1", "Temp Subfolder"]) is None
    assert widget.service.get_folder(folder_item.id) is None

    # Delete temp subalbum
    pos_album = widget.tree.visualItemRect(album_item).center()
    widget._on_tree_context_menu(pos_album)
    assert _find_item_by_path(widget.tree, ["Session 1", "Temp Subalbum"]) is None
    assert widget.service.get_album(album_item.id) is None


def test_recreate_item(widget, create_tree_item, set_context_menu):
    """ Check that we can make, delete, remake without problems. """
    # Set to delete
    set_context_menu("Delete")

    # Create
    item = create_tree_item(["Test"], "folder")
    assert widget.service.get_folder(item.id)
    # Delete
    pos_item = widget.tree.visualItemRect(item).center()
    widget._on_tree_context_menu(pos_item)
    assert not _find_item_by_path(widget.tree, ["Test"])
    assert widget.service.get_folder(item.id) is None
    # Recreate
    item = create_tree_item(["Test"], "folder")
    assert widget.service.get_folder(item.id)


def test_rename_folder_and_album(widget, set_context_menu, set_dialog_text):
    set_context_menu("Rename")

    # Get the two things to be renamed, expanding top folder to get at subfolder
    folder_item = _find_item_by_path(widget.tree, ["Session 1"])
    widget.tree.expandItem(_find_item_by_path(widget.tree, ["Session 2"]))
    album_item = _find_item_by_path(widget.tree, ["Session 2", "NPCs2"])
    assert folder_item is not None and album_item is not None

    # Rename folder
    set_dialog_text("Renamed Folder")
    pos_folder = widget.tree.visualItemRect(folder_item).center()
    widget._on_tree_context_menu(pos_folder)
    assert _find_item_by_path(widget.tree, ["Renamed Folder"]) is not None
    assert widget.service.get_folder(folder_item.id).name == "Renamed Folder"

    # Rename nested album
    set_dialog_text("Renamed Album")
    pos_album = widget.tree.visualItemRect(album_item).center()
    widget._on_tree_context_menu(pos_album)
    assert _find_item_by_path(widget.tree, ["Session 2", "Renamed Album"]) is not None
    assert widget.service.get_album(album_item.id).name == "Renamed Album"

@pytest.mark.parametrize("src_path, dst_path", [
    (["Session 1", "Locations"], ["Session 2"]),  # Subfolder -> Folder
    (["Session 1", "Locations"], []),  # Subfolder -> Root
    (["Session 1", "NPCs"], ["Session 2"]),  # Subalbum -> Folder
    (["Session 1", "NPCs"], [])  # Subalbum -> Root
])
def test_move_node_on_item(widget, src_path, dst_path):
    """ Check we can move folders and albums into new folders via OnItem drop. """
    src_parent = _find_item_by_path(widget.tree, src_path[:-1])
    src_item = _find_item_by_path(widget.tree, src_path)
    dst_item = _find_item_by_path(widget.tree, dst_path)
    assert src_parent and src_item and dst_item

    # Test move action
    widget.tree._handle_item_movement([src_item], dst_item, QAbstractItemView.OnItem)

   # UI. Parent no longer has as child, destination does.
    assert _find_item_by_path(widget.tree, dst_path + [src_path[-1]])
    assert src_item.id not in [src_parent.child(i).id for i in range(src_parent.childCount())]
    assert src_item.id in [dst_item.child(i).id for i in range(dst_item.childCount())]
    assert src_item.parent() is dst_item

    # DB. Check that the source is listed in children and position is at the end.
    if isinstance(src_item, FolderItem):
        db_item = widget.service.get_folder(src_item.id)
    else:
        db_item = widget.service.get_album(src_item.id)

    if dst_item.id is None:  # If the dst is root then don't check for it in the DB.
        assert db_item.parent_id is None
    else:
        db_dst = widget.service.get_folder(dst_item.id)
        assert db_item.parent_id == db_dst.id
        assert db_item in db_dst.subfolders + db_dst.albums
    assert db_item.position == dst_item.childCount() - 1

@pytest.mark.parametrize("src_path, dst_path", [
    (["Session 1", "Locations"], ["Session 1", "Locations"]),  # Folder -> self
    (["Session 1"], ["Session 1", "Locations"]),  # Folder -> Own subfolder
    (["Session 2"], ["Session 1", "NPCs"]),  # Folder -> Album
    (["Session 2", "NPCs2"], ["Session 1", "NPCs"]),  # Album -> Album
    ([], ["Session 1"])  # Root -> anywhere (also is folder -> descendant)
])
def test_catch_illegal_move(widget, src_path, dst_path):
    src_item = _find_item_by_path(widget.tree, src_path)
    dst_item = _find_item_by_path(widget.tree, dst_path)
    assert src_item and dst_item
    assert not widget.tree._handle_item_movement([src_item], dst_item, QAbstractItemView.OnItem)


# def test_move_image_to_album(widget):
#     src_item = _find_item_by_path(widget.tree, ["Session 1", "NPCs", "Guard"])
#     dst_item = _find_item_by_path(widget.tree, ["Session 1", "Locations"])
#     assert src_item and dst_item
#
#     src_img = src_item.data(0, Qt.UserRole)["ref"]
#     old_album = _find_item_by_path(widget.tree, ["Session 1", "NPCs"]).data(0, Qt.UserRole)["ref"]
#     new_album = dst_item.data(0, Qt.UserRole)["ref"]
#
#     # pre: image is in old album
#     assert src_img in old_album.images
#     assert src_img not in new_album.images
#
#     assert widget._is_valid_drop(src_item, dst_item)
#     widget._handle_internal_move(src_item, dst_item)
#
#     # UI parent changed
#     assert src_item.parent() is dst_item
#     # model lists updated
#     assert src_img not in old_album.images
#     assert src_img in new_album.images
