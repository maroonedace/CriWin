"""Covers the shared Postgres connection (src.services.db), which the soundboard
repository now depends on."""

from unittest.mock import MagicMock, patch

import pytest

import src.services.db as db
import src.services.soundboard.repository as repo
from src.config import Config


@pytest.fixture(autouse=True)
def _reset_connection_singleton():
    db._connection = None
    yield
    db._connection = None


def test_get_database_connection_passes_config():
    fake_conn = MagicMock()
    fake_conn.closed = False

    with patch("src.services.db.psycopg2.connect", return_value=fake_conn) as mock_connect:
        conn = db.get_database_connection()

    assert conn is fake_conn
    mock_connect.assert_called_once_with(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        database=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        connect_timeout=10,
    )


def test_get_database_connection_is_cached():
    fake_conn = MagicMock()
    fake_conn.closed = False

    with patch("src.services.db.psycopg2.connect", return_value=fake_conn) as mock_connect:
        db.get_database_connection()
        db.get_database_connection()

    mock_connect.assert_called_once()


def test_get_database_connection_reconnects_when_closed():
    closed_conn = MagicMock()
    closed_conn.closed = True
    fresh_conn = MagicMock()
    fresh_conn.closed = False
    db._connection = closed_conn

    with patch("src.services.db.psycopg2.connect", return_value=fresh_conn) as mock_connect:
        conn = db.get_database_connection()

    assert conn is fresh_conn
    mock_connect.assert_called_once()


