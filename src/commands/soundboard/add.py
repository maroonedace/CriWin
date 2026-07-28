from discord import Interaction
import discord
import re

from src.commands.soundboard.utils import get_sounds, upload_sound_file
from src.core.messaging import send_message

# Regular expression for validating sound IDs
ID_RE = re.compile(r"^[a-zA-Z0-9 _'-]{1,64}$")

DISPLAY_NAME_INVALID_MESSAGE = "Display Name is invalid. It must be no more than 64 characters."
INVALID_AUDIO_MESSAGE = "Only audio files are allowed."
DUPLICATE_DISPLAY_NAME_MESSAGE = "❌ A sound with that Display Name already exists."

ALLOWED_CONTENT_TYPES = {"audio/wav", "audio/mpeg", "audio/flac", "audio/mp4"}

async def setup_soundboard_add(interaction: Interaction, sound_name: str, sound_file: discord.Attachment) -> None:
    # Acknowledge the interaction and defer response
    await interaction.response.defer(ephemeral=True)
    
    # Confirms that the sound name is valid
    if not ID_RE.match(sound_name):
        await send_message(interaction, DISPLAY_NAME_INVALID_MESSAGE)
        return
    
    # Confirms that the uploaded file is an audio file
    if sound_file.content_type not in ALLOWED_CONTENT_TYPES:
        await send_message(interaction, INVALID_AUDIO_MESSAGE)
        return
    
    sounds = get_sounds()
    
    if any(sound["name"] == sound_name for sound in sounds):
        await send_message(interaction, DUPLICATE_DISPLAY_NAME_MESSAGE)
        return
    
    try:
        await upload_sound_file(sound_name, sound_file)
    except ValueError as err:
        await send_message(interaction, str(err))
        return

    await send_message(
        interaction,
        f"✅ Added **{sound_name}** → {sound_file.filename}"
        )
    
    
    
    
