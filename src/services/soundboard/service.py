from typing import Any, Dict, List

import discord
from discord import app_commands

from src.services.soundboard.cache import FileOperations, SoundCache
from src.services.soundboard.repository import DatabaseOperations
from src.services.soundboard.storage import S3Operations


def get_sounds() -> List[Dict[str, Any]]:
    """Get all sounds (cached or from database)"""
    return DatabaseOperations.get_all_sounds()


async def upload_sound_file(name: str, file: discord.Attachment) -> None:
    """Upload sound file to object storage and database"""
    try:
        await S3Operations.upload_file(file)
        DatabaseOperations.add_sound(name, file.filename)
        SoundCache.invalidate()
    except Exception as e:
        raise ValueError(f"Could not upload sound file: {e}")


async def delete_sound(name: str, file_name: str) -> None:
    """Delete sound from object storage, database, and local cache"""
    try:
        S3Operations.delete_file(file_name)
        DatabaseOperations.delete_sound(name)
        FileOperations.delete_local_file(file_name)
        SoundCache.invalidate()
    except Exception as e:
        raise ValueError(f"Could not delete sound file: {e}")


def download_sound_file(file_name: str) -> None:
    """Download sound file from object storage to local cache"""
    S3Operations.download_file(file_name)


async def autocomplete_sound_name(current: str) -> List[app_commands.Choice[str]]:
    """Generate autocomplete choices for sound names"""
    try:
        sounds = get_sounds()
        filtered_sounds = [
            sound for sound in sounds if current.lower() in sound["name"].lower()
        ]
        return [
            app_commands.Choice(name=sound["name"], value=sound["name"])
            for sound in filtered_sounds[:25]  # Discord limit
        ]
    except Exception:
        return []
