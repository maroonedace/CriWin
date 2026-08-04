from discord import Interaction, app_commands

from bot.commands.ping.ping import handle_ping


def setup_ping(tree: app_commands.CommandTree):
    """Setup the ping command"""

    @tree.command(name="ping", description="Ping the bot.")
    async def ping(interaction: Interaction):
        await handle_ping(interaction)