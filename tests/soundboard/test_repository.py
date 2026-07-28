from unittest.mock import MagicMock, patch

import pytest

import src.services.soundboard.repository as repo
from src.config import Config


@pytest.fixture(autouse=True)
def _reset_connection_singleton():
    repo._db_connection = None
    yield
    repo._db_connection = None


def test_get_database_connection_passes_config():
    fake_conn = MagicMock()
    fake_conn.closed = False

    with patch(
        "src.services.soundboard.repository.psycopg2.connect",
        return_value=fake_conn,
    ) as mock_connect:
        conn = repo.get_database_connection()

    assert conn is fake_conn
    mock_connect.assert_called_once_with(
        host=Config.POSTGRES_HOST,
        port=Config.POSTGRES_PORT,
        database=Config.POSTGRES_DB,
        user=Config.POSTGRES_USER,
        password=Config.POSTGRES_PASSWORD,
        connect_timeout=10,
    )


def test_get_database_connection_is_cached():
    fake_conn = MagicMock()
    fake_conn.closed = False

    with patch(
        "src.services.soundboard.repository.psycopg2.connect",
        return_value=fake_conn,
    ) as mock_connect:
        repo.get_database_connection()
        repo.get_database_connection()

    mock_connect.assert_called_once()


def test_get_database_connection_reconnects_when_closed():
    closed_conn = MagicMock()
    closed_conn.closed = True
    fresh_conn = MagicMock()
    fresh_conn.closed = False
    repo._db_connection = closed_conn

    with patch(
        "src.services.soundboard.repository.psycopg2.connect",
        return_value=fresh_conn,
    ) as mock_connect:
        conn = repo.get_database_connection()

    assert conn is fresh_conn
    mock_connect.assert_called_once()
