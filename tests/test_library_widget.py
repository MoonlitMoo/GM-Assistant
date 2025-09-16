from contextlib import contextmanager

import pytest
from PySide6.QtWidgets import QInputDialog, QMessageBox

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
    a1 = make_album(folder=s1, name="NPCs", position=0)
    # Session 2 folder and album
    sf2 = make_folder("Locations2", parent=s2, position=0)
    a2 = make_album(folder=s2, name="NPCs2", position=0)
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

def test_add_folder_and_album(widget, monkeypatch):
    # Names to return for folder/album creation
    names = iter(["My Folder", "My Album", "My Subfolder", "My Subalbum"])

    def get_text_cycle(*args, **kwargs):
        return next(names), True

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(get_text_cycle))

    # Add Folder at root
    _select_by_path(widget.tree, [])
    widget._create_node(make_album=False)
    folder_item = _find_item_by_path(widget.tree, ["My Folder"])
    assert folder_item is not None and isinstance(folder_item, FolderItem)
    assert folder_item.label == "My Folder"
    assert widget.service.is_folder(folder_item.id)

    # Add Album at root
    _select_by_path(widget.tree, [])
    widget._create_node(make_album=True)
    album_item = _find_item_by_path(widget.tree, ["My Album"])
    assert album_item is not None and isinstance(album_item, AlbumItem)
    assert album_item.label == "My Album"
    assert widget.service.is_album(album_item.id)

    # Add Folder in subfolder
    _select_by_path(widget.tree, ["Session 1"])
    widget._create_node(make_album=False)
    folder_item = _find_item_by_path(widget.tree, ["Session 1", "My Subfolder"])
    assert folder_item is not None and isinstance(folder_item, FolderItem)
    assert widget.service.is_folder(folder_item.id)

    # Add Album in subfolder
    _select_by_path(widget.tree, ["Session 2"])
    widget._create_node(make_album=True)
    album_item = _find_item_by_path(widget.tree, ["Session 2", "My Subalbum"])
    assert album_item is not None and isinstance(album_item, AlbumItem)
    assert widget.service.is_album(album_item.id)



def test_root_protected_from_delete(widget, monkeypatch):
    root = widget.tree.topLevelItem(0)
    pos_folder = widget.tree.visualItemRect(root).center()
    widget._on_tree_context_menu(pos_folder)
    assert widget.tree.topLevelItem(0)


def test_remove_folder_and_album(widget, monkeypatch):
    # Create one folder + one album first (names fixed via monkeypatched getText)
    names = iter(["Temp Folder", "Temp Album", "Temp Subfolder", "Temp Subalbum"])

    def get_text_cycle(*args, **kwargs):
        return next(names), True

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(get_text_cycle))
    # Set context menu to return delete
    import dmt.ui.library_widget as lw
    monkeypatch.setattr(FakeContextMenu, "decision", "Delete")
    monkeypatch.setattr(lw, "QMenu", FakeContextMenu)

    # Add the test nodes at root
    _select_by_path(widget.tree, [])
    widget._create_node(make_album=False)
    _select_by_path(widget.tree, [])
    widget._create_node(make_album=True)

    folder_item = _find_item_by_path(widget.tree, ["Temp Folder"])
    album_item = _find_item_by_path(widget.tree, ["Temp Album"])
    assert folder_item is not None and album_item is not None

    # Delete temp folder
    pos_folder = widget.tree.visualItemRect(folder_item).center()
    widget._on_tree_context_menu(pos_folder)
    assert _find_item_by_path(widget.tree, ["Temp Folder"]) is None
    assert widget.service.get_folder(folder_item.id).is_deleted

    # Delete temp album
    pos_album = widget.tree.visualItemRect(album_item).center()
    widget._on_tree_context_menu(pos_album)
    assert _find_item_by_path(widget.tree, ["Temp Album"]) is None
    assert widget.service.get_album(album_item.id).is_deleted

    # Select subfolder and create temp files
    _select_by_path(widget.tree, ["Session 1"])
    widget._create_node(make_album=False)
    _select_by_path(widget.tree, ["Session 1"])
    widget._create_node(make_album=True)

    folder_item = _find_item_by_path(widget.tree, ["Session 1", "Temp Subfolder"])
    album_item = _find_item_by_path(widget.tree, ["Session 1", "Temp Subalbum"])

    # Delete temp subfolder
    pos_folder = widget.tree.visualItemRect(folder_item).center()
    widget._on_tree_context_menu(pos_folder)
    assert _find_item_by_path(widget.tree, ["Session 1", "Temp Subfolder"]) is None
    assert widget.service.get_folder(folder_item.id).is_deleted

    # Delete temp subalbum
    pos_album = widget.tree.visualItemRect(album_item).center()
    widget._on_tree_context_menu(pos_album)
    assert _find_item_by_path(widget.tree, ["Session 1", "Temp Subalbum"]) is None
    assert widget.service.get_album(album_item.id).is_deleted


