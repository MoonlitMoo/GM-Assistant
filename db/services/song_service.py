from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from db.models import Song, SongSource, SongTagLink, Playlist, PlaylistType, PlaylistItem
from db.repositories.playlist_repo import PlaylistRepo
from db.repositories.song_repo import SongRepo, SongFilter, SongSort
from db.repositories.tag_repo import TagRepo


@dataclass(frozen=True)
class LibraryQuery:
    text: str | None = None
    sources: set[SongSource] | None = None
    tag_any: list[int] | None = None
    tag_all: list[int] | None = None
    tag_not: list[int] | None = None
    min_duration_ms: int | None = None
    max_duration_ms: int | None = None
    sort_field: str = "date_added"
    sort_desc: bool = True
    page: int = 0
    page_size: int = 100


class DuplicateUriError(Exception):
    ...


class InvalidSourceError(Exception):
    ...


class SongService:
    """
    Service with per-call session management.
    Pass in a DB manager that exposes `session()` → context manager yielding a Session,
    e.g. `with self.db.session() as s: ...`.
    """

    def __init__(self, db, tagging_service: Optional[object] = None):
        self.db = db
        self.song_repo = SongRepo()
        self.tag_repo = TagRepo()
        self.tagging = tagging_service

    # ---------- Read ----------
    def get(self, song_id: int):
        with self.db.session() as s:
            return self.song_repo.get(s, song_id)

    # ---------- Ingestion / Mutations (own session + commit) ----------
    def add_song(
        self,
        *,
        title: str,
        uri: str,
        source: SongSource,
        artist: str | None = None,
        album: str | None = None,
        duration_ms: int | None = None,
        tag_names: list[str] | None = None,
        tag_ids: list[int] | None = None,
    ) -> Song:
        if source not in (SongSource.LOCAL, SongSource.SPOTIFY, SongSource.YOUTUBE):
            raise InvalidSourceError(str(source))

        with self.db.session() as s:  # type: Session
            existing = self.song_repo.get_by_uri(s, uri)
            if existing:
                raise DuplicateUriError(uri)

            song = self.song_repo.create(
                s, title=title, uri=uri, source=source, artist=artist, album=album, duration_ms=duration_ms
            )

            ids: list[int] = []
            if tag_names:
                ids.extend(self.tag_repo.get_ids_by_names(s, tag_names, ensure=True))
            if tag_ids:
                ids.extend(tag_ids)
            if ids:
                ids = sorted(set(ids))
                if self.tagging and hasattr(self.tagging, "attach_tags_to_song_ids"):
                    self.tagging.attach_tags_to_song_ids(s, song.id, ids)
                else:
                    existing_pairs = {link.tag_id for link in song.tags}
                    for tid in ids:
                        if tid not in existing_pairs:
                            s.add(SongTagLink(song_id=song.id, tag_id=tid))

            s.commit()
            # Make a safe, detached instance for the caller
            s.refresh(song)
            s.expunge(song)
            return song

    def add_songs_bulk(self, payloads: Iterable[dict]) -> list[Song]:
        out: list[Song] = []
        for p in payloads:
            out.append(self.add_song(**p))
        return out

    def update_song(self, song_id: int, **fields) -> Song | None:
        with self.db.session() as s:
            if "uri" in fields:
                new_uri = fields["uri"]
                other = self.song_repo.get_by_uri(s, new_uri)
                if other and other.id != song_id:
                    raise DuplicateUriError(new_uri)

            song = self.song_repo.update_fields(s, song_id, **fields)
            s.commit()
            if song:
                s.refresh(song)
                s.expunge(song)
            return song

    def delete_song(self, song_id: int) -> bool:
        with self.db.session() as s:
            ok = self.song_repo.delete(s, song_id)
            s.commit()
            return ok

    def tag_songs(
        self,
        song_ids: list[int],
        *,
        add_tag_names: list[str] | None = None,
        add_tag_ids: list[int] | None = None,
        remove_tag_ids: list[int] | None = None,
    ) -> None:
        with self.db.session() as s:
            if self.tagging and hasattr(self.tagging, "bulk_update_song_tags"):
                self.tagging.bulk_update_song_tags(
                    s,
                    song_ids,
                    add_tag_names=add_tag_names,
                    add_tag_ids=add_tag_ids,
                    remove_tag_ids=remove_tag_ids,
                )
                s.commit()
                return

            ids_to_add: list[int] = []
            if add_tag_names:
                ids_to_add.extend(self.tag_repo.get_ids_by_names(s, add_tag_names, ensure=True))
            if add_tag_ids:
                ids_to_add.extend(add_tag_ids)
            ids_to_add = sorted(set(ids_to_add))

            if ids_to_add:
                for sid in song_ids:
                    existing = {t.tag_id for t in s.query(SongTagLink).filter(SongTagLink.song_id == sid).all()}
                    for tid in ids_to_add:
                        if tid not in existing:
                            s.add(SongTagLink(song_id=sid, tag_id=tid))

            if remove_tag_ids:
                s.query(SongTagLink).filter(
                    SongTagLink.song_id.in_(song_ids), SongTagLink.tag_id.in_(remove_tag_ids)
                ).delete(synchronize_session=False)

            s.commit()

    # ---------- Library Browse (own session, no commit) ----------

    def browse(self, q: LibraryQuery) -> tuple[list[Song], int]:
        flt = SongFilter(
            text=q.text,
            sources=q.sources,
            min_duration_ms=q.min_duration_ms,
            max_duration_ms=q.max_duration_ms,
            tag_ids_any=set(q.tag_any or []),
            tag_ids_all=set(q.tag_all or []),
            tag_ids_not=set(q.tag_not or []),
        )
        sort = SongSort(field=q.sort_field, desc=q.sort_desc)
        offset = max(0, q.page) * max(1, q.page_size)

        with self.db.session() as s:
            rows, total = self.song_repo.list(
                s, flt=flt, sort=sort, offset=offset, limit=q.page_size, eager_tags=True
            )
            # Detach to avoid stale session issues in UI
            for obj in rows:
                s.expunge(obj)
            return rows, total

    # ---------- Analytics (own session + commit) ----------

    def record_play_progress(self, *, song_id: int, played_ms: int, completion_threshold: float = 0.5) -> None:
        with self.db.session() as s:
            song = self.song_repo.get(s, song_id)
            if not song or not song.duration_ms:
                return
            if played_ms >= int(song.duration_ms * completion_threshold):
                song.play_count = (song.play_count or 0) + 1
                from datetime import datetime, timezone

                # store naive UTC (align with your TimestampMixin usage)
                song.last_played = datetime.now(timezone.utc).replace(tzinfo=None)
                s.commit()


