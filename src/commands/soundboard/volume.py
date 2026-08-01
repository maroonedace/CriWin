"""Personal per-play volume for the soundboard panel.

Each user picks their own playback volume from a dropdown on the panel; it applies only
to sounds *they* play and never changes a sound's stored default. Preferences are kept
in memory (personal and transient — they reset when the bot restarts).
"""

import logging

import discord
from discord import Interaction

from src.commands.soundboard.access import NO_ACCESS_MESSAGE, has_panel_access
from src.services.soundboard import get_access_role_ids

logger = logging.getLogger(__name__)

VOLUME_CUSTOM_ID = "soundboard:volume"

# Selectable volume presets, as percentages.
VOLUME_PERCENTS = (25, 50, 75, 100, 125, 150, 175, 200)

# user_id -> chosen volume multiplier (personal, in-memory only).
_user_volumes: dict[int, float] = {}


def set_user_volume(user_id: int, volume: float) -> None:
    _user_volumes[user_id] = volume


def get_user_volume(user_id: int) -> float | None:
    return _user_volumes.get(user_id)


def resolve_volume(user_id: int, stored_volume: float) -> float:
    """The user's chosen volume if they set one, otherwise the sound's stored volume."""
    personal = _user_volumes.get(user_id)
    return personal if personal is not None else stored_volume


class VolumeSelect(discord.ui.DynamicItem[discord.ui.Select], template=f"^{VOLUME_CUSTOM_ID}$"):
    """Persistent dropdown that sets the clicking user's personal playback volume."""

    def __init__(self) -> None:
        super().__init__(
            discord.ui.Select(
                custom_id=VOLUME_CUSTOM_ID,
                placeholder="Set your volume…",
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(label=f"{pct}%", value=str(pct / 100))
                    for pct in VOLUME_PERCENTS
                ],
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match, /):
        return cls()

    async def callback(self, interaction: Interaction) -> None:
        allowed = set(get_access_role_ids(interaction.guild.id))
        if not has_panel_access(interaction.user, allowed):
            await interaction.response.send_message(NO_ACCESS_MESSAGE, ephemeral=True)
            return

        try:
            volume = float(interaction.data["values"][0])
        except (KeyError, IndexError, ValueError, TypeError):
            volume = 1.0

        set_user_volume(interaction.user.id, volume)
        await interaction.response.send_message(
            f"🔊 Your volume is now **{int(volume * 100)}%**.", ephemeral=True
        )
