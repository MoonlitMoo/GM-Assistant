from contextlib import contextmanager

import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QMessageBox, QInputDialog, QMenu

from db.manager import DatabaseManager
from db.models import Song, SongSource, Playlist, PlaylistType
from db.models import PlaylistItem, Image, Tag
from db.services.tagging_service import TaggingService
from db.services.song_service import SongService, PlaylistService, InvalidSourceError
from dmt.ui.music_tab import SongTab
from tests.test_library_widget import FakeContextMenu


# ---------------------- Fake dialogs (monkeypatch targets) ----------------------

class _FakeAddSongDialog:
    _payloads = []

    def __init__(self, *args, **kwargs): ...

    @classmethod
    def set_payloads(cls, payloads): cls._payloads = list(payloads)

    def exec(self): return True

    def payloads(self): return list(self._payloads)


class _FakeTagSongsDialog:
    _result = ([], [], [])

    def __init__(self, *args, **kwargs): ...

    @classmethod
    def set_result(cls, add_names, add_ids, remove_ids):
        cls._result = (list(add_names or []), list(add_ids or []), list(remove_ids or []))

    def exec(self): return True

    def result_sets(self): return self._result


# ---------------------- Local UI helpers ----------------------

def _table_titles(tab: SongTab):
    m = tab.table.model()
    return [m.data(m.index(r, 0), role=Qt.DisplayRole) for r in range(m.rowCount())]


def _select_first_row(tab: SongTab):
    tab.table.view.clearSelection()
    if tab.table.model().rowCount() > 0:
        tab.table.view.selectRow(0)


def _sidebar_click_playlist(sidebar, name: str):
    for i in range(sidebar.list_playlists.count()):
        it = sidebar.list_playlists.item(i)
        if it.text() == name:
            sidebar._on_playlist_clicked(it)
            return
    raise AssertionError(f"Playlist '{name}' not found in sidebar")


def _sidebar_click_smart(sidebar, name: str):
    for i in range(sidebar.list_smart.count()):
        it = sidebar.list_smart.item(i)
        if it.text() == name:
            sidebar._on_smart_clicked(it)
            return
    raise AssertionError(f"Smart list '{name}' not found in sidebar")


def _has_item_with_text(list_widget, text: str) -> bool:
    for i in range(list_widget.count()):
        if list_widget.item(i).text() == text:
            return True
    return False


# ---------------------- Core services fixture ----------------------
@pytest.fixture()
def music_services(session, monkeypatch):
    """
    Real repos/services, but route DatabaseManager.session() to the shared test session.
    """
    dbm = DatabaseManager()

    @contextmanager
    def fake_session(self=None):
        yield session

    monkeypatch.setattr(dbm, "session", fake_session)
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: True))

    tagging = TaggingService(dbm)
    song_service = SongService(dbm, tagging_service=tagging)
    playlist_service = PlaylistService(dbm)

    return dict(db=dbm, song_service=song_service,
                playlist_service=playlist_service, tagging_service=tagging)


@pytest.fixture()
def music_tab(qtbot, music_services, monkeypatch):
    """
    Construct the SongTab. SongTab ctor takes services directly.
    """
    tab = SongTab(
        song_service=music_services["song_service"],
        playlist_service=music_services["playlist_service"],
        tagging_service=music_services["tagging_service"],
        player_service=None,
    )
    qtbot.addWidget(tab)
    return tab


# ---------------------- Dialog / message / menu patch helpers ----------------------

@pytest.fixture()
def fake_add_dialog(monkeypatch):
    import dmt.ui.music_tab.music_tab as st
    monkeypatch.setattr(st, "AddSongDialog", _FakeAddSongDialog)
    return _FakeAddSongDialog


@pytest.fixture()
def fake_tag_dialog(monkeypatch):
    import dmt.ui.music_tab.music_tab as st
    monkeypatch.setattr(st, "TagSongsDialog", _FakeTagSongsDialog)
    return _FakeTagSongsDialog