class TestDatabaseOperations:
    def _conn_with_cursor(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        return conn, cursor

    def test_get_all_sounds_selects_volume_for_one_guild(self):
        conn, cursor = self._conn_with_cursor()
        cursor.fetchall.return_value = [{"name": "a", "file_name": "a.mp3", "volume": 1.0}]

        with (
            patch("src.services.soundboard.repository.get_database_connection", return_value=conn),
            patch.object(repo.SoundCache, "save"),
        ):
            result = repo.DatabaseOperations.get_all_sounds(999)

        sql, params = cursor.execute.call_args.args
        assert "volume" in sql
        assert "WHERE guild_id = %s" in sql
        assert params == (999,)
        assert result == [{"name": "a", "file_name": "a.mp3", "volume": 1.0}]

    def test_add_sound_records_the_guild(self):
        conn, cursor = self._conn_with_cursor()

        with patch("src.services.soundboard.repository.get_database_connection", return_value=conn):
            repo.DatabaseOperations.add_sound(999, "My Sound", "999_boom.mp3")

        sql, params = cursor.execute.call_args.args
        assert "INSERT INTO sounds (guild_id, name, file_name)" in sql
        assert params == (999, "My Sound", "999_boom.mp3")
        conn.commit.assert_called_once()

    def test_delete_sound_is_scoped_to_the_guild(self):
        conn, cursor = self._conn_with_cursor()

        with patch("src.services.soundboard.repository.get_database_connection", return_value=conn):
            repo.DatabaseOperations.delete_sound(999, "My Sound")

        sql, params = cursor.execute.call_args.args
        assert "DELETE FROM sounds WHERE guild_id = %s AND name = %s" in sql
        assert params == (999, "My Sound")
        conn.commit.assert_called_once()

    def test_set_volume_updates_row(self):
        conn, cursor = self._conn_with_cursor()

        with patch("src.services.soundboard.repository.get_database_connection", return_value=conn):
            repo.DatabaseOperations.set_volume(999, "My Sound", 0.5)

        sql, params = cursor.execute.call_args.args
        assert "UPDATE sounds SET volume" in sql
        assert "WHERE guild_id = %s AND name = %s" in sql
        assert params == (0.5, 999, "My Sound")
        conn.commit.assert_called_once()

    def test_rename_updates_row(self):
        conn, cursor = self._conn_with_cursor()

        with patch("src.services.soundboard.repository.get_database_connection", return_value=conn):
            repo.DatabaseOperations.rename_sound(999, "Old", "New")

        sql, params = cursor.execute.call_args.args
        assert "UPDATE sounds SET name" in sql
        assert "WHERE guild_id = %s AND name = %s" in sql
        assert params == ("New", 999, "Old")
        conn.commit.assert_called_once()

    def test_get_panel_returns_row_for_the_guild(self):
        conn, cursor = self._conn_with_cursor()
        cursor.fetchone.return_value = {"channel_id": 999, "message_ids": [1, 2]}

        with patch("src.services.soundboard.repository.get_database_connection", return_value=conn):
            result = repo.DatabaseOperations.get_panel(777)

        sql, params = cursor.execute.call_args.args
        assert "FROM soundboard_panels WHERE guild_id = %s" in sql
        assert params == (777,)
        assert result == {"channel_id": 999, "message_ids": [1, 2]}

    def test_get_panel_returns_none_when_absent(self):
        conn, cursor = self._conn_with_cursor()
        cursor.fetchone.return_value = None

        with patch("src.services.soundboard.repository.get_database_connection", return_value=conn):
            assert repo.DatabaseOperations.get_panel(777) is None

    def test_get_all_panels_returns_every_guild(self):
        conn, cursor = self._conn_with_cursor()
        cursor.fetchall.return_value = [
            {"guild_id": 777, "channel_id": 999, "message_ids": [1]},
            {"guild_id": 888, "channel_id": 111, "message_ids": []},
        ]

        with patch("src.services.soundboard.repository.get_database_connection", return_value=conn):
            result = repo.DatabaseOperations.get_all_panels()

        assert "WHERE" not in cursor.execute.call_args.args[0]
        assert [row["guild_id"] for row in result] == [777, 888]

    def test_save_panel_upserts_per_guild(self):
        conn, cursor = self._conn_with_cursor()

        with patch("src.services.soundboard.repository.get_database_connection", return_value=conn):
            repo.DatabaseOperations.save_panel(777, 999, [1, 2, 3])

        sql, params = cursor.execute.call_args.args
        assert "INSERT INTO soundboard_panels" in sql
        assert "ON CONFLICT (guild_id)" in sql
        assert params == (777, 999, [1, 2, 3])
        conn.commit.assert_called_once()

    def test_get_guilds_returns_rows(self):
        conn, cursor = self._conn_with_cursor()
        cursor.fetchall.return_value = [{"guild_id": 1, "name": "A"}, {"guild_id": 2, "name": "B"}]

        with patch("src.services.soundboard.repository.get_database_connection", return_value=conn):
            result = repo.DatabaseOperations.get_guilds()

        assert result == [{"guild_id": 1, "name": "A"}, {"guild_id": 2, "name": "B"}]

    def test_upsert_guild_refreshes_name(self):
        conn, cursor = self._conn_with_cursor()

        with patch("src.services.soundboard.repository.get_database_connection", return_value=conn):
            repo.DatabaseOperations.upsert_guild(999, "My Server")

        sql, params = cursor.execute.call_args.args
        assert "INSERT INTO guilds" in sql
        assert "ON CONFLICT" in sql
        assert params == (999, "My Server")
        conn.commit.assert_called_once()

    def test_get_access_role_ids(self):
        conn, cursor = self._conn_with_cursor()
        cursor.fetchall.return_value = [(11,), (22,)]

        with patch("src.services.soundboard.repository.get_database_connection", return_value=conn):
            result = repo.DatabaseOperations.get_access_role_ids(999)

        assert result == [11, 22]

    def test_add_access_role_upserts(self):
        conn, cursor = self._conn_with_cursor()

        with patch("src.services.soundboard.repository.get_database_connection", return_value=conn):
            repo.DatabaseOperations.add_access_role(999, 11)

        sql, params = cursor.execute.call_args.args
        assert "INSERT INTO soundboard_access" in sql
        assert "ON CONFLICT" in sql
        assert params == (999, 11)
        conn.commit.assert_called_once()

    def test_remove_access_role_deletes(self):
        conn, cursor = self._conn_with_cursor()

        with patch("src.services.soundboard.repository.get_database_connection", return_value=conn):
            repo.DatabaseOperations.remove_access_role(999, 11)

        sql, params = cursor.execute.call_args.args
        assert "DELETE FROM soundboard_access" in sql
        assert params == (999, 11)
        conn.commit.assert_called_once()
