"""Database access for the soundboard.

Statements are built with SQLAlchemy Core against the declarative models in
``src.services.db.models``, then executed through a Session. Rows come back as
dicts rather than ORM instances because the callers (``service.py``, the admin
panel, the Jinja templates) subscript them by key.

Each method wraps its ``with session_scope()`` block in ``try`` rather than the
other way round: the transaction commits as the block exits, so a commit-time
failure only becomes catchable as ``ValueError`` if the ``with`` is inside the
``try``. ``src/web/app.py`` turns those into HTTP 400s.
"""

from typing import Any

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.services.db import session_scope
from src.services.db.models import Guild, Sound, SoundboardAccess, SoundboardPanel
from src.services.soundboard.errors import ErrorMessages


class DatabaseOperations:
    @staticmethod
    def get_all_sounds(guild_id: int) -> list[dict[str, Any]]:
        """Get a guild's sounds from database"""
        stmt = (
            select(Sound.name, Sound.file_name, Sound.volume)
            .where(Sound.guild_id == guild_id)
            .order_by(Sound.name)
        )
        try:
            with session_scope() as session:
                return [dict(row) for row in session.execute(stmt).mappings()]
        except Exception as e:
            raise ValueError(f"{ErrorMessages.DATABASE}: {str(e)}") from e

    @staticmethod
    def add_sound(guild_id: int, name: str, file_name: str) -> None:
        """Add sound to database"""
        # volume and created_at are left to their server defaults.
        stmt = insert(Sound).values(guild_id=guild_id, name=name, file_name=file_name)
        try:
            with session_scope() as session:
                session.execute(stmt)
        except Exception as e:
            raise ValueError(f"{ErrorMessages.UPLOAD_DATABASE}: {str(e)}") from e

    @staticmethod
    def delete_sound(guild_id: int, name: str) -> None:
        """Delete sound from database"""
        stmt = (
            delete(Sound)
            .where(Sound.guild_id == guild_id, Sound.name == name)
            .execution_options(synchronize_session=False)
        )
        try:
            with session_scope() as session:
                session.execute(stmt)
        except Exception as e:
            raise ValueError(f"{ErrorMessages.DELETE_DATABASE}: {str(e)}") from e

    @staticmethod
    def set_volume(guild_id: int, name: str, volume: float) -> None:
        """Update a sound's playback volume"""
        stmt = (
            update(Sound)
            .where(Sound.guild_id == guild_id, Sound.name == name)
            .values(volume=volume)
            .execution_options(synchronize_session=False)
        )
        try:
            with session_scope() as session:
                session.execute(stmt)
        except Exception as e:
            raise ValueError(f"Could not update sound volume: {str(e)}") from e

    @staticmethod
    def rename_sound(guild_id: int, old_name: str, new_name: str) -> None:
        """Rename a sound (updates the display name only, not the stored file)"""
        stmt = (
            update(Sound)
            .where(Sound.guild_id == guild_id, Sound.name == old_name)
            .values(name=new_name)
            .execution_options(synchronize_session=False)
        )
        try:
            with session_scope() as session:
                session.execute(stmt)
        except Exception as e:
            raise ValueError(f"Could not rename sound: {str(e)}") from e

    @staticmethod
    def get_panel(guild_id: int) -> dict[str, Any] | None:
        """Return a guild's stored panel location, or None if it has no panel."""
        stmt = select(SoundboardPanel.channel_id, SoundboardPanel.message_ids).where(
            SoundboardPanel.guild_id == guild_id
        )
        try:
            with session_scope() as session:
                row = session.execute(stmt).mappings().first()
                return dict(row) if row else None
        except Exception as e:
            raise ValueError(f"{ErrorMessages.DATABASE}: {str(e)}") from e

    @staticmethod
    def get_all_panels() -> list[dict[str, Any]]:
        """Return every guild's panel location, for the periodic refresh."""
        stmt = select(
            SoundboardPanel.guild_id, SoundboardPanel.channel_id, SoundboardPanel.message_ids
        )
        try:
            with session_scope() as session:
                return [dict(row) for row in session.execute(stmt).mappings()]
        except Exception as e:
            raise ValueError(f"{ErrorMessages.DATABASE}: {str(e)}") from e

    @staticmethod
    def save_panel(guild_id: int, channel_id: int, message_ids: list[int]) -> None:
        """Upsert a guild's soundboard panel location (channel + message ids)."""
        stmt = pg_insert(SoundboardPanel).values(
            guild_id=guild_id,
            channel_id=channel_id,
            message_ids=message_ids,
            updated_at=func.current_timestamp(),
        )
        # ``stmt.excluded`` is SQL's EXCLUDED: the row the INSERT proposed but the
        # conflict rejected, i.e. the new values.
        stmt = stmt.on_conflict_do_update(
            index_elements=[SoundboardPanel.guild_id],
            set_={
                "channel_id": stmt.excluded.channel_id,
                "message_ids": stmt.excluded.message_ids,
                "updated_at": func.current_timestamp(),
            },
        )
        try:
            with session_scope() as session:
                session.execute(stmt)
        except Exception as e:
            raise ValueError(f"Could not save soundboard panel: {str(e)}") from e

    @staticmethod
    def get_guilds() -> list[dict[str, Any]]:
        """Return every guild the bot is known to be in, ordered by name."""
        stmt = select(Guild.guild_id, Guild.name).order_by(Guild.name)
        try:
            with session_scope() as session:
                return [dict(row) for row in session.execute(stmt).mappings()]
        except Exception as e:
            raise ValueError(f"{ErrorMessages.DATABASE}: {str(e)}") from e

    @staticmethod
    def upsert_guild(guild_id: int, name: str) -> None:
        """Record a guild the bot is in, refreshing its name if it changed."""
        stmt = pg_insert(Guild).values(
            guild_id=guild_id, name=name, updated_at=func.current_timestamp()
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[Guild.guild_id],
            set_={"name": stmt.excluded.name, "updated_at": func.current_timestamp()},
        )
        try:
            with session_scope() as session:
                session.execute(stmt)
        except Exception as e:
            raise ValueError(f"Could not save guild: {str(e)}") from e

    @staticmethod
    def get_access_role_ids(guild_id: int) -> list[int]:
        """Return the role ids allowed to use the panel in a guild (empty = open)."""
        stmt = select(SoundboardAccess.role_id).where(SoundboardAccess.guild_id == guild_id)
        try:
            with session_scope() as session:
                return list(session.scalars(stmt))
        except Exception as e:
            raise ValueError(f"{ErrorMessages.DATABASE}: {str(e)}") from e

    @staticmethod
    def add_access_role(guild_id: int, role_id: int) -> None:
        """Grant a role access to the panel (idempotent)."""
        stmt = (
            pg_insert(SoundboardAccess)
            .values(guild_id=guild_id, role_id=role_id)
            .on_conflict_do_nothing(index_elements=["guild_id", "role_id"])
        )
        try:
            with session_scope() as session:
                session.execute(stmt)
        except Exception as e:
            raise ValueError(f"Could not add soundboard access role: {str(e)}") from e

    @staticmethod
    def remove_access_role(guild_id: int, role_id: int) -> None:
        """Revoke a role's access to the panel."""
        stmt = (
            delete(SoundboardAccess)
            .where(SoundboardAccess.guild_id == guild_id, SoundboardAccess.role_id == role_id)
            .execution_options(synchronize_session=False)
        )
        try:
            with session_scope() as session:
                session.execute(stmt)
        except Exception as e:
            raise ValueError(f"Could not remove soundboard access role: {str(e)}") from e
