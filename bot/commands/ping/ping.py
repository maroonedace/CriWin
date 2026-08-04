from discord import Interaction

async def handle_ping(interaction: Interaction):
    await interaction.response.send_message("Pong!", ephemeral=True)