from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _sqlite_url(path: Path) -> str:
    p = path.resolve()
    return f"sqlite:///{p.as_posix()}"


def _apply_sqlite_pragmas(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_conn, conn_rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")
        cur.execute("PRAGMA journal_mode = WAL;")
        cur.execute("PRAGMA synchronous = NORMAL;")
        cur.execute("PRAGMA temp_store = MEMORY;")
        cur.execute("PRAGMA mmap_size = 134217728;")  # 128MB
        cur.close()


class DatabaseManager:
    """
    Holds the current SQLAlchemy engine and session factory for the app.
    Call .open(path) at startup or when user chooses a file.
    """

    def __init__(self) -> None:
        self._engine: Optional[Engine] = None
        self._Session: Optional[sessionmaker[Session]] = None
        self._path: Optional[Path] = None

    @property
    def path(self) -> Optional[Path]:
        return self._path

    def open(self, path: Path, *, create_if_missing: bool = True) -> None:
        _ensure_parent_dir(path)
        need_create = create_if_missing and not path.exists()

        url = _sqlite_url(path)
        engine = create_engine(url, future=True)
        _apply_sqlite_pragmas(engine)

        if need_create:
            Base.metadata.create_all(engine)

        # Swap in atomically
        self._engine = engine
        self._Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
        self._path = path

    def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
        self._engine = None
        self._Session = None
        self._path = None

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Context-managed session for transactional work."""
        if self._Session is None:
            raise RuntimeError("Database not opened. Call DatabaseManager.open() first.")
        s = self._Session()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()
