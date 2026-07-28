from discord import Interaction

from src.commands.soundboard.utils import delete_sound, get_sounds
from src.core.messaging import send_message

UNAVAILABLE_SOUND_MESSAGE = "❌ That sound isn't available."

async def setup_soundboard_delete(interaction: Interaction, sound_name: str) -> None:
    # Acknowledge the interaction and defer response
    await interaction.response.defer(ephemeral=True)
    
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
    
    try:
        await delete_sound(sound_name, sound_entry["file_name"])
    except ValueError as err:
        await send_message(interaction, str(err))
        return

    await send_message(
        interaction,
        f"✅ Deleted **{sound_name}** from the soundboard."
        )
    