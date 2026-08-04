import logging

from discord import Interaction

from bot.constants import EXTRACTION_ERROR, EXTRACTION_REQUESTED
from bot.media.extractor import extract
from bot.messages import (
    EXTRACTION_FAILED,
    POST_SUMMARY,
    UNSUPPORTED_PLATFORM,
    UNTITLED_POST,
)

logger = logging.getLogger(__name__)


async def handle_download(interaction: Interaction, url: str):
    """Handle the download command"""
    await interaction.response.defer(ephemeral=True)

    logger.info(EXTRACTION_REQUESTED, interaction.user.id, url)

    try:
        post = await extract(url)

    except Exception:
        logger.exception(EXTRACTION_ERROR, url)
        await interaction.followup.send(EXTRACTION_FAILED, ephemeral=True)
        return

    if post is None:
        await interaction.followup.send(UNSUPPORTED_PLATFORM, ephemeral=True)
        return

    await interaction.followup.send(
        POST_SUMMARY.format(
            title=post.title or UNTITLED_POST,
            platform=post.platform,
            count=len(post.items),
        ),
        ephemeral=True,
    )