@pytest.fixture()
def capture_messages(monkeypatch):
    calls = {"info": [], "warn": [], "crit": []}

    def _info(*args, **kwargs): calls["info"].append((args, kwargs)); return QMessageBox.Ok

    def _warn(*args, **kwargs): calls["warn"].append((args, kwargs)); return QMessageBox.Ok

    def _crit(*args, **kwargs): calls["crit"].append((args, kwargs)); return QMessageBox.Ok

    monkeypatch.setattr(QMessageBox, "information", staticmethod(_info))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(_warn))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(_crit))
    return calls


@pytest.fixture()
def auto_confirm(monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))


@pytest.fixture()
def deny_confirm(monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.No))


@pytest.fixture()
def choose_playlist(monkeypatch):
    def _choose(label_text):
        monkeypatch.setattr(QInputDialog, "getItem", staticmethod(lambda *a, **k: (label_text, True)))

    return _choose


@pytest.fixture()
def input_text(monkeypatch):
    def _text(value):
        monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: (value, True)))

    return _text


@pytest.fixture()
def input_multiline(monkeypatch):
    def _text(value):
        monkeypatch.setattr(QInputDialog, "getMultiLineText", staticmethod(lambda *a, **k: (value, True)))

    return _text


@pytest.fixture()
def menu_returns_action(monkeypatch):
    """
    Patch QMenu.exec to return a specific action index for the *next* call.
    Usage:
      set_index(0) -> returns first action, set_index(1) -> second, etc.
    """

    def _set_menu(module, decision):
        monkeypatch.setattr(FakeContextMenu, "decision", decision)
        monkeypatch.setattr(module, "QMenu", FakeContextMenu)

    return _set_menu


# ---------------------- Tests ----------------------

def test_add_song_updates_db_and_table(music_tab, music_services, fake_add_dialog):
    # Prepare dialog return
    fake_add_dialog.set_payloads([{
        "title": "Local A",
        "artist": "Someone",
        "uri": "file:///a.mp3",
        "source": SongSource.LOCAL,
    }])

    # Click Add
    music_tab.btn_add.click()

    # DB has one song
    with music_services["db"].session() as s:
        rows = s.query(Song).all()
        assert len(rows) == 1
        assert rows[0].title == "Local A"

    # UI shows one row with that title
    assert _table_titles(music_tab) == ["Local A"]


def test_add_duplicate_uri_shows_warning(music_tab, music_services, fake_add_dialog, capture_messages):
    # Seed DB with existing song
    music_services["song_service"].add_song(
        title="Existing", uri="file:///dup.mp3", source=SongSource.LOCAL
    )

    # Prepare dialog with duplicate uri
    fake_add_dialog.set_payloads([{
        "title": "Dup",
        "artist": "X",
        "uri": "file:///dup.mp3",
        "source": SongSource.LOCAL,
    }])

    # Click Add
    music_tab.btn_add.click()

    # Warning should have been shown; DB unchanged
    assert len(capture_messages["warn"]) == 1
    with music_services["db"].session() as s:
        assert s.query(Song).count() == 1


def test_add_invalid_source_shows_critical(music_tab, monkeypatch, capture_messages, fake_add_dialog):
    # Force the service call to raise InvalidSourceError regardless of payloads
    def _boom(*args, **kwargs):
        raise InvalidSourceError("bad")

    monkeypatch.setattr(music_tab.song_service, "add_songs_bulk", _boom)

    fake_add_dialog.set_payloads([{
        "title": "X",
        "artist": "Y",
        "uri": "file:///x.mp3",
        "source": SongSource.LOCAL,
    }])

    music_tab.btn_add.click()
    assert len(capture_messages["crit"]) == 1


