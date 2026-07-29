from typing import Any, Dict, List

from psycopg2.extras import RealDictCursor

from src.services.db import get_database_connection
from src.services.soundboard.cache import SoundCache
from src.services.soundboard.errors import ErrorMessages


class DatabaseOperations:
    @staticmethod
    def get_all_sounds() -> List[Dict[str, Any]]:
        """Get all sounds from database"""
        conn = get_database_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT name, file_name, volume FROM sounds ORDER BY name;")
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

    @staticmethod
    def set_volume(name: str, volume: float) -> None:
        """Update a sound's playback volume"""
        conn = get_database_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE sounds SET volume = %s WHERE name = %s;",
                    (volume, name)
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"Could not update sound volume: {str(e)}")
