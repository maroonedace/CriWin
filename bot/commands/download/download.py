import logging

from discord import Interaction

from bot.constants import (
    EXTRACTION_ERROR,
    EXTRACTION_REQUESTED,
    POST_REFUSED,
    SIZING_ERROR,
)
from bot.media.extractor import extract
from bot.media.sizing import SizeVerdict, resolve_post_size
from bot.messages import (
    EXTRACTION_FAILED,
    POST_EMPTY,
    POST_SIZE_UNKNOWN,
    POST_SUMMARY,
    POST_TOO_LARGE,
    UNSUPPORTED_PLATFORM,
    UNTITLED_POST,
)
from bot.units import MEGABYTE

logger = logging.getLogger(__name__)

REFUSALS = {
    SizeVerdict.TOO_LARGE: POST_TOO_LARGE,
    SizeVerdict.UNKNOWN: POST_SIZE_UNKNOWN,
    SizeVerdict.EMPTY: POST_EMPTY,
}


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

    try:
        size = await resolve_post_size(post)
    except Exception:
        logger.exception(SIZING_ERROR, url)
        await interaction.followup.send(EXTRACTION_FAILED, ephemeral=True)
        return

    if not size.accepted:
        logger.info(
            POST_REFUSED, url, size.verdict, size.total_bytes, size.limit_bytes
        )
        await interaction.followup.send(
            REFUSALS.get(size.verdict, POST_SIZE_UNKNOWN).format(
                size=megabytes(size.total_bytes),
                limit=megabytes(size.limit_bytes),
            ),
            ephemeral=True,
        )
        return

    await interaction.followup.send(
        POST_SUMMARY.format(
            title=post.title or UNTITLED_POST,
            platform=post.platform,
            count=len(post.items),
        ),
        ephemeral=True,
    )


def megabytes(total: int) -> str:
    """Render a byte count for a user, who does not think in bytes."""
    return f"{total / MEGABYTE:.1f}"
