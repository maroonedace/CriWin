"""Shared fixtures, chiefly the Postgres database the repository tests run against.

These tests use a real database rather than a mocked Session on purpose: the point
of building statements with SQLAlchemy is that it generates the SQL, so only a real
database proves it generates the right SQL. SQLite is not an option either -- the
``message_ids`` column is a Postgres ``BIGINT[]``, which has no SQLite compiler.
"""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import src.services.db as db_module
from src.services.db.models import Base

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql+psycopg2://criwin:criwin@localhost:5432/criwin_test"
)

_TABLES = "sounds, soundboard_panels, guilds, soundboard_access"


@pytest.fixture(scope="session")
def db_engine():
    """Engine for the test database, with the schema created from the models."""
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as error:
        # Locally these tests skip so `make test` works without Docker running. In CI
        # a missing database has to fail loudly, or the whole suite goes green while
        # silently testing nothing.
        if os.getenv("CI"):
            raise
        pytest.skip(f"no test database at {TEST_DATABASE_URL}: {error}")

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(db_engine, monkeypatch):
    """Point ``src.services.db`` at the test engine, and leave the tables empty."""
    monkeypatch.setattr(db_module, "_engine", db_engine)
    monkeypatch.setattr(db_module, "_session_factory", sessionmaker(bind=db_engine))
    yield db_engine
    with db_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE"))