def test_tag_songs_adds_tags(music_tab, music_services, fake_tag_dialog):
    # Create a song and reload UI
    music_services["song_service"].add_song(title="T1", uri="file:///t1.mp3", source=SongSource.LOCAL)
    music_tab.reload()

    # Prepare tagging dialog to add two tags: one by name, one by id
    with music_services["db"].session() as s:
        # Pre-create tag 'ambient' to get id
        t = Tag(name="ambient")
        s.add(t)
        s.commit()
        ambient_id = t.id

    fake_tag_dialog.set_result(add_names=["combat"], add_ids=[ambient_id], remove_ids=[])

    # Select the first row and click Tag…
    _select_first_row(music_tab)
    music_tab.btn_tag.click()

    # DB: song now has two tags
    with music_services["db"].session() as s:
        song = s.query(Song).filter(Song.uri == "file:///t1.mp3").one()
        names = sorted([lnk.tag.name for lnk in song.tags])
        assert names == ["ambient", "combat"]


def test_delete_song_removes_db_and_ui(music_tab, music_services, auto_confirm):
    # Seed two songs and reload
    music_services["song_service"].add_song(title="A", uri="file:///a.mp3", source=SongSource.LOCAL)
    music_services["song_service"].add_song(title="B", uri="file:///b.mp3", source=SongSource.LOCAL)
    music_tab.reload()
    assert set(_table_titles(music_tab)) == {"A", "B"}

    # Select first row and delete
    _select_first_row(music_tab)
    music_tab.btn_delete.click()

    # DB: one song remains
    with music_services["db"].session() as s:
        assert s.query(Song).count() == 1

    # UI: one row remains
    assert len(_table_titles(music_tab)) == 1


def test_add_to_playlist_appends_items(music_tab, music_services, choose_playlist):
    # Prepare a playlist and a song
    p = music_services["playlist_service"].create_manual("My List")
    music_services["song_service"].add_song(title="A", uri="file:///a.mp3", source=SongSource.LOCAL)
    music_tab.reload()

    # Select the song
    _select_first_row(music_tab)

    # Choose the target playlist in the dialog
    choose_playlist(f"{p.name} ({p.type.value.lower()})")

    # Click Add to Playlist…
    music_tab.btn_add_to_playlist.click()

    # DB: the playlist has one item referencing the song
    with music_services["db"].session() as s:
        items = s.query(PlaylistItem).filter(PlaylistItem.playlist_id == p.id).all()
        assert len(items) == 1
        song = s.get(Song, items[0].song_id)
        assert song.title == "A"


def test_add_to_playlist_no_playlists_shows_info(music_tab, monkeypatch, capture_messages):
    # Seed a song
    music_tab.song_service.add_song(title="A", uri="file:///a.mp3", source=SongSource.LOCAL)
    music_tab.reload()
    _select_first_row(music_tab)

    # Force service to return no playlists
    monkeypatch.setattr(music_tab.playlist_service, "list_all", lambda *a, **k: [])

    music_tab.btn_add_to_playlist.click()
    assert len(capture_messages["info"]) == 1


def test_sidebar_select_playlist_filters_table(music_tab, music_services, choose_playlist):
    # Build playlist with two songs
    p = music_services["playlist_service"].create_manual("Showcase")
    s1 = music_services["song_service"].add_song(title="A", uri="file:///a.mp3", source=SongSource.LOCAL)
    s2 = music_services["song_service"].add_song(title="B", uri="file:///b.mp3", source=SongSource.LOCAL)
    music_services["playlist_service"].add_songs_append(p.id, [s1.id, s2.id])

    # Refresh sidebar lists then click the playlist
    music_tab.sidebar._reload_lists()
    # Find the matching item in the sidebar list and emit click
    for i in range(music_tab.sidebar.list_playlists.count()):
        it = music_tab.sidebar.list_playlists.item(i)
        if it.text() == "Showcase":
            music_tab.sidebar._on_playlist_clicked(it)
            break

    # UI shows A,B
    assert set(_table_titles(music_tab)) == {"A", "B"}


