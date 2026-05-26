"""SQLAlchemy engine + session factory + WAL-mode bootstrap."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from core.config import ensure_data_dirs, settings
from core.store.models import Base

log = logging.getLogger(__name__)


def _build_engine() -> Engine:
    """Construct the SQLAlchemy engine, applying SQLite-specific tuning."""
    ensure_data_dirs()
    url = settings.database_url
    connect_args: dict = {}
    if url.startswith("sqlite"):
        # Without check_same_thread=False, FastAPI's threadpool will choke on
        # session reuse across requests.
        connect_args["check_same_thread"] = False

    eng = create_engine(
        url,
        echo=settings.database_echo,
        connect_args=connect_args,
        future=True,
    )

    if url.startswith("sqlite") and settings.database_wal:
        # WAL prevents lock storms when the eval runner writes concurrently
        # with the API server reading. Apply on every new connection.
        @event.listens_for(eng, "connect")
        def _set_sqlite_pragma(dbapi_connection, _):  # noqa: ANN001
            cur = dbapi_connection.cursor()
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA synchronous=NORMAL;")
            cur.execute("PRAGMA foreign_keys=ON;")
            cur.execute("PRAGMA busy_timeout=5000;")
            cur.close()

    return eng


engine: Engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Create tables if they don't exist. Safe to call repeatedly."""
    Base.metadata.create_all(bind=engine)
    log.info("eval_harness store ready at %s", settings.database_url)


@contextmanager
def get_session() -> Iterator[Session]:
    """Yield a session, committing on success and rolling back on exception.

    Usage:
        with get_session() as s:
            s.add(EvalRun(...))
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
