"""Constants for the soundboard command handlers.

The display-name rules (regex + messages) are re-exported from the Discord-free
service layer (:mod:`src.services.soundboard.validation`) so the bot commands and
the FastAPI admin panel enforce identical rules from a single source of truth.
"""

from src.services.soundboard.validation import (
    DUPLICATE_NAME_MESSAGE as DUPLICATE_DISPLAY_NAME_MESSAGE,
)
from src.services.soundboard.validation import (
    INVALID_NAME_MESSAGE as DISPLAY_NAME_INVALID_MESSAGE,
)
from src.services.soundboard.validation import (
    NAME_RE as ID_RE,
)

ALLOWED_CONTENT_TYPES = {"audio/wav", "audio/mpeg", "audio/flac", "audio/mp4"}

# /soundboard-add
INVALID_AUDIO_MESSAGE = "Only audio files are allowed."

# /soundboard (play)
VOICE_STATE_INVALID_MESSAGE = "❌ You must be in a voice channel."

# /soundboard (play) and /soundboard-delete
UNAVAILABLE_SOUND_MESSAGE = "❌ That sound isn't available."

__all__ = [
    "ALLOWED_CONTENT_TYPES",
    "DISPLAY_NAME_INVALID_MESSAGE",
    "DUPLICATE_DISPLAY_NAME_MESSAGE",
    "ID_RE",
    "INVALID_AUDIO_MESSAGE",
    "UNAVAILABLE_SOUND_MESSAGE",
    "VOICE_STATE_INVALID_MESSAGE",
]
