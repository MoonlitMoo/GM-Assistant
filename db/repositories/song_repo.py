from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import asc, desc, func, select, or_, literal
from sqlalchemy.orm import Session, joinedload

from db.models import Song, SongSource, Tag, SongTagLink


@dataclass(frozen=True)
class SongFilter:
    text: str | None = None  # matches title/artist/album (ILIKE)
    sources: set[SongSource] | None = None  # filter by sources
    min_duration_ms: int | None = None
    max_duration_ms: int | None = None
    tag_ids_any: set[int] | None = None  # OR semantics
    tag_ids_all: set[int] | None = None  # AND semantics
    tag_ids_not: set[int] | None = None  # NOT semantics


@dataclass(frozen=True)
class SongSort:
    field: str = "date_added"
    desc: bool = True


class SongRepo:
    """Pure data access for Song + tag-based filtering. No business rules here."""

    def create(self, s: Session, *, title: str, uri: str, source: SongSource,
               artist: str | None = None, album: str | None = None, duration_ms: int | None = None) -> Song:
        song = Song(title=title, uri=uri, source=source, artist=artist, album=album, duration_ms=duration_ms)
        s.add(song)
        s.flush()
        return song

    def get(self, s: Session, song_id: int) -> Song | None:
        return s.get(Song, song_id)

    def get_by_uri(self, s: Session, uri: str) -> Song | None:
        return s.execute(
            select(Song).where(Song.uri == uri)
        ).scalars().first()

    def update_fields(self, s: Session, song_id: int, **fields) -> Song | None:
        song = s.get(Song, song_id)
        if not song:
            return None
        for k, v in fields.items():
            if hasattr(song, k):
                setattr(song, k, v)
        s.flush()
        return song

    def delete(self, s: Session, song_id: int) -> bool:
        song = s.get(Song, song_id)
        if not song:
            return False
        s.delete(song)
        s.flush()
        return True

    # ---------- Queries with tag filters ----------

    def list(self, s: Session, *, flt: SongFilter | None = None,
             sort: SongSort | None = None, offset: int = 0, limit: int = 100,
             eager_tags: bool = True) -> tuple[list[Song], int]:
        flt = flt or SongFilter()
        sort = sort or SongSort()

        base = select(Song)
        count_q = select(func.count(literal(1)))

        # Text search (ILIKE)
        if flt.text:
            pat = f"%{flt.text.strip()}%"
            cond = or_(Song.title.ilike(pat), Song.artist.ilike(pat), Song.album.ilike(pat))
            base = base.where(cond)
            count_q = count_q.select_from(Song).where(cond)

        # Source filter
        if flt.sources:
            cond = Song.source.in_(list(flt.sources))
            base = base.where(cond)
            count_q = count_q.where(cond)

        # Duration bounds
        if flt.min_duration_ms is not None:
            cond = Song.duration_ms.is_not(None) & (Song.duration_ms >= flt.min_duration_ms)
            base = base.where(cond)
            count_q = count_q.where(cond)
        if flt.max_duration_ms is not None:
            cond = Song.duration_ms.is_not(None) & (Song.duration_ms <= flt.max_duration_ms)
            base = base.where(cond)
            count_q = count_q.where(cond)

        # Tag OR (ANY)
        if flt.tag_ids_any:
            sub_any = (
                select(SongTagLink.song_id)
                .where(SongTagLink.tag_id.in_(list(flt.tag_ids_any)))
                .subquery()
            )
            cond = Song.id.in_(select(sub_any.c.song_id))
            base = base.where(cond)
            count_q = count_q.where(cond)

        # Tag AND (ALL) — having count = len(all_tags)
        if flt.tag_ids_all:
            all_ids = list(flt.tag_ids_all)
            sub_all = (
                select(SongTagLink.song_id)
                .where(SongTagLink.tag_id.in_(all_ids))
                .group_by(SongTagLink.song_id)
                .having(func.count(func.distinct(SongTagLink.tag_id)) == len(all_ids))
                .subquery()
            )
            cond = Song.id.in_(select(sub_all.c.song_id))
            base = base.where(cond)
            count_q = count_q.where(cond)

        # Tag NOT
        if flt.tag_ids_not:
            sub_not = (
                select(SongTagLink.song_id)
                .where(SongTagLink.tag_id.in_(list(flt.tag_ids_not)))
                .subquery()
            )
            cond = ~Song.id.in_(select(sub_not.c.song_id))
            base = base.where(cond)
            count_q = count_q.where(cond)

        # Sorting
        field_map = {
            "title": Song.title,
            "artist": Song.artist,
            "album": Song.album,
            "date_added": Song.date_added,
            "duration_ms": Song.duration_ms,
            "play_count": Song.play_count,
            "last_played": Song.last_played,
        }
        order_col = field_map.get(sort.field, Song.date_added)
        base = base.order_by(desc(order_col) if sort.desc else asc(order_col))

        # Count first
        total = s.execute(count_q).scalar_one()

        # Eager tags for chip rendering (joinedload on link → tag)
        opt = []
        if eager_tags:
            opt = [joinedload(Song.tags).joinedload(SongTagLink.tag)]

        rows = s.execute(base.options(*opt).offset(offset).limit(limit)).unique().scalars().all()
        return rows, total

    # ---------- Tag read helpers (no mutations) ----------

    def tags_for_song(self, s: Session, song_id: int) -> list[Tag]:
        return s.execute(
            select(Tag).join(SongTagLink, SongTagLink.tag_id == Tag.id).where(SongTagLink.song_id == song_id)
        ).scalars().all()