class InvalidPlaylistError(Exception):
    ...


class InvalidSmartQueryError(Exception):
    ...


class PlaylistService:
    """
    Service with per-call session management.
    Pass a DB manager exposing `session()` → context manager yielding Session.
    """

    def __init__(self, db):
        self.db = db
        self.pl = PlaylistRepo()
        self.songs = SongRepo()
        self.tags = TagRepo()

    # ---------- Read ----------
    def get(self, p_id: int):
        with self.db.session() as s:
            return self.pl.get(s, p_id)

    # ---------- Manual playlists (own session + commit where needed) ----------
    def create_manual(self, name: str) -> Playlist:
        with self.db.session() as s:  # type: Session
            p = self.pl.create(s, name=name, type_=PlaylistType.MANUAL)
            s.commit()
            s.refresh(p)
            s.expunge(p)
            return p

    def rename(self, playlist_id: int, name: str) -> Playlist | None:
        with self.db.session() as s:
            p = self.pl.update(s, playlist_id, name=name)
            s.commit()
            if p:
                s.refresh(p)
                s.expunge(p)
            return p

    def delete(self, playlist_id: int) -> bool:
        with self.db.session() as s:
            ok = self.pl.delete(s, playlist_id)
            s.commit()
            return ok

    def add_songs_append(self, playlist_id: int, song_ids: Iterable[int]) -> list[PlaylistItem]:
        with self.db.session() as s:
            items = self.pl.append(s, playlist_id, song_ids)
            s.commit()
            for it in items:
                s.refresh(it)
                s.expunge(it)
            return items

    def add_songs_insert(self, playlist_id: int, position: int, song_ids: Iterable[int]) -> list[PlaylistItem]:
        with self.db.session() as s:
            items = self.pl.insert_at(s, playlist_id, position, song_ids)
            s.commit()
            for it in items:
                s.refresh(it)
                s.expunge(it)
            return items

    def reorder_item(self, playlist_id: int, item_id: int, new_position: int) -> None:
        with self.db.session() as s:
            self.pl.reorder(s, playlist_id, item_id=item_id, new_position=new_position)
            s.commit()

    def remove_items(self, playlist_id: int, item_ids: Iterable[int]) -> int:
        with self.db.session() as s:
            count = self.pl.remove_items(s, playlist_id, item_ids)
            s.commit()
            return count

    def remove_songs(self, playlist_id: int, song_ids: Iterable[int]) -> int:
        with self.db.session() as s:
            count = self.pl.remove_songs(s, playlist_id, song_ids)
            s.commit()
            return count

    def items(self, playlist_id: int) -> list[PlaylistItem]:
        with self.db.session() as s:
            rows = self.pl.items(s, playlist_id)
            for it in rows:
                # detach nested song objects as well
                if it.song:
                    s.expunge(it.song)
                s.expunge(it)
            return rows

    def list_all(self):
        with self.db.session() as s:
            return self.pl.list_all(s)

    # ---------- Image playlists ----------

    def get_or_create_for_image(self, image_id: int, name: Optional[str] = None) -> Playlist:
        with self.db.session() as s:
            p = self.pl.get_or_create_image_playlist(s, image_id=image_id, name=name)
            # If it was created, it will be pending in the session; commit either way for a stable return.
            s.commit()
            s.refresh(p)
            s.expunge(p)
            return p

    # ---------- Smart playlists ----------

    def create_smart(self, name: str, query: dict) -> Playlist:
        self._validate_smart_query(query)
        with self.db.session() as s:
            p = self.pl.create(s, name=name, type_=PlaylistType.SMART, query=query)
            s.commit()
            s.refresh(p)
            s.expunge(p)
            return p

    def update_smart_query(self, playlist_id: int, query: dict) -> Playlist | None:
        self._validate_smart_query(query)
        with self.db.session() as s:
            p = self.pl.update(s, playlist_id, query=query)
            s.commit()
            if p:
                s.refresh(p)
                s.expunge(p)
            return p

    def evaluate_smart(
        self,
        playlist_id: int,
        *,
        page: int = 0,
        page_size: int = 100,
        sort_field: str = "title",
        sort_desc: bool = False,
    ) -> tuple[list[Song], int]:
        with self.db.session() as s:
            p = self.pl.get(s, playlist_id)
            if not p or p.type != PlaylistType.SMART or not p.query:
                raise InvalidPlaylistError("Not a smart playlist or missing query")

            q = p.query or {}
            op = (q.get("op") or "AND").upper()
            if op not in ("AND", "OR"):
                raise InvalidSmartQueryError("op must be AND or OR")

            # Resolve tag sets (tags: ALL; any: ANY; not: NOT)
            def resolve_ids(maybe_ids_or_names) -> list[int]:
                if not maybe_ids_or_names:
                    return []
                ints = [t for t in maybe_ids_or_names if isinstance(t, int)]
                names = [t for t in maybe_ids_or_names if isinstance(t, str)]
                if names:
                    ints.extend(self.tags.get_ids_by_names(s, names, ensure=False))
                # unique
                return list({*ints})

            tags_all = resolve_ids(q.get("tags"))       # treated as ALL
            tags_any = resolve_ids(q.get("any"))        # optional ANY
            tags_not = resolve_ids(q.get("not"))

            src = q.get("source")
            sources = None
            if isinstance(src, list) and src:
                from db.models.song import SongSource
                mapping = {
                    "local": SongSource.LOCAL,
                    "spotify": SongSource.SPOTIFY,
                    "youtube": SongSource.YOUTUBE,
                }
                sources = {mapping[x.lower()] for x in src if isinstance(x, str) and x.lower() in mapping}

            text = q.get("text")

            flt = SongFilter(
                text=text,
                sources=sources,
                tag_ids_any=set(tags_any) if op == "OR" else None,
                tag_ids_all=set(tags_all) if op == "AND" else None,
                tag_ids_not=set(tags_not),
            )
            sort = SongSort(field=sort_field, desc=sort_desc)
            offset = max(0, page) * max(1, page_size)

            rows, total = self.songs.list(s, flt=flt, sort=sort, offset=offset, limit=page_size, eager_tags=True)
            for obj in rows:
                s.expunge(obj)
            return rows, total

    # ---------- Validation ----------

    def _validate_smart_query(self, q: dict) -> None:
        if not isinstance(q, dict):
            raise InvalidSmartQueryError("query must be an object")
        op = (q.get("op") or "AND").upper()
        if op not in ("AND", "OR"):
            raise InvalidSmartQueryError("op must be AND or OR")
        for key in ("tags", "any", "not"):
            if key in q and not isinstance(q[key], list):
                raise InvalidSmartQueryError(f"{key} must be a list")
