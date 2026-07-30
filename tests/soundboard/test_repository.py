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

    def test_get_all_sounds_selects_volume(self):
        conn, cursor = self._conn_with_cursor()
        cursor.fetchall.return_value = [{"name": "a", "file_name": "a.mp3", "volume": 1.0}]

        with (
            patch("src.services.soundboard.repository.get_database_connection", return_value=conn),
            patch.object(repo.SoundCache, "save"),
        ):
            result = repo.DatabaseOperations.get_all_sounds()

        assert "volume" in cursor.execute.call_args.args[0]
        assert result == [{"name": "a", "file_name": "a.mp3", "volume": 1.0}]

    def test_set_volume_updates_row(self):
        conn, cursor = self._conn_with_cursor()

        with patch("src.services.soundboard.repository.get_database_connection", return_value=conn):
            repo.DatabaseOperations.set_volume("My Sound", 0.5)

        sql, params = cursor.execute.call_args.args
        assert "UPDATE sounds SET volume" in sql
        assert params == (0.5, "My Sound")
        conn.commit.assert_called_once()

    def test_rename_updates_row(self):
        conn, cursor = self._conn_with_cursor()

        with patch("src.services.soundboard.repository.get_database_connection", return_value=conn):
            repo.DatabaseOperations.rename_sound("Old", "New")

        sql, params = cursor.execute.call_args.args
        assert "UPDATE sounds SET name" in sql
        assert params == ("New", "Old")
        conn.commit.assert_called_once()

    def test_get_panel_returns_row(self):
        conn, cursor = self._conn_with_cursor()
        cursor.fetchone.return_value = {"channel_id": 999, "message_ids": [1, 2]}

        with patch("src.services.soundboard.repository.get_database_connection", return_value=conn):
            result = repo.DatabaseOperations.get_panel()

        assert result == {"channel_id": 999, "message_ids": [1, 2]}

    def test_get_panel_returns_none_when_absent(self):
        conn, cursor = self._conn_with_cursor()
        cursor.fetchone.return_value = None

        with patch("src.services.soundboard.repository.get_database_connection", return_value=conn):
            assert repo.DatabaseOperations.get_panel() is None

    def test_save_panel_upserts(self):
        conn, cursor = self._conn_with_cursor()

        with patch("src.services.soundboard.repository.get_database_connection", return_value=conn):
            repo.DatabaseOperations.save_panel(999, [1, 2, 3])

        sql, params = cursor.execute.call_args.args
        assert "INSERT INTO soundboard_panel" in sql
        assert "ON CONFLICT" in sql
        assert params == (999, [1, 2, 3])
        conn.commit.assert_called_once()
