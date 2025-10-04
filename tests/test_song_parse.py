import pytest

from dmt.db.services.song_service import parse_input_link
from dmt.db.models import SongSource


@pytest.mark.parametrize(
    "inp,expect_id",
    [
        ("spotify:track:3n3Ppam7vgaVa1iaRUc9Lp", "3n3Ppam7vgaVa1iaRUc9Lp"),
        ("https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp?si=abc", "3n3Ppam7vgaVa1iaRUc9Lp"),
        ("http://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp", "3n3Ppam7vgaVa1iaRUc9Lp"),
    ],
)
def test_parse_spotify_track_variants(inp, expect_id):
    p = parse_input_link(inp)
    assert p.kind is SongSource.spotify
    assert p.track_id == expect_id


@pytest.mark.parametrize(
    "inp",
    [
        "https://example.com/audio/track.mp3",
        "http://example.org/dir/",
        "example.com/no-scheme",     # treated as URL by fallback
    ],
)
def test_parse_generic_url(inp):
    p = parse_input_link(inp)
    assert p.kind is SongSource.url
    assert p.url is not None


@pytest.mark.parametrize(
    "inp",
    [
        r"file:///C:/music/track.ogg",
        r"C:\absolute\path\track.ogg",
    ],
)
def test_parse_local_paths(inp):
    p = parse_input_link(inp)
    print(p)
    assert p.kind is SongSource.file
    assert p.local_path is not None


def test_parse_edge_cases_fallback_to_url():
    # Something odd but not spotify/local → URL
    p = parse_input_link("mysite.test/resource")
    assert p.kind is SongSource.url
    assert p.url == "mysite.test/resource"
