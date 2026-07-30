"""Soundboard service.

Postgres metadata + object-storage audio + local filesystem cache, split into
cohesive modules (models / errors / repository / storage / cache / service).
This package's public API is consumed by the soundboard command handlers under
``src/commands/soundboard``.
"""

from src.services.soundboard.models import Sound
from src.services.soundboard.service import (
    autocomplete_sound_name,
    delete_sound,
    download_sound_file,
    get_panel,
    get_sounds,
    rename_sound,
    save_panel,
    set_volume,
    upload_sound_file,
)

__all__ = [
    "Sound",
    "autocomplete_sound_name",
    "delete_sound",
    "download_sound_file",
    "get_panel",
    "get_sounds",
    "rename_sound",
    "save_panel",
    "set_volume",
    "upload_sound_file",
]