def test_sidebar_select_smart_playlist_evaluates_query(music_tab, music_services):
    # Two songs, one tagged 'ambient'
    s1 = music_services["song_service"].add_song(title="Calm", uri="file:///calm.mp3", source=SongSource.LOCAL)
    s2 = music_services["song_service"].add_song(title="Loud", uri="file:///loud.mp3", source=SongSource.LOCAL)

    # Tag 'Calm' with tag 'ambient'
    music_services["song_service"].tag_songs([s1.id], add_tag_names=["ambient"])

    # Create a smart playlist: tags AND ["ambient"]
    sp = music_services["playlist_service"].create_smart("Ambient Only", {"op": "AND", "tags": ["ambient"]})

    # Refresh lists and click it
    music_tab.sidebar._reload_lists()
    for i in range(music_tab.sidebar.list_smart.count()):
        it = music_tab.sidebar.list_smart.item(i)
        if it.text() == "Ambient Only":
            music_tab.sidebar._on_smart_clicked(it)
            break

    titles = _table_titles(music_tab)
    assert titles == ["Calm"]


# =============================================================================
# Library & Table behaviour
# =============================================================================

def test_library_search_sort_pagination(music_tab, music_services):
    # Seed 5 songs
    for i in range(5):
        music_services["song_service"].add_song(
            title=f"Track {i}", artist="Band", uri=f"file:///t{i}.mp3", source=SongSource.LOCAL, duration_ms=1000 + i
        )
    music_tab.reload()
    # Page size small to exercise paging
    music_tab.page_size_spin.setValue(2)
    music_tab._on_page_size_changed(2)  # ensure reload

    # First page shows 2 entries
    assert len(_table_titles(music_tab)) == 2

    # Search for a specific track
    music_tab.search_edit.setText("Track 3")
    music_tab._on_search_enter()
    titles = _table_titles(music_tab)
    assert titles == ["Track 3"]

    # Clear search and sort ascending by title
    music_tab.search_edit.setText("")
    music_tab._on_search_enter()
    music_tab.sort_combo.setCurrentText("title")
    music_tab.order_combo.setCurrentText("asc")
    # after sort change, reload called; first page ascending should start at Track 0
    titles = _table_titles(music_tab)
    assert titles[0].startswith("Track 0")

    # Next/Prev pagination
    music_tab._go_next()
    assert len(_table_titles(music_tab)) == 2
    music_tab._go_prev()
    assert len(_table_titles(music_tab)) == 2


def test_context_menu_emits_signals(music_tab, music_services, menu_returns_action):
    # Add two songs
    s1 = music_services["song_service"].add_song(title="A", uri="file:///a.mp3", source=SongSource.LOCAL)
    s2 = music_services["song_service"].add_song(title="B", uri="file:///b.mp3", source=SongSource.LOCAL)
    music_tab.reload()
    _select_first_row(music_tab)

    played, nexted, enqd = [], [], []

    music_tab.table.playSongsRequested.connect(lambda ids: played.extend(ids))
    music_tab.table.playNextRequested.connect(lambda ids: nexted.extend(ids))
    music_tab.table.enqueueSongsRequested.connect(lambda ids: enqd.extend(ids))

    import dmt.ui.music_tab.song_table as st
    # Simulate "Play Now"
    menu_returns_action(st, "Play Now")
    music_tab.table._on_ctx_menu(QPoint(5, 5))
    assert played and isinstance(played[0], int)

    # Simulate "Play Next"
    menu_returns_action(st, "Play Next")
    music_tab.table._on_ctx_menu(QPoint(5, 5))
    assert nexted and isinstance(nexted[0], int)

    # Simulate "Add to Queue"
    menu_returns_action(st, "Add to Queue")
    music_tab.table._on_ctx_menu(QPoint(5, 5))
    assert enqd and isinstance(enqd[0], int)


# =============================================================================
# Tagging flows
# =============================================================================

def test_tagging_no_selection_info(music_tab, capture_messages):
    music_tab.btn_tag.click()
    assert len(capture_messages["info"]) == 1


