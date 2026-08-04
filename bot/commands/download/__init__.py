from discord import Interaction, app_commands

from bot.commands.download.download import handle_download


def setup_download(tree: app_commands.CommandTree):
    """Setup the download command"""

    @tree.command(name="download", description="Download a media post.")
    @app_commands.describe(
        url="The URL to download media from"
    )
    async def download(interaction: Interaction, url: str):
        await handle_download(interaction, url)