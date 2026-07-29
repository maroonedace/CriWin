from discord import Interaction

from src.commands.leave.constants import BOT_NOT_CONNECTED, NOT_IN_VOICE_CHANNEL
from src.core.messaging import send_message


async def handle_leave(interaction: Interaction):
    """Handle the leave command logic"""
    # Defer response to handle potential delays
    await interaction.response.defer(ephemeral=True)

    user = interaction.user
    guild = interaction.guild

    # Validate voice state
    validation_result = await validate_voice_state(user, guild)
    if validation_result is not True:
        await send_message(interaction, validation_result)
        return

    # Disconnect from voice channel
    await disconnect_from_voice_channel(interaction, guild.voice_client)


async def validate_voice_state(user, guild):
    """Validate user and bot voice states"""
    # Check if user is in a voice channel
    if not user.voice or not user.voice.channel:
        return NOT_IN_VOICE_CHANNEL

    # Check if bot is connected to a voice channel
    vc = guild.voice_client
    if not vc or not vc.is_connected():
        return BOT_NOT_CONNECTED

    # Check if user is in the same voice channel as the bot
    if vc.channel.id != user.voice.channel.id:
        return f"❌ You need to be in **{vc.channel.name}** to make me leave."

    return True


async def disconnect_from_voice_channel(interaction: Interaction, voice_client):
    """Disconnect the bot from voice channel"""
    try:
        channel_name = voice_client.channel.name
        await voice_client.disconnect()
        await send_message(interaction, f"👋 Disconnected from **{channel_name}**.")
    except Exception as e:
        await send_message(interaction, f"❌ Failed to disconnect: {str(e)}")
