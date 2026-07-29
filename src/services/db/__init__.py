"""Shared PostgreSQL connection.

A single cached module-level connection reused across the app. Not
multi-worker-safe; the web admin runs a single worker (see the sprint plan).
"""

import psycopg2

from src.config import Config

_connection = None


def get_database_connection():
    """Return a cached psycopg2 connection to the configured database."""
    global _connection
    if _connection is None or _connection.closed:
        try:
            _connection = psycopg2.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                database=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                connect_timeout=10,
            )
        except Exception as e:
            raise ValueError(f"Could not connect to the database: {e}")
    return _connection
