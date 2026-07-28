from typing import Any, Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config import Config
from src.services.soundboard.cache import SoundCache
from src.services.soundboard.errors import ErrorMessages

_db_connection = None  # cached module-level connection


def get_database_connection():
    """Get PostgreSQL database connection (cached module-level singleton)."""
    global _db_connection
    if _db_connection is None or _db_connection.closed:
        try:
            _db_connection = psycopg2.connect(
                database=Config.POSTGRES_DB,
                user=Config.POSTGRES_USER,
                password=Config.POSTGRES_PASSWORD,
                connect_timeout=10
            )
        except Exception as e:
            raise ValueError(f"{ErrorMessages.DATABASE_CLIENT}: {str(e)}")
    return _db_connection


class DatabaseOperations:
    @staticmethod
    def get_all_sounds() -> List[Dict[str, Any]]:
        """Get all sounds from database"""

        conn = get_database_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT name, file_name FROM sounds ORDER BY name;")
                sound_items = cursor.fetchall()

                # Convert to list of dicts
                sound_items = [dict(row) for row in sound_items]
        except Exception as e:
            conn.rollback()
            raise ValueError(f"{ErrorMessages.DATABASE}: {str(e)}")

        SoundCache.save(sound_items)
        return sound_items

    @staticmethod
    def add_sound(name: str, file_name: str) -> None:
        """Add sound to database"""
        conn = get_database_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO sounds (name, file_name) VALUES (%s, %s);",
                    (name, file_name)
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"{ErrorMessages.UPLOAD_DATABASE}: {str(e)}")

    @staticmethod
    def delete_sound(name: str) -> None:
        """Delete sound from database"""
        conn = get_database_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM sounds WHERE name = %s;",
                    (name,)
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"{ErrorMessages.DELETE_DATABASE}: {str(e)}")
