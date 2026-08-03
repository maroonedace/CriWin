"""Covers the Alembic migrations and the pre-Alembic baselining path.

The legacy-baseline test is the one that matters on deploy day: it is the only
automated proof that an existing production database survives the switch from
init.sql to Alembic with its rows intact.

Each test gets its own scratch database, because migrations run DDL against a whole
database and Alembic tracks state in a table it creates itself.
"""

import os
from contextlib import contextmanager
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config as AlembicConfig
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, make_url, text

import src.services.db as db_module
from src.services.db import migrate
from src.services.db.models import Base
from tests.conftest import TEST_DATABASE_URL

LEGACY_INIT_SQL = Path(__file__).parent / "fixtures" / "legacy_init.sql"
ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def _admin_engine():
    """Engine on the 'postgres' database, for CREATE/DROP DATABASE."""
    url = make_url(TEST_DATABASE_URL).set(database="postgres")
    return create_engine(url, isolation_level="AUTOCOMMIT")


@contextmanager
def scratch_database(name: str):
    """Yield an engine for a freshly created database, dropping it afterwards."""
    admin = _admin_engine()
    try:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
            connection.execute(text(f'CREATE DATABASE "{name}"'))

        engine = create_engine(make_url(TEST_DATABASE_URL).set(database=name))
        try:
            yield engine
        finally:
            engine.dispose()

        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    finally:
        admin.dispose()


@pytest.fixture
def scratch(request, db_engine, monkeypatch):
    """A scratch database with src.services.db pointed at it.

    Depends on db_engine so an unreachable Postgres skips (or, in CI, fails) here the
    same way it does for the repository tests.
    """
    name = f"criwin_mig_{abs(hash(request.node.name)) % 100000}"
    with scratch_database(name) as engine:
        monkeypatch.setattr(db_module, "_engine", engine)
        monkeypatch.setattr(db_module, "_session_factory", None)
        yield engine


def _alembic_config() -> AlembicConfig:
    return AlembicConfig(str(ALEMBIC_INI))


def _metadata_diff(engine) -> list:
    """Differences between the live schema and the models. Empty means in sync."""
    with engine.connect() as connection:
        return compare_metadata(MigrationContext.configure(connection), Base.metadata)


def _table_names(engine) -> set[str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        return {row[0] for row in rows}


def _current_revision(engine) -> str | None:
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def _apply_legacy_init_sql(engine) -> None:
    """Build the schema the way the retired init.sql did, via the Postgres entrypoint."""
    script = LEGACY_INIT_SQL.read_text()
    with engine.begin() as connection:
        connection.execute(text(script))


class TestFreshDatabase:
    def test_upgrade_head_matches_the_models(self, scratch):
        """The migrations and the models must not drift apart.

        This is what stops someone editing a model and shipping without generating a
        migration: the next autogenerate would silently carry their change along.
        """
        command.upgrade(_alembic_config(), "head")

        assert _metadata_diff(scratch) == []

    def test_upgrade_creates_every_table(self, scratch):
        command.upgrade(_alembic_config(), "head")

        assert {"sounds", "soundboard_panels", "guilds", "soundboard_access"} <= _table_names(
            scratch
        )

    def test_initial_revision_is_reversible(self, scratch):
        command.upgrade(_alembic_config(), "head")
        command.downgrade(_alembic_config(), "base")

        remaining = _table_names(scratch)
        assert "sounds" not in remaining
        assert "guilds" not in remaining


class TestLegacyBaselining:
    def test_needs_baseline_is_false_for_an_empty_database(self, scratch):
        assert migrate.needs_baseline() is False

    def test_needs_baseline_is_true_for_an_init_sql_database(self, scratch):
        _apply_legacy_init_sql(scratch)

        assert migrate.needs_baseline() is True

    def test_needs_baseline_is_false_once_alembic_has_run(self, scratch):
        command.upgrade(_alembic_config(), "head")

        assert migrate.needs_baseline() is False

    def test_existing_database_is_stamped_and_upgraded_without_data_loss(self, scratch):
        """The deploy-day path: a database built by init.sql, carrying real rows."""
        _apply_legacy_init_sql(scratch)
        with scratch.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO sounds (guild_id, name, file_name) "
                    "VALUES (999, 'Boom', '999_boom.mp3')"
                )
            )

        migrate.main()

        with scratch.begin() as connection:
            row = connection.execute(text("SELECT guild_id, name, volume FROM sounds")).one()
        assert row == (999, "Boom", 1.0)
        assert _current_revision(scratch) == "0002"
        assert _metadata_diff(scratch) == []

    def test_legacy_single_row_panel_table_is_dropped(self, scratch):
        _apply_legacy_init_sql(scratch)
        with scratch.begin() as connection:
            connection.execute(text("CREATE TABLE soundboard_panel (channel_id BIGINT)"))

        migrate.main()

        assert "soundboard_panel" not in _table_names(scratch)

    def test_pre_guild_scoping_database_is_reconciled(self, scratch):
        """A database old enough to predate the volume and guild_id columns.

        Stamping at 0001 assumes the legacy database already has 0001's shape. One
        this old does not, which is what revision 0002 exists to fix.
        """
        with scratch.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE sounds ("
                    "  id SERIAL PRIMARY KEY,"
                    "  name VARCHAR(255) NOT NULL UNIQUE,"
                    "  file_name VARCHAR(255) NOT NULL,"
                    "  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
                )
            )
            connection.execute(
                text("INSERT INTO sounds (name, file_name) VALUES ('Old', 'old.mp3')")
            )
            # The other three tables arrived with later init.sql edits.
            connection.execute(
                text(
                    "CREATE TABLE guilds ("
                    "  guild_id BIGINT PRIMARY KEY,"
                    "  name VARCHAR(255) NOT NULL,"
                    "  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
                )
            )
            connection.execute(
                text(
                    "CREATE TABLE soundboard_panels ("
                    "  guild_id BIGINT PRIMARY KEY,"
                    "  channel_id BIGINT NOT NULL,"
                    "  message_ids BIGINT[] NOT NULL DEFAULT '{}',"
                    "  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
                )
            )
            connection.execute(
                text(
                    "CREATE TABLE soundboard_access ("
                    "  guild_id BIGINT NOT NULL,"
                    "  role_id BIGINT NOT NULL,"
                    "  PRIMARY KEY (guild_id, role_id))"
                )
            )

        migrate.main()

        with scratch.begin() as connection:
            row = connection.execute(text("SELECT guild_id, volume FROM sounds")).one()
        # Rows predating guild scoping land in guild 0; pointing them at a real guild
        # is a documented manual step, not something a migration should guess at.
        assert row == (0, 1.0)
        assert _metadata_diff(scratch) == []

    def test_running_twice_is_a_no_op(self, scratch):
        _apply_legacy_init_sql(scratch)

        migrate.main()
        migrate.main()

        assert _current_revision(scratch) == "0002"
        assert _metadata_diff(scratch) == []


class TestAlembicIni:
    def test_does_not_hardcode_a_database_url(self):
        """The URL comes from Config via env.py, so a '%' in a password is safe."""
        assert _alembic_config().get_main_option("sqlalchemy.url") is None

    def test_ini_is_shipped_next_to_the_package(self):
        assert migrate.ALEMBIC_INI == ALEMBIC_INI
        assert os.path.exists(migrate.ALEMBIC_INI)
