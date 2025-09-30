from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from typing import Iterator, Optional

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session


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


def _alembic_paths() -> tuple[Path, Path]:
    """Find alembic.ini and migrations dir by walking up from this file."""
    here = Path(__file__).resolve()
    for p in (here, *here.parents):
        ini = p / "alembic.ini"
        mig = p / "dmt" / "db" / "migrations"
        if ini.exists() and mig.exists():
            return ini, mig
    raise RuntimeError("Could not locate alembic.ini and db/migration")


def _alembic_cfg(alembic_ini: Path, migrations_dir: Path, db_url: str) -> Config:
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(migrations_dir))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def _has_table(db_path: Path, table: str) -> bool:
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table,)
        )
        return cur.fetchone() is not None


def _is_empty(db_path: Path) -> bool:
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            "SELECT count(*) FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        return cur.fetchone()[0] == 0


def _backup_db_file(path: Path) -> Path | None:
    """Create a timestamped backup beside the DB. Returns backup path or None."""
    if not path.exists():
        return None
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".bak.{ts}")
    shutil.copy2(path, backup_path)
    return backup_path


def _ensure_upgraded(
        db_path: Path,
        *,
        do_backup: bool = True,
        backup_on_stamp: bool = False,
) -> None:
    """Ensure SQLite DB at db_path is migrated to Alembic 'head'.

    - No backup if already at head.
    - No backup when stamping unversioned DBs (unless backup_on_stamp=True).
    - Backup only when a real upgrade will run.
    """
    alembic_ini, migrations_dir = _alembic_paths()
    db_url = _sqlite_url(db_path)
    cfg = _alembic_cfg(alembic_ini, migrations_dir, db_url)
    script = ScriptDirectory.from_config(cfg)

    # Brand-new or empty → just build schema (no prior file to back up meaningfully)
    if not db_path.exists() or _is_empty(db_path):
        command.upgrade(cfg, "head")
        return

    # Figure out current revision (None if unversioned)
    engine = create_engine(db_url, future=True)
    try:
        with engine.connect() as conn:
            mc = MigrationContext.configure(conn)
            current_rev = mc.get_current_revision()
    finally:
        engine.dispose()

    heads = set(script.get_heads())  # usually one item

    if current_rev is None:
        # Existing but unversioned → assume schema ≈ initial; stamp to head
        if do_backup and backup_on_stamp:
            _backup_db_file(db_path)
        # Ensure version table path is set up in some envs, then stamp
        command.upgrade(cfg, "+0")
        command.stamp(cfg, "head")
        return

    if current_rev in heads:
        # Already at head → nothing to do (and no backup)
        return

    # Behind → backup then upgrade to head
    if do_backup:
        _backup_db_file(db_path)
    command.upgrade(cfg, "head")


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

        # Always ensure schema is current before Engine/Session creation.
        if create_if_missing or path.exists():
            _ensure_upgraded(path, do_backup=True)

        url = _sqlite_url(path)
        engine = create_engine(url, future=True)
        _apply_sqlite_pragmas(engine)

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
