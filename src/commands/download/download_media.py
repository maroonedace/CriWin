import asyncio
import logging
from pathlib import Path

from discord import File, Interaction

from src.commands.download.constants import (
    DOWNLOAD_SENT_TO_CHANNEL_MESSAGE,
    LIMIT_DOWNLOAD_MESSAGE,
    large_file_message,
)
from src.commands.download.limits import get_max_upload_mb
from src.core.messaging import send_message
from src.services.media import (
    gallery_downloader,
    is_file_too_large,
    is_instagram_url,
    video_downloader,
)

logger = logging.getLogger(__name__)


def _collect_files(result: Path | list[Path]) -> list[Path]:
    """Normalize the downloader result into a flat list of Paths."""
    if isinstance(result, list):
        return result
    return [result]


async def handle_download_media(
    interaction: Interaction,
    active_downloads: set[int],
    url: str,
    is_hidden: bool,
) -> None:
    await interaction.response.defer(ephemeral=is_hidden)

    user_id = interaction.user.id

    if user_id in active_downloads:
        await send_message(interaction, LIMIT_DOWNLOAD_MESSAGE)
        return

    active_downloads.add(user_id)
    files: list[Path] = []

    try:
        logger.info("Media download started by user %s for URL: %s", user_id, url)

        if is_instagram_url(url):
            result = await asyncio.to_thread(gallery_downloader, url)
        else:
            result = await asyncio.to_thread(video_downloader, url, True)

        files = _collect_files(result)

        max_size_mb = get_max_upload_mb(interaction)
        for file_path in files:
            if is_file_too_large(str(file_path), max_size_mb):
                raise ValueError(large_file_message(max_size_mb))

        discord_files = [File(str(f)) for f in files]

        if is_hidden:
            await interaction.followup.send(files=discord_files, ephemeral=True)
            return

        await interaction.followup.send(
            files=discord_files, content=DOWNLOAD_SENT_TO_CHANNEL_MESSAGE
        )

        logger.info("Media download completed for user %s", user_id)

    except ValueError as error:
        await send_message(interaction, str(error))

    except Exception:
        logger.exception("Unexpected error during media download for user %s", user_id)
        await send_message(interaction, "⚠️ An unexpected error occurred during the download.")

    finally:
        active_downloads.discard(user_id)
        for file_path in files:
            file_path.unlink(missing_ok=True)
