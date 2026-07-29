from discord import Interaction
import discord

from src.services.soundboard import get_sounds, upload_sound_file
from src.core.messaging import send_message
from src.commands.soundboard.constants import (
    ALLOWED_CONTENT_TYPES,
    DISPLAY_NAME_INVALID_MESSAGE,
    DUPLICATE_DISPLAY_NAME_MESSAGE,
    ID_RE,
    INVALID_AUDIO_MESSAGE,
)


async def handle_add(interaction: Interaction, sound_name: str, sound_file: discord.Attachment) -> None:
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
        data = await sound_file.read()
        await upload_sound_file(sound_name, data, sound_file.filename, sound_file.content_type)
    except ValueError as err:
        await send_message(interaction, str(err))
        return

    await send_message(
        interaction,
        f"✅ Added **{sound_name}** → {sound_file.filename}"
    )
