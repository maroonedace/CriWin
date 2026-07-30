from pathlib import Path
from typing import Any

from discord import app_commands

from src.config import Config
from src.services import storage
from src.services.processing import normalize_audio
from src.services.soundboard.cache import FileOperations, SoundCache
from src.services.soundboard.repository import DatabaseOperations


def _object_key(file_name: str) -> str:
    """Build the object-storage key for a soundboard file."""
    return f"{Config.SOUNDBOARD_DIR}/{file_name}"


def get_sounds() -> list[dict[str, Any]]:
    """Get all sounds (cached or from database)"""
    return DatabaseOperations.get_all_sounds()


async def upload_sound_file(
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
        storage.put_bytes(
            _object_key(filename), normalized, content_type or "application/octet-stream"
        )
        DatabaseOperations.add_sound(name, filename)
        SoundCache.invalidate()
    except Exception as e:
        raise ValueError(f"Could not upload sound file: {e}") from e


async def delete_sound(name: str, file_name: str) -> None:
    """Delete sound from object storage, database, and local cache"""
    try:
        storage.remove(_object_key(file_name))
        DatabaseOperations.delete_sound(name)
        FileOperations.delete_local_file(file_name)
        SoundCache.invalidate()
    except Exception as e:
        raise ValueError(f"Could not delete sound file: {e}") from e


def set_volume(name: str, volume: float) -> None:
    """Update a sound's playback volume."""
    DatabaseOperations.set_volume(name, volume)
    SoundCache.invalidate()


def rename_sound(old_name: str, new_name: str) -> None:
    """Rename a sound's display name (metadata only; the stored file is unchanged)."""
    DatabaseOperations.rename_sound(old_name, new_name)
    SoundCache.invalidate()


def download_sound_file(file_name: str) -> None:
    """Download sound file from object storage to the local cache"""
    SoundCache.ensure_cache_dir()
    dest = Config.CACHE_DIR / "sounds" / file_name
    storage.fget(_object_key(file_name), dest)


async def autocomplete_sound_name(current: str) -> list[app_commands.Choice[str]]:
    """Generate autocomplete choices for sound names"""
    try:
        sounds = get_sounds()
        filtered_sounds = [sound for sound in sounds if current.lower() in sound["name"].lower()]
        return [
            app_commands.Choice(name=sound["name"], value=sound["name"])
            for sound in filtered_sounds[:25]  # Discord limit
        ]
    except Exception:
        return []
