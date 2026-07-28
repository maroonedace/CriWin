from discord import Interaction

from src.services.media.constants import BOOST_LEVEL_UPLOAD_SIZE, DEFAULT_UPLOAD_LIMIT_MB


def get_max_upload_mb(interaction: Interaction) -> int:
    """Return the guild's Discord upload cap in MB, based on its Nitro boost tier.

    Falls back to the default limit outside a guild or for an unknown tier.
    """
    if interaction.guild is not None:
        return BOOST_LEVEL_UPLOAD_SIZE.get(interaction.guild.premium_tier, DEFAULT_UPLOAD_LIMIT_MB)
    return DEFAULT_UPLOAD_LIMIT_MB