def test_rename_folder_and_album(widget, monkeypatch):
    # Not testing rename of subfolder, since delete covers that.
    # Create one folder + one album first (names fixed via monkeypatched getText)
    names = iter(["Renamed Folder", "Renamed Album"])

    def get_text_cycle(*args, **kwargs):
        return next(names), True

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(get_text_cycle))
    # Set context menu to return delete
    import dmt.ui.library_widget as lw
    monkeypatch.setattr(FakeContextMenu, "decision", "Rename")
    monkeypatch.setattr(lw, "QMenu", FakeContextMenu)

    folder_item = _find_item_by_path(widget.tree, ["Session 1"])
    f2 = _find_item_by_path(widget.tree, ["Session 2"])
    widget.tree.expandItem(f2)
    album_item = _find_item_by_path(widget.tree, ["Session 2", "NPCs2"])
    assert folder_item is not None and album_item is not None

    # Right-click position for folder
    pos_folder = widget.tree.visualItemRect(folder_item).center()
    widget._on_tree_context_menu(pos_folder)
    assert _find_item_by_path(widget.tree, ["Renamed Folder"]) is not None
    assert widget.service.get_folder(folder_item.id).name == "Renamed Folder"

    # Right-click position for album
    pos_album = widget.tree.visualItemRect(album_item).center()
    widget._on_tree_context_menu(pos_album)
    assert _find_item_by_path(widget.tree, ["Session 2", "Renamed Album"]) is not None
    assert widget.service.get_album(album_item.id).name == "Renamed Album"

# def test_move_folder_to_folder_updates_model_and_ui(widget):
#     # Add subfolder
#     widget._create_node(make_album=False)
#     subfolder = _find_item_by_text(widget.tree, "Session 1")
#     widget.tree.setCurrentItem(subfolder)
#     widget._create_node(make_album=False)
#
#     src_item = _find_item_by_path(widget.tree, ["Session 1", "SubFolder"])
#     dst_item = _find_item_by_path(widget.tree, ["Dest"])
#     assert src_item and dst_item
#
#     # preconditions
#     assert src_item.parent().text(0) == "Session 1"
#     src_ref = src_item.data(0, Qt.UserRole)["ref"]
#     old_parent_ref = src_item.parent().data(0, Qt.UserRole)["ref"]
#     new_parent_ref = dst_item.data(0, Qt.UserRole)["ref"]
#     assert src_ref in list(old_parent_ref)
#
#     # move
#     assert widget._is_valid_drop(src_item, dst_item)
#     widget._handle_internal_move(src_item, dst_item)
#
#     # UI parent changed
#     assert src_item.parent() is dst_item
#     # model parents changed
#     assert src_ref not in list(old_parent_ref)
#     assert src_ref in list(new_parent_ref)
#     # save called
#     assert widget._save_calls, "save_library should be called at least once"
#
#
# def test_move_album_to_folder(widget):
#     src_item = _find_item_by_path(widget.tree, ["Session 1", "NPCs"])
#     dst_item = _find_item_by_path(widget.tree, ["Dest"])
#     assert src_item and dst_item
#
#     src_ref = src_item.data(0, Qt.UserRole)["ref"]
#     old_parent_ref = src_item.parent().data(0, Qt.UserRole)["ref"]
#     new_parent_ref = dst_item.data(0, Qt.UserRole)["ref"]
#
#     assert widget._is_valid_drop(src_item, dst_item)
#     widget._handle_internal_move(src_item, dst_item)
#
#     assert src_item.parent() is dst_item
#     assert src_ref not in list(old_parent_ref)
#     assert src_ref in list(new_parent_ref)
#
#
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
#
#
# def test_invalid_drops_disallowed(widget):
#     folder = _find_item_by_path(widget.tree, ["Session 1"])
#     subfolder = _find_item_by_path(widget.tree, ["Session 1", "SubFolder"])
#     album = _find_item_by_path(widget.tree, ["Session 1", "NPCs"])
#     image = _find_item_by_path(widget.tree, ["Session 1", "NPCs", "Guard"])
#     assert folder and subfolder and album and image
#
#     # Cannot drop folder/album onto album
#     assert not widget._is_valid_drop(subfolder, album)
#     assert not widget._is_valid_drop(album, album)
#
#     # Image cannot drop onto folder
#     assert not widget._is_valid_drop(image, folder)
#
#     # Cannot drop onto self
#     assert not widget._is_valid_drop(folder, folder)
#     assert not widget._is_valid_drop(album, album)
#     assert not widget._is_valid_drop(image, image)
#
#     # No cycles: cannot move ancestor under its descendant
#     assert not widget._is_valid_drop(folder, subfolder)
