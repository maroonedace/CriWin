from discord import Interaction, app_commands

from src.commands.download.download_audio import handle_download_audio
from src.commands.download.download_media import handle_download_media

active_downloads: set[int] = set()


def setup_download(tree: app_commands.CommandTree):
    @tree.command(
        name="download-audio",
        description="Download audio from a URL",
    )
    @app_commands.describe(
        url="The URL to download audio from",
        is_hidden="Make the download hidden from others in the channel",
    )
    async def download_audio(interaction: Interaction, url: str, is_hidden: bool = False):
        await handle_download_audio(interaction, active_downloads, url, is_hidden)

    @tree.command(
        name="download-media",
        description="Download video or images from a URL",
    )
    @app_commands.describe(
        url="The URL to download media from",
        is_hidden="Make the download hidden from others in the channel",
    )
    async def download_media(interaction: Interaction, url: str, is_hidden: bool = False):
        await handle_download_media(interaction, active_downloads, url, is_hidden)


__all__ = ["setup_download"]
