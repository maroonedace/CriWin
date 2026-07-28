"""Covers the shared Postgres connection (src.services.db), which the soundboard
repository now depends on."""

from unittest.mock import MagicMock, patch

import pytest

import src.services.db as db
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
