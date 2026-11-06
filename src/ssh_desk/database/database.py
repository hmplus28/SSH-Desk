"""Database engine, session management and schema migrations (SQLite)."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from ssh_desk.database.models import Base

SCHEMA_VERSION = 1

_MIGRATIONS = {
    1: lambda engine: Base.metadata.create_all(engine),
}


class Database:
    def __init__(self, db_path: Path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{self.path}",
            connect_args={"check_same_thread": False, "timeout": 15},
            pool_pre_ping=True,
        )

        @event.listens_for(self.engine, "connect")
        def _on_connect(dbapi_conn, _record):  # pragma: no cover - driver callback
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA busy_timeout=10000")
            cur.close()

    def init(self) -> None:
        """Create database on first run and apply pending migrations."""
        current = self._read_version()
        for version in sorted(_MIGRATIONS):
            if version > current:
                _MIGRATIONS[version](self.engine)
                self._write_version(version)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def _read_version(self) -> int:
        with self.engine.connect() as conn:
            conn.exec_driver_sql(
                "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
            )
            row = conn.execute(text("SELECT version FROM schema_version LIMIT 1")).fetchone()
            conn.commit()
        return int(row[0]) if row else 0

    def _write_version(self, version: int) -> None:
        with self.engine.begin() as conn:
            conn.exec_driver_sql("DELETE FROM schema_version")
            conn.exec_driver_sql("INSERT INTO schema_version (version) VALUES (?)", (version,))

    @contextmanager
    def session(self):
        session = Session(self.engine, expire_on_commit=False)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def vacuum(self) -> None:  # pragma: no cover - maintenance helper
        raw = sqlite3.connect(str(self.path))
        raw.execute("VACUUM")
        raw.commit()
        raw.close()

    def dispose(self) -> None:
        self.engine.dispose()