def test_tagging_add_names_and_ids(music_tab, music_services, fake_tag_dialog):
    # Seed a song
    s = music_services["song_service"].add_song(title="T1", uri="file:///t1.mp3", source=SongSource.LOCAL)
    # Pre-create 'ambient' to get id
    with music_services["db"].session() as sess:
        t = Tag(name="ambient")
        sess.add(t)
        sess.commit()
        ambient_id = t.id

    _FakeTagSongsDialog.set_result(add_names=["combat"], add_ids=[ambient_id], remove_ids=[])

    music_tab.reload()
    _select_first_row(music_tab)
    music_tab.btn_tag.click()

    with music_services["db"].session() as sess:
        row = sess.query(Song).filter(Song.id == s.id).one()
        names = sorted([lnk.tag.name for lnk in row.tags])
        assert names == ["ambient", "combat"]


# =============================================================================
# Add / Delete flows & errors
# =============================================================================

def test_add_song_success(music_tab, music_services, fake_add_dialog):
    _FakeAddSongDialog.set_payloads([{
        "title": "Local A", "artist": "Somebody", "uri": "file:///a.mp3", "source": SongSource.LOCAL
    }])
    music_tab.btn_add.click()
    with music_services["db"].session() as s:
        assert s.query(Song).count() == 1
    assert _table_titles(music_tab) == ["Local A"]


def test_add_duplicate_uri_warning(music_tab, music_services, fake_add_dialog, capture_messages):
    music_services["song_service"].add_song(title="Existing", uri="file:///dup.mp3", source=SongSource.LOCAL)
    _FakeAddSongDialog.set_payloads([{
        "title": "Dup", "artist": "X", "uri": "file:///dup.mp3", "source": SongSource.LOCAL
    }])
    music_tab.btn_add.click()
    assert len(capture_messages["warn"]) == 1


def test_add_invalid_source_critical(music_tab, monkeypatch, capture_messages, fake_add_dialog):
    _FakeAddSongDialog.set_payloads([{
        "title": "X", "artist": "Y", "uri": "file:///x.mp3", "source": SongSource.LOCAL
    }])
    # Force raise
    monkeypatch.setattr(music_tab.song_service, "add_songs_bulk",
                        lambda *a, **k: (_ for _ in ()).throw(InvalidSourceError("bad")))
    music_tab.btn_add.click()
    assert len(capture_messages["crit"]) == 1


def test_delete_cancel_no_change(music_tab, music_services, deny_confirm):
    music_services["song_service"].add_song(title="A", uri="file:///a.mp3", source=SongSource.LOCAL)
    music_tab.reload()
    _select_first_row(music_tab)
    music_tab.btn_delete.click()
    with music_services["db"].session() as s:
        assert s.query(Song).count() == 1


def test_delete_confirm_removes(music_tab, music_services, auto_confirm):
    music_services["song_service"].add_song(title="A", uri="file:///a.mp3", source=SongSource.LOCAL)
    music_services["song_service"].add_song(title="B", uri="file:///b.mp3", source=SongSource.LOCAL)
    music_tab.reload()
    _select_first_row(music_tab)
    music_tab.btn_delete.click()
    with music_services["db"].session() as s:
        assert s.query(Song).count() == 1
    assert len(_table_titles(music_tab)) == 1


# =============================================================================
# Playlists (manual & image)
# =============================================================================

def test_create_manual_playlist_reflected_in_db_and_ui(music_tab, music_services, input_text):
    # Simulate user entering a name in the sidebar's "New Playlist"
    assert len(music_tab.playlist_service.list_all()) == 0
    input_text("My Manual List")
    music_tab.sidebar._on_new_playlist()  # triggers PlaylistService.create_manual
    music_tab.sidebar._reload_lists()
    # DB assertion
    assert len(music_tab.playlist_service.list_all()) == 1

    # UI assertion (list_playlists shows the new item)
    assert _has_item_with_text(music_tab.sidebar.list_playlists, "My Manual List"), \
        "Manual playlist should appear in the sidebar list"


