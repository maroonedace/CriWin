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
from src.services.media import is_file_too_large, video_downloader

logger = logging.getLogger(__name__)


async def handle_download_audio(
    interaction: Interaction, active_downloads: set[int], url: str, is_hidden: bool
) -> None:
    # Acknowledge the interaction and defer response
    await interaction.response.defer(ephemeral=is_hidden)

    # Get user ID for download tracking
    user_id = interaction.user.id

    # Limit to one download at a time per user
    if user_id in active_downloads:
        await send_message(interaction, LIMIT_DOWNLOAD_MESSAGE)
        return

    # Add user to active downloads tracking
    active_downloads.add(user_id)

    # Initialize file_path for cleanup
    file_path: Path | None = None

    try:
        logger.info("Audio download started by user %s for URL: %s", user_id, url)
        file_path = await asyncio.to_thread(video_downloader, url, False)

        max_size_mb = get_max_upload_mb(interaction)

        if is_file_too_large(str(file_path), max_size_mb):
            raise ValueError(large_file_message(max_size_mb))

        discord_file = File(str(file_path))

        if is_hidden:
            await interaction.followup.send(file=discord_file, ephemeral=True)
            return

        await interaction.followup.send(file=discord_file, content=DOWNLOAD_SENT_TO_CHANNEL_MESSAGE)

        logger.info("Audio download completed for user %s", user_id)

    except ValueError as error:
        await send_message(interaction, str(error))

    except Exception:
        logger.exception("Unexpected error during audio download for user %s", user_id)
        await send_message(interaction, "⚠️ An unexpected error occurred during the download.")

    finally:
        active_downloads.discard(user_id)
        if file_path is not None:
            file_path.unlink(missing_ok=True)
