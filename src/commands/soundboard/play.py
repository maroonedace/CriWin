import asyncio
from pathlib import Path
from discord import Interaction, FFmpegPCMAudio

from src.services.soundboard import download_sound_file, get_sounds
from src.core.messaging import send_message
from src.commands.soundboard.constants import (
    UNAVAILABLE_SOUND_MESSAGE,
    VOICE_STATE_INVALID_MESSAGE,
)


async def handle_play(interaction: Interaction, sound_name: str) -> None:
    # Acknowledge the interaction and defer response
    await interaction.response.defer(ephemeral=True)

    # Check user's voice state
    user = interaction.user
    if not user.voice or not user.voice.channel:
        await send_message(interaction, VOICE_STATE_INVALID_MESSAGE)
        return

    try:
        sounds = get_sounds()

    except ValueError as err:
        await send_message(interaction, str(err))
        return

    # Find the requested sound
    sound_entry = next((sound for sound in sounds if sound["name"] == sound_name), None)

    if not sound_entry:
        await send_message(interaction, UNAVAILABLE_SOUND_MESSAGE)
        return

    file_name = sound_entry["file_name"]

    file_path = Path("cache/sounds") / file_name

    if not file_path.exists():
        download_sound_file(file_name)

    channel = user.voice.channel
    vc = interaction.guild.voice_client

    # Connect to voice channel
    try:
        if vc and vc.is_connected():
            await vc.move_to(channel)
        else:
            vc = await channel.connect(timeout=10.0, reconnect=True)
    except Exception:
        await send_message(interaction, "❌ Failed to join voice channel.")
        return

    # Play the sound
    try:
        source_path = file_path
        source = FFmpegPCMAudio(source_path)
        done = asyncio.Event()

        def after_playing(error: Exception = None):
            if error:
                print(f"Error playing sound: {error}")
            interaction.client.loop.call_soon_threadsafe(done.set)

        vc.play(source, after=after_playing)
        await send_message(interaction, f"▶️ Playing **{sound_name}**.")

        # Wait for playback to finish
        await done.wait()

        # Disconnect after playback
        if vc and vc.is_connected():
            await vc.disconnect()

    except Exception as e:
        # Ensure cleanup on error
        try:
            if vc and vc.is_connected():
                await vc.disconnect()
        except Exception:
            pass
        await send_message(interaction, f"❌ Could not play sound: {e}")
