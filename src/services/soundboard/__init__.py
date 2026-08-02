"""Soundboard service.

Postgres metadata + object-storage audio + local filesystem cache, split into
cohesive modules (models / errors / repository / storage / cache / service).
This package's public API is consumed by the soundboard command handlers under
``src/commands/soundboard``.
"""

from src.services.soundboard.models import Sound
from src.services.soundboard.service import (
    add_access_role,
    delete_sound,
    download_sound_file,
    get_access_role_ids,
    get_all_panels,
    get_guilds,
    get_panel,
    get_sounds,
    remove_access_role,
    rename_sound,
    save_panel,
    set_volume,
    upload_sound_file,
    upsert_guild,
)

__all__ = [
    "Sound",
    "add_access_role",
    "delete_sound",
    "download_sound_file",
    "get_access_role_ids",
    "get_all_panels",
    "get_guilds",
    "get_panel",
    "get_sounds",
    "remove_access_role",
    "rename_sound",
    "save_panel",
    "set_volume",
    "upload_sound_file",
    "upsert_guild",
]
