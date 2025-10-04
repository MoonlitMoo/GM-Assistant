from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol
from urllib.parse import urlparse
import re
import os

from sqlalchemy.orm import Session

from dmt.db.models import Song, SongSource
from dmt.db.repositories import SongRepo


# ---------- Provider seam----------
@dataclass
class SpotifyTrackMeta:
    track_id: str
    title: str
    artist: str          # flattened "A, B feat. C" is fine
    album: Optional[str]
    duration_ms: Optional[int]
    open_url: Optional[str]


class SpotifyProvider(Protocol):
    """Abstract provider the service can call to resolve a Spotify link/URI."""
    def fetch_track(self, track_id: str) -> SpotifyTrackMeta:
        ...


# ---------- Link parsing ----------
_SPOTIFY_URL_RE = re.compile(r"open\.spotify\.com/track/([A-Za-z0-9]+)")
_SPOTIFY_URI_RE = re.compile(r"^spotify:track:([A-Za-z0-9]+)$")


@dataclass
class ParsedLink:
    kind: SongSource
    track_id: Optional[str] = None
    local_path: Optional[str] = None
    url: Optional[str] = None


def parse_input_link(link: str) -> ParsedLink:
    link = link.strip()

    # Spotify URI
    m = _SPOTIFY_URI_RE.match(link)
    if m:
        return ParsedLink(kind=SongSource.spotify, track_id=m.group(1))

    # Spotify open URL
    m = _SPOTIFY_URL_RE.search(link)
    if m:
        return ParsedLink(kind=SongSource.spotify, track_id=m.group(1))

    # Generic URL?
    pu = urlparse(link)
    if pu.scheme in {"http", "https"}:
        return ParsedLink(kind=SongSource.url, url=link)

    # Local file (absolute path or file://)
    if pu.scheme == "file":
        p = Path(pu.path)
        return ParsedLink(kind=SongSource.file, local_path=str(p))
    if os.path.isabs(link) or Path(link).exists():
        return ParsedLink(kind=SongSource.file, local_path=str(Path(link)))

    # Fallback: treat as URL (lets user paste bare domains)
    return ParsedLink(kind=SongSource.url, url=link)


# ---------- Service ----------
class SongService:
    """
    Orchestrates parsing links and creating/updating Song rows.
    Designed for DI: pass DatabaseManager with .session(), and optional SpotifyProvider.
    """

    def __init__(self, db_manager, spotify: Optional[SpotifyProvider] = None):
        self.db = db_manager
        self.spotify = spotify

    # Public API --------------------------------------------------------------
    def add_from_link(self, link: str, tag_ids: Optional[list[int]] = None) -> Song:
        """
        Parse the link, resolve metadata (via provider if Spotify), and upsert a Song.
        Returns the Song row.
        """
        parsed = parse_input_link(link)
        tag_ids = tag_ids or []

        with self.db.session() as s:  # type: Session
            repo = SongRepo(s)

            if parsed.kind is SongSource.spotify:
                if not parsed.track_id:
                    raise ValueError("Invalid Spotify link/URI (no track id).")
                # Provider required for proper metadata
                if not self.spotify:
                    raise RuntimeError("Spotify provider not configured.")
                meta = self.spotify.fetch_track(parsed.track_id)
                song = repo.upsert(
                    source=SongSource.spotify,
                    source_id=meta.track_id,
                    title=meta.title or "Unknown Title",
                    artist=meta.artist or "Unknown Artist",
                    album=meta.album,
                    source_url=meta.open_url,
                    duration_ms=meta.duration_ms,
                )

            elif parsed.kind is SongSource.file:
                if not parsed.local_path:
                    raise ValueError("Local path missing.")
                p = Path(parsed.local_path)
                if not p.exists():
                    raise FileNotFoundError(f"File not found: {p}")
                title = p.stem
                song = repo.upsert(
                    source=SongSource.file,
                    source_id=None,
                    title=title,
                    artist="",
                    album=None,
                    source_url=None,
                    duration_ms=None,   # optional: probe later with a media lib
                    local_path=str(p),
                )

            elif parsed.kind is SongSource.url:
                # Minimal record from generic URL; title = last path segment or host
                pu = urlparse(parsed.url or "")
                title = (Path(pu.path).name or pu.netloc or parsed.url or "").strip() or "Link"
                song = repo.upsert(
                    source=SongSource.url,
                    source_id=None,
                    title=title,
                    artist="",
                    album=None,
                    source_url=parsed.url,
                    duration_ms=None,
                )

            else:
                raise ValueError(f"Unsupported link type: {parsed.kind}")

            # Tags
            if tag_ids:
                # If Song is new, it may not have id yet; flush to assign PK
                s.flush()
                repo.set_tags(song, tag_ids)

            s.commit()
            return song
