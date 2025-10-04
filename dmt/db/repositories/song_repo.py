from __future__ import annotations
from typing import Iterable, Optional

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from dmt.db.models import Song, SongSource


class SongRepo:
    """Data-access for Song and tag links."""

    def __init__(self, session: Session):
        self.s = session

    # ---------- lookups ----------
    def get_by_id(self, song_id: int) -> Optional[Song]:
        return self.s.get(Song, song_id)

    def get_by_source_id(self, source: SongSource, source_id: str) -> Optional[Song]:
        if source_id is None:
            return None
        return self.s.execute(
            select(Song).where(and_(Song.source == source, Song.source_id == source_id))
        ).scalar_one_or_none()

    def get_by_local_path(self, path: str) -> Optional[Song]:
        return self.s.execute(
            select(Song).where(and_(Song.source == SongSource.file, Song.local_path == path))
        ).scalar_one_or_none()

    # ---------- upsert ----------
    def upsert(
        self,
        *,
        source: SongSource,
        source_id: Optional[str],
        title: str,
        artist: str,
        album: Optional[str] = None,
        source_url: Optional[str] = None,
        duration_ms: Optional[int] = None,
        local_path: Optional[str] = None,
    ) -> Song:
        """
        Upsert by (source, source_id) when source_id is present.
        For local files (source=file) with no source_id, we try to de-dup by local_path.
        """
        obj: Optional[Song] = None
        if source_id:
            obj = self.get_by_source_id(source, source_id)
        elif source == SongSource.file and local_path:
            obj = self.get_by_local_path(local_path)

        if obj is None:
            obj = Song(
                title=title,
                artist=artist,
                album=album,
                source=source,
                source_id=source_id,
                source_url=source_url,
                duration_ms=duration_ms,
                local_path=local_path,
            )
            self.s.add(obj)
        else:
            obj.title = title
            obj.artist = artist
            obj.album = album
            obj.source_url = source_url
            obj.duration_ms = duration_ms
            if source == SongSource.file:
                obj.local_path = local_path

        return obj

    # ---------- tags ----------
    def set_tags(self, song: Song, tag_ids: Iterable[int]) -> None:
        """Replace tags with the given set (idempotent)."""
        wanted = set(tag_ids)
        current = {st.tag_id for st in song.tags}
        # remove
        for st in list(song.tags):
            if st.tag_id not in wanted:
                song.tags.remove(st)
        # add
        missing = wanted - current
        if missing:
            from dmt.db.models import SongTagLink
            for tid in missing:
                song.tags.append(SongTagLink(song_id=song.id, tag_id=tid))
