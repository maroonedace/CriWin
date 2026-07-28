import re

# Regular expression for validating sound names
ID_RE = re.compile(r"^[a-zA-Z0-9 _'-]{1,64}$")

ALLOWED_CONTENT_TYPES = {"audio/wav", "audio/mpeg", "audio/flac", "audio/mp4"}

# /soundboard-add
DISPLAY_NAME_INVALID_MESSAGE = "Display Name is invalid. It must be no more than 64 characters."
INVALID_AUDIO_MESSAGE = "Only audio files are allowed."
DUPLICATE_DISPLAY_NAME_MESSAGE = "❌ A sound with that Display Name already exists."

# /soundboard (play)
VOICE_STATE_INVALID_MESSAGE = "❌ You must be in a voice channel."

# /soundboard (play) and /soundboard-delete
UNAVAILABLE_SOUND_MESSAGE = "❌ That sound isn't available."
