from typing import Any

from psycopg2.extras import RealDictCursor

from src.services.db import get_database_connection
from src.services.soundboard.cache import SoundCache
from src.services.soundboard.errors import ErrorMessages


class DatabaseOperations:
    @staticmethod
    def get_all_sounds(guild_id: int) -> list[dict[str, Any]]:
        """Get a guild's sounds from database"""
        conn = get_database_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT name, file_name, volume FROM sounds WHERE guild_id = %s ORDER BY name;",
                    (guild_id,),
                )
                sound_items = cursor.fetchall()

                # Convert to list of dicts
                sound_items = [dict(row) for row in sound_items]
        except Exception as e:
            conn.rollback()
            raise ValueError(f"{ErrorMessages.DATABASE}: {str(e)}") from e

        SoundCache.save(sound_items)
        return sound_items

    @staticmethod
    def add_sound(guild_id: int, name: str, file_name: str) -> None:
        """Add sound to database"""
        conn = get_database_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO sounds (guild_id, name, file_name) VALUES (%s, %s, %s);",
                    (guild_id, name, file_name),
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"{ErrorMessages.UPLOAD_DATABASE}: {str(e)}") from e

    @staticmethod
    def delete_sound(guild_id: int, name: str) -> None:
        """Delete sound from database"""
        conn = get_database_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM sounds WHERE guild_id = %s AND name = %s;", (guild_id, name)
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"{ErrorMessages.DELETE_DATABASE}: {str(e)}") from e

    @staticmethod
    def set_volume(guild_id: int, name: str, volume: float) -> None:
        """Update a sound's playback volume"""
        conn = get_database_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE sounds SET volume = %s WHERE guild_id = %s AND name = %s;",
                    (volume, guild_id, name),
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"Could not update sound volume: {str(e)}") from e

    @staticmethod
    def rename_sound(guild_id: int, old_name: str, new_name: str) -> None:
        """Rename a sound (updates the display name only, not the stored file)"""
        conn = get_database_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE sounds SET name = %s WHERE guild_id = %s AND name = %s;",
                    (new_name, guild_id, old_name),
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"Could not rename sound: {str(e)}") from e

    @staticmethod
    def get_panel(guild_id: int) -> dict[str, Any] | None:
        """Return a guild's stored panel location, or None if it has no panel."""
        conn = get_database_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT channel_id, message_ids FROM soundboard_panels WHERE guild_id = %s;",
                    (guild_id,),
                )
                row = cursor.fetchone()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"{ErrorMessages.DATABASE}: {str(e)}") from e
        return dict(row) if row else None

    @staticmethod
    def get_all_panels() -> list[dict[str, Any]]:
        """Return every guild's panel location, for the periodic refresh."""
        conn = get_database_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT guild_id, channel_id, message_ids FROM soundboard_panels;")
                rows = cursor.fetchall()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"{ErrorMessages.DATABASE}: {str(e)}") from e
        return [dict(row) for row in rows]

    @staticmethod
    def save_panel(guild_id: int, channel_id: int, message_ids: list[int]) -> None:
        """Upsert a guild's soundboard panel location (channel + message ids)."""
        conn = get_database_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO soundboard_panels (guild_id, channel_id, message_ids, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (guild_id) DO UPDATE
                        SET channel_id = EXCLUDED.channel_id,
                            message_ids = EXCLUDED.message_ids,
                            updated_at = CURRENT_TIMESTAMP;
                    """,
                    (guild_id, channel_id, message_ids),
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"Could not save soundboard panel: {str(e)}") from e

    @staticmethod
    def get_guilds() -> list[dict[str, Any]]:
        """Return every guild the bot is known to be in, ordered by name."""
        conn = get_database_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT guild_id, name FROM guilds ORDER BY name;")
                rows = cursor.fetchall()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"{ErrorMessages.DATABASE}: {str(e)}") from e
        return [dict(row) for row in rows]

    @staticmethod
    def upsert_guild(guild_id: int, name: str) -> None:
        """Record a guild the bot is in, refreshing its name if it changed."""
        conn = get_database_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO guilds (guild_id, name, updated_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (guild_id) DO UPDATE
                        SET name = EXCLUDED.name,
                            updated_at = CURRENT_TIMESTAMP;
                    """,
                    (guild_id, name),
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"Could not save guild: {str(e)}") from e

    @staticmethod
    def get_access_role_ids(guild_id: int) -> list[int]:
        """Return the role ids allowed to use the panel in a guild (empty = open)."""
        conn = get_database_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT role_id FROM soundboard_access WHERE guild_id = %s;", (guild_id,)
                )
                rows = cursor.fetchall()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"{ErrorMessages.DATABASE}: {str(e)}") from e
        return [row[0] for row in rows]

    @staticmethod
    def add_access_role(guild_id: int, role_id: int) -> None:
        """Grant a role access to the panel (idempotent)."""
        conn = get_database_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO soundboard_access (guild_id, role_id) VALUES (%s, %s) "
                    "ON CONFLICT (guild_id, role_id) DO NOTHING;",
                    (guild_id, role_id),
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"Could not add soundboard access role: {str(e)}") from e

    @staticmethod
    def remove_access_role(guild_id: int, role_id: int) -> None:
        """Revoke a role's access to the panel."""
        conn = get_database_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM soundboard_access WHERE guild_id = %s AND role_id = %s;",
                    (guild_id, role_id),
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"Could not remove soundboard access role: {str(e)}") from e