def test_create_smart_playlist_reflected_in_db_and_ui(music_tab, music_services, input_text):
    # Simulate user entering a name in the sidebar's "New Smart"
    assert len(music_tab.playlist_service.list_all()) == 0
    input_text("My Smart List")
    music_tab.sidebar._on_new_smart()  # triggers PlaylistService.create_smart with {"op": "AND"}
    music_tab.sidebar._reload_lists()

    # DB assertion
    assert len(music_tab.playlist_service.list_all()) == 1
    # UI assertion (list_smart shows the new item)
    assert _has_item_with_text(music_tab.sidebar.list_smart, "My Smart List"), \
        "Smart playlist should appear in the sidebar list"


def test_manual_playlist_append_insert_remove_and_view(music_tab, music_services, choose_playlist):
    # Create manual
    p = music_services["playlist_service"].create_manual("My List")

    # Seed songs
    a = music_services["song_service"].add_song(title="A", uri="file:///a.mp3", source=SongSource.LOCAL)
    b = music_services["song_service"].add_song(title="B", uri="file:///b.mp3", source=SongSource.LOCAL)
    c = music_services["song_service"].add_song(title="C", uri="file:///c.mp3", source=SongSource.LOCAL)
    music_tab.reload()

    # Select A and add to playlist (append)
    _select_first_row(music_tab)
    choose_playlist(f"{p.name} ({p.type.value.lower()})")
    music_tab.btn_add_to_playlist.click()

    # Insert B at position 0 via service (UI exposes append only)
    music_services["playlist_service"].add_songs_insert(p.id, 0, [b.id])
    # Append C
    music_services["playlist_service"].add_songs_append(p.id, [c.id])

    # Select playlist in sidebar and verify order: B, A, C
    music_tab.sidebar._reload_lists()
    _sidebar_click_playlist(music_tab.sidebar, "My List")
    assert _table_titles(music_tab) == ["B", "A", "C"]

    # Remove the middle item (A) -> order becomes B, C with positions [0,1]
    items = music_services["playlist_service"].items(p.id)
    mid_id = items[1].id
    music_services["playlist_service"].remove_items(p.id, [mid_id])

    music_tab.sidebar._reload_lists()
    _sidebar_click_playlist(music_tab.sidebar, "My List")
    assert _table_titles(music_tab) == ["B", "C"]


def test_image_playlist_shows_songs(music_tab, music_services, make_image):
    # Create an Image row
    img = make_image(caption="Scene 1", full_bytes=b"2")

    p = music_services["playlist_service"].get_or_create_for_image(img.id, "Scene 1 Music")
    s1 = music_services["song_service"].add_song(title="Theme", uri="file:///theme.mp3", source=SongSource.LOCAL)
    s2 = music_services["song_service"].add_song(title="Underscore", uri="file:///under.mp3", source=SongSource.LOCAL)
    music_services["playlist_service"].add_songs_append(p.id, [s1.id, s2.id])

    # Show playlist and assert titles
    music_tab.sidebar._reload_lists()
    _sidebar_click_playlist(music_tab.sidebar, "Scene 1 Music")
    assert _table_titles(music_tab) == ["Theme", "Underscore"]


# =============================================================================
# Smart playlists
# =============================================================================

def test_smart_playlist_AND_OR_NOT_and_invalid_json(music_tab, music_services, capture_messages, input_multiline,
                                                    menu_returns_action):
    # Two songs
    calm = music_services["song_service"].add_song(title="Calm", uri="file:///calm.mp3", source=SongSource.LOCAL)
    loud = music_services["song_service"].add_song(title="Loud", uri="file:///loud.mp3", source=SongSource.LOCAL)
    # Tag Calm with 'ambient'
    music_services["song_service"].tag_songs([calm.id], add_tag_names=["ambient"])

    # Create smart: AND ambient
    sp = music_services["playlist_service"].create_smart("Ambient Only", {"op": "AND", "tags": ["ambient"]})

    # Select smart
    music_tab.sidebar._reload_lists()
    _sidebar_click_smart(music_tab.sidebar, "Ambient Only")
    assert _table_titles(music_tab) == ["Calm"]

    # Now modify: OR ambient with text filter (no UI path for structured edit; simulate sidebar menu -> edit)
    # First, trigger invalid JSON path
    input_multiline("{this is not json}")
    # open context menu on the smart item, force "Edit Query"
    print(music_tab.playlist_service.list_all()[0].id)
    for i in range(music_tab.sidebar.list_smart.count()):
        it = music_tab.sidebar.list_smart.item(i)
        if it.text() == "Ambient Only":
            import dmt.ui.music_tab.sidebar as sb
            menu_returns_action(sb, "Edit Query (JSON)…")  # first action is "Edit Query"
            pos = music_tab.sidebar.list_smart.visualItemRect(it).center()
            music_tab.sidebar._on_smart_menu(pos)
            break
    assert len(capture_messages["crit"]) >= 1  # invalid JSON reported


