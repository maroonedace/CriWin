"""Soundboard button panel.

A message of buttons (one per sound) posted in a channel. Buttons are persistent
``DynamicItem``s (their handler is registered once at startup and survives restarts),
so the panel keeps working across reboots and as sounds change. An hourly task rebuilds
the message(s) from the current soundboard.
"""

import logging
import re

import discord
from discord import Interaction

from src.commands.soundboard.voice import play_sound
from src.services.soundboard import get_panel, get_sounds, save_panel

logger = logging.getLogger(__name__)

# custom_id encodes the sound name: "soundboard:play:<name>" (prefix 16 + name ≤64 ≤ 100).
PLAY_TEMPLATE = r"^soundboard:play:(?P<name>.+)$"

PANEL_CONTENT = "🔊 **Soundboard** — click a button to play a sound."
EMPTY_CONTENT = "🔊 **Soundboard** — no sounds yet."
CONTINUATION_CONTENT = "​"  # zero-width space for continuation messages
MAX_BUTTONS_PER_MESSAGE = 25  # Discord allows 5 rows × 5 buttons per message


class SoundButton(discord.ui.DynamicItem[discord.ui.Button], template=PLAY_TEMPLATE):
    """A persistent button that plays one sound when clicked."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(
            discord.ui.Button(
                label=name[:80],
                style=discord.ButtonStyle.secondary,
                custom_id=f"soundboard:play:{name}",
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match: re.Match[str], /):
        return cls(match["name"])

    async def callback(self, interaction: Interaction) -> None:
        await play_sound(interaction, self.name)


def _chunk(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def build_panel_views(sounds: list[dict]) -> list[discord.ui.View]:
    """Build one persistent View (≤25 sound buttons) per chunk of sounds."""
    views: list[discord.ui.View] = []
    for chunk in _chunk(sounds, MAX_BUTTONS_PER_MESSAGE):
        view = discord.ui.View(timeout=None)
        for sound in chunk:
            view.add_item(SoundButton(sound["name"]))
        views.append(view)
    return views


async def _render(channel, existing_ids: list[int]) -> None:
    """Reconcile the panel messages in ``channel`` with the current soundboard."""
    sounds = get_sounds()
    views: list[discord.ui.View | None] = build_panel_views(sounds) or [None]
    new_ids: list[int] = []

    for index, view in enumerate(views):
        if index == 0:
            content = PANEL_CONTENT if sounds else EMPTY_CONTENT
        else:
            content = CONTINUATION_CONTENT

        message = None
        if index < len(existing_ids):
            try:
                message = await channel.fetch_message(existing_ids[index])
                await message.edit(content=content, view=view)
            except Exception:
                message = None  # message was deleted — fall through and send a new one
        if message is None:
            message = await channel.send(content=content, view=view)
        new_ids.append(message.id)

    # Delete any surplus messages no longer needed.
    for extra_id in existing_ids[len(views) :]:
        try:
            stale = await channel.fetch_message(extra_id)
            await stale.delete()
        except Exception:
            pass

    save_panel(channel.id, new_ids)


async def refresh_panel(client) -> None:
    """Rebuild the panel from the current soundboard (hourly task / on boot)."""
    panel = get_panel()
    if not panel:
        return

    channel = client.get_channel(panel["channel_id"])
    if channel is None:
        try:
            channel = await client.fetch_channel(panel["channel_id"])
        except Exception:
            logger.warning("Soundboard panel channel %s not found", panel["channel_id"])
            return

    await _render(channel, list(panel.get("message_ids") or []))


async def handle_setup_panel(interaction: Interaction) -> None:
    """/soundboard-panel — (re)create the button panel in the current channel."""
    await interaction.response.defer(ephemeral=True)

    # Best-effort removal of any previously-tracked panel messages.
    panel = get_panel()
    if panel:
        old_channel = interaction.client.get_channel(panel["channel_id"])
        if old_channel is not None:
            for message_id in panel.get("message_ids") or []:
                try:
                    old = await old_channel.fetch_message(message_id)
                    await old.delete()
                except Exception:
                    pass

    await _render(interaction.channel, [])
    await interaction.followup.send("✅ Soundboard panel created here.", ephemeral=True)
