from discord import Client, Interaction, InteractionCallbackResponse


async def send_message(
    interaction: Interaction, message: str
) -> InteractionCallbackResponse[Client]:
    return await interaction.followup.send(message, ephemeral=True)
