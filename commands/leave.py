from discord import Interaction, app_commands

def setup_leave(tree: app_commands.CommandTree):
    @tree.command(name="leave", description="Kick the bot from your voice channel.")

    async def leave(interaction: Interaction):
        user = interaction.user
        if not user.voice or not user.voice.channel:
            return await interaction.followup.send(
                "❌ You must be in a voice channel to use this command.",
                ephemeral=True
            )
        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.followup.send(
                "⚠️ I'm not connected to any voice channel in this server.",
                ephemeral=True
            )
        
        if vc.channel.id != user.voice.channel.id:
            return await interaction.followup.send(
                f"❌ You need to be in **{vc.channel.name}** to make me leave.",
                ephemeral=True
            )
        await vc.disconnect()
        await interaction.followup.send(
            f"👋 Disconnected from **{vc.channel.name}**.",
            ephemeral=True
        )