from pathlib import Path
from typing import Any

from src.config import Config
from src.services import storage
from src.services.processing import normalize_audio
from src.services.soundboard.cache import FileOperations
from src.services.soundboard.repository import DatabaseOperations


def _object_key(file_name: str) -> str:
    """Build the object-storage key for a soundboard file."""
    return f"{Config.SOUNDBOARD_DIR}/{file_name}"


def _stored_file_name(guild_id: int, filename: str) -> str:
    """Namespace an uploaded file name by guild.

    Display names are only unique per guild, so two guilds can upload the same file
    name; without this they would share (and overwrite) one object in storage.
    """
    return f"{guild_id}_{filename}"


def get_sounds(guild_id: int) -> list[dict[str, Any]]:
    """Get a guild's sounds from the database"""
    return DatabaseOperations.get_all_sounds(guild_id)


async def upload_sound_file(
    guild_id: int,
    name: str,
    data: bytes,
    filename: str,
    content_type: str | None = None,
) -> None:
    """Store sound bytes in object storage and record the sound in the database.

    Framework-agnostic: callers pass raw bytes (a Discord attachment or a web
    upload), not a ``discord.Attachment``.
    """
    try:
        normalized = normalize_audio(data, Path(filename).suffix)
        stored_name = _stored_file_name(guild_id, filename)
        storage.put_bytes(
            _object_key(stored_name), normalized, content_type or "application/octet-stream"
        )
        DatabaseOperations.add_sound(guild_id, name, stored_name)
    except Exception as e:
        raise ValueError(f"Could not upload sound file: {e}") from e


async def delete_sound(guild_id: int, name: str, file_name: str) -> None:
    """Delete sound from object storage, database, and local cache"""
    try:
        storage.remove(_object_key(file_name))
        DatabaseOperations.delete_sound(guild_id, name)
        FileOperations.delete_local_file(file_name)
    except Exception as e:
        raise ValueError(f"Could not delete sound file: {e}") from e


def set_volume(guild_id: int, name: str, volume: float) -> None:
    """Update a sound's playback volume."""
    DatabaseOperations.set_volume(guild_id, name, volume)


def rename_sound(guild_id: int, old_name: str, new_name: str) -> None:
    """Rename a sound's display name (metadata only; the stored file is unchanged)."""
    DatabaseOperations.rename_sound(guild_id, old_name, new_name)


def download_sound_file(file_name: str) -> None:
    """Download sound file from object storage to the local cache"""
    FileOperations.ensure_cache_dir()
    dest = Config.CACHE_DIR / "sounds" / file_name
    storage.fget(_object_key(file_name), dest)


def get_panel(guild_id: int) -> dict[str, Any] | None:
    """Return a guild's panel location (channel id + message ids), or None."""
    return DatabaseOperations.get_panel(guild_id)


def get_all_panels() -> list[dict[str, Any]]:
    """Return every guild's panel location, for the periodic refresh."""
    return DatabaseOperations.get_all_panels()


def save_panel(guild_id: int, channel_id: int, message_ids: list[int]) -> None:
    """Persist a guild's panel location (channel id + message ids)."""
    DatabaseOperations.save_panel(guild_id, channel_id, message_ids)


def get_guilds() -> list[dict[str, Any]]:
    """Return every guild the bot is in (guild_id + name), ordered by name."""
    return DatabaseOperations.get_guilds()


def upsert_guild(guild_id: int, name: str) -> None:
    """Record a guild the bot is in, refreshing its name if it changed."""
    DatabaseOperations.upsert_guild(guild_id, name)


def get_access_role_ids(guild_id: int) -> list[int]:
    """Return the role ids allowed to use the soundboard panel in a guild."""
    return DatabaseOperations.get_access_role_ids(guild_id)


def add_access_role(guild_id: int, role_id: int) -> None:
    """Grant a role access to the soundboard panel."""
    DatabaseOperations.add_access_role(guild_id, role_id)


def remove_access_role(guild_id: int, role_id: int) -> None:
    """Revoke a role's access to the soundboard panel."""
    DatabaseOperations.remove_access_role(guild_id, role_id)