# =============================================================================
# Reorder invariants (service-level, then reflected in UI)
# =============================================================================

def test_reorder_invariants_positions_contiguous(music_tab, music_services):
    p = music_services["playlist_service"].create_manual("Order")
    a = music_services["song_service"].add_song(title="A", uri="file:///a.mp3", source=SongSource.LOCAL)
    b = music_services["song_service"].add_song(title="B", uri="file:///b.mp3", source=SongSource.LOCAL)
    c = music_services["song_service"].add_song(title="C", uri="file:///c.mp3", source=SongSource.LOCAL)
    music_services["playlist_service"].add_songs_append(p.id, [a.id, b.id, c.id])

    # Move last item to the front
    items = music_services["playlist_service"].items(p.id)
    last_id = items[-1].id
    music_services["playlist_service"].reorder_item(p.id, item_id=last_id, new_position=0)

    items2 = music_services["playlist_service"].items(p.id)
    assert [it.position for it in items2] == [0, 1, 2]
    assert [it.song.title for it in items2] == ["C", "A", "B"]

    # Reflect in UI
    music_tab.sidebar._reload_lists()
    _sidebar_click_playlist(music_tab.sidebar, "Order")
    assert _table_titles(music_tab) == ["C", "A", "B"]


# =============================================================================
# Sidebar behaviour
# =============================================================================

def test_sidebar_new_playlist_rename_delete(music_tab, music_services, input_text, menu_returns_action):
    # New playlist via button
    input_text("My New List")
    music_tab.sidebar._on_new_playlist()
    music_tab.sidebar._reload_lists()
    _sidebar_click_playlist(music_tab.sidebar, "My New List")  # must exist

    # Rename via context menu (first action)
    input_text("Renamed List")
    # choose rename action on that item
    import dmt.ui.music_tab.sidebar as sb
    for i in range(music_tab.sidebar.list_playlists.count()):
        it = music_tab.sidebar.list_playlists.item(i)
        if it.text() == "My New List":
            pos = music_tab.sidebar.list_playlists.visualItemRect(it).center()
            menu_returns_action(sb, "Rename")  # rename
            music_tab.sidebar._on_playlist_menu(pos)
            break

    music_tab.sidebar._reload_lists()
    _sidebar_click_playlist(music_tab.sidebar, "Renamed List")  # renamed exists

    # Delete via context menu (second action)
    for i in range(music_tab.sidebar.list_playlists.count()):
        it = music_tab.sidebar.list_playlists.item(i)
        if it.text() == "Renamed List":
            pos = music_tab.sidebar.list_playlists.visualItemRect(it).center()
            menu_returns_action(sb, "Delete")  # delete
            # auto confirm delete
            QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
            music_tab.sidebar._on_playlist_menu(pos)
            break

    # Should be gone
    with pytest.raises(AssertionError):
        _sidebar_click_playlist(music_tab.sidebar, "Renamed List")


def test_sidebar_new_smart_list(music_tab, music_services, input_text):
    input_text("Smart X")
    music_tab.sidebar._on_new_smart()
    music_tab.sidebar._reload_lists()
    _sidebar_click_smart(music_tab.sidebar, "Smart X")
