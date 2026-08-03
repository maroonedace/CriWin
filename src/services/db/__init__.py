"""Shared SQLAlchemy engine and session factory.

Replaces the single cached psycopg2 connection this module used to hand out. An
Engine owns a connection pool, so the admin panel -- whose synchronous ``def``
endpoints FastAPI dispatches onto a worker thread pool -- no longer runs concurrent
requests through one shared connection and transaction.

The driver is still synchronous and still blocks the bot's event loop while a query
runs, exactly as before. Moving to asyncpg would change every call site up through
``src/services/soundboard/service.py``, so it stays out of scope here.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import Config

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def database_url() -> URL:
    """Build the connection URL from ``Config``.

    ``URL.create`` escapes each component, so a password containing ``@``, ``/`` or
    ``%`` cannot corrupt the URL the way string concatenation would. ``Config`` is
    read here rather than at import time so tests can point this at another database.
    """
    return URL.create(
        "postgresql+psycopg2",
        username=Config.DB_USER,
        password=Config.DB_PASSWORD,
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        database=Config.DB_NAME,
    )


def get_engine() -> Engine:
    """Return the process-wide Engine, creating it on first use."""
    global _engine
    if _engine is None:
        try:
            _engine = create_engine(
                database_url(),
                # At most 10 connections per process; the bot and the admin panel are
                # separate processes, so 20 against Postgres's default limit of 100.
                pool_size=5,
                max_overflow=5,
                # Replaces the old "reconnect if conn.closed" check: a connection the
                # server or a firewall dropped is discarded and replaced transparently.
                pool_pre_ping=True,
                pool_recycle=1800,
                connect_args={"connect_timeout": 10},
            )
        except Exception as e:
            raise ValueError(f"Could not connect to the database: {e}") from e
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the process-wide session factory, creating it on first use."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


@contextmanager
def session_scope() -> Iterator[Session]:
    """Yield a Session in a transaction: commits on success, rolls back on failure.

    Note that the commit happens on the way *out* of the block, so callers that
    translate database errors must wrap the ``with`` statement, not its body.
    """
    with get_session_factory().begin() as session:
        yield session
