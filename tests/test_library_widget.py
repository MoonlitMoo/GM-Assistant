import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QInputDialog, QMessageBox, QMenu, QTreeWidget

from dmt.ui.library_items import Node, Leaf
from dmt.ui.library_widget import LibraryWidget
from tests.test_library_items import library_text, library_dict


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
def widget(tmp_path, library_text, qtbot, monkeypatch):
    # Ensure LibraryWidget finds library.json in CWD
    lib_file = tmp_path / "library.json"
    lib_file.write_text(library_text, encoding="utf-8")

    # Auto-accept dialogs: name prompts + delete confirms
    def fake_get_text(*args, **kwargs):
        default = kwargs.get("text", "") or kwargs.get("default", "") or "New Name"
        return default, True

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(fake_get_text))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))

    w = LibraryWidget(filename=lib_file)
    qtbot.addWidget(w)
    return w


def _find_item_by_text(tree, text):
    """ Find an item by its text. Only gets first instance.

    Parameters
    ----------
    tree : QTreeWidget or QTreeWidgetItem
        The place to start searching, only recurses down so that you can search a subtree.
    text : str
        The label to find.

    Returns
    -------
    item : QTreeWidgetItem or None
        The found item or None if not found
    """

    def walk(item):
        if item.text(0) == text:
            return item
        for i in range(item.childCount()):
            found = walk(item.child(i))
            if found:
                return found
        return None

    # Get top level item if it is the full widget.
    if isinstance(tree, QTreeWidget):
        top = tree.topLevelItem(0)
    else:
        top = tree
    return walk(top)


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


# ---- Tests ----
def test_add_folder_and_album(widget, monkeypatch):
    # Names to return for folder/album creation
    names = iter(["My Folder", "My Album", "My Subfolder", "My Subalbum"])

    def get_text_cycle(*args, **kwargs):
        return next(names), True

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(get_text_cycle))

    # Add Folder at root
    widget._create_node(make_album=False)
    folder_item = _find_item_by_text(widget.tree, "My Folder")
    assert folder_item is not None
    node = folder_item.data(0, Qt.UserRole).get("ref")
    assert isinstance(node, Node)
    assert node.label == "My Folder"

    # Add Album at root
    widget._create_node(make_album=True)
    album_item = _find_item_by_text(widget.tree, "My Album")
    assert album_item is not None
    node = album_item.data(0, Qt.UserRole).get("ref")
    assert isinstance(node, Leaf)
    assert node.label == "My Album"

    # Select subfolder
    subfolder = _find_item_by_text(widget.tree, "Session 1")
    widget.tree.setCurrentItem(subfolder)

    # Add Folder in subfolder
    widget._create_node(make_album=False)
    folder_item = _find_item_by_text(subfolder, "My Subfolder")
    assert folder_item is not None

    # Add Album in subfolder
    widget._create_node(make_album=True)
    album_item = _find_item_by_text(subfolder, "My Subalbum")
    assert album_item is not None

    # Assert that it's reflected in saved file
    with open(widget.LIBRARY_FILENAME, "r") as f:
        text = " ".join(s.strip() for s in f.readlines())
        assert "My Folder" in text
        assert "My Album" in text
        assert "My Subfolder" in text
        assert "My Subalbum" in text


def test_root_protected_from_delete(widget, monkeypatch):
    root = widget.tree.topLevelItem(0)
    pos_folder = widget.tree.visualItemRect(root).center()
    widget._on_tree_context_menu(pos_folder)
    assert _find_item_by_text(widget.tree, root.text(0))


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

    widget._create_node(make_album=False)
    widget._create_node(make_album=True)

    folder_item = _find_item_by_text(widget.tree, "Temp Folder")
    album_item = _find_item_by_text(widget.tree, "Temp Album")
    assert folder_item is not None and album_item is not None

    # Delete temp folder
    pos_folder = widget.tree.visualItemRect(folder_item).center()
    widget._on_tree_context_menu(pos_folder)
    assert _find_item_by_text(widget.tree, "Temp Folder") is None

    # Delete temp album
    pos_album = widget.tree.visualItemRect(album_item).center()
    widget._on_tree_context_menu(pos_album)
    assert _find_item_by_text(widget.tree, "Temp Album") is None

    # Select subfolder and create temp files
    subfolder = _find_item_by_text(widget.tree, "Session 1")
    widget.tree.setCurrentItem(subfolder)
    widget._create_node(make_album=False)
    widget._create_node(make_album=True)

    folder_item = _find_item_by_text(widget.tree, "Temp Subfolder")
    album_item = _find_item_by_text(widget.tree, "Temp Subalbum")

    # Delete temp subfolder
    pos_folder = widget.tree.visualItemRect(folder_item).center()
    widget._on_tree_context_menu(pos_folder)
    assert _find_item_by_text(widget.tree, "Temp Subfolder") is None

    # Delete temp subalbum
    pos_album = widget.tree.visualItemRect(album_item).center()
    widget._on_tree_context_menu(pos_album)
    assert _find_item_by_text(widget.tree, "Temp Subalbum") is None


def test_rename_folder_and_album(widget, monkeypatch):
    # Not testing rename of subfolder, since delete covers that.
    # Create one folder + one album first (names fixed via monkeypatched getText)
    names = iter(["Temp Folder", "Temp Album", "Renamed Folder", "Renamed Album"])

    def get_text_cycle(*args, **kwargs):
        return next(names), True

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(get_text_cycle))
    # Set context menu to return delete
    import dmt.ui.library_widget as lw
    monkeypatch.setattr(FakeContextMenu, "decision", "Rename")
    monkeypatch.setattr(lw, "QMenu", FakeContextMenu)

    # Add test nodes
    widget._create_node(make_album=False)
    widget._create_node(make_album=True)

    folder_item = _find_item_by_text(widget.tree, "Temp Folder")
    album_item = _find_item_by_text(widget.tree, "Temp Album")
    assert folder_item is not None and album_item is not None

    # Right-click position for folder
    pos_folder = widget.tree.visualItemRect(folder_item).center()
    widget._on_tree_context_menu(pos_folder)
    assert _find_item_by_text(widget.tree, "Renamed Folder") is not None

    # Right-click position for album
    pos_album = widget.tree.visualItemRect(album_item).center()
    widget._on_tree_context_menu(pos_album)
    assert _find_item_by_text(widget.tree, "Renamed Album") is not None

    # Assert that it's reflected in saved file
    with open(widget.LIBRARY_FILENAME, "r") as f:
        text = " ".join(s.strip() for s in f.readlines())
        assert "Renamed Folder" in text
        assert "Renamed Album" in text


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
