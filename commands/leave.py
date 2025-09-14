from discord import Interaction, app_commands
from discord.ext import commands

def setup_leave(tree: app_commands.CommandTree):
    @tree.command(name="leave", description="Kick the bot from your voice channel.")

    async def leave(interaction: Interaction):
        user = interaction.user
        
        # Helper function to send error messages
        async def send_error(message: str):
            await interaction.followup.send(message, ephemeral=True)
            
        if not user.voice or not user.voice.channel:
            return await send_error(
                "❌ You must be in a voice channel to use this command."
            )
        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await send_error(
                "⚠️ I'm not connected to any voice channel in this server."
            )
        if vc.channel.id != user.voice.channel.id:
            return await send_error(
                f"❌ You need to be in **{vc.channel.name}** to make me leave."
            )
        await vc.disconnect()
        await interaction.followup.send(
            f"👋 Disconnected from **{vc.channel.name}**.",
            ephemeral=True
        )