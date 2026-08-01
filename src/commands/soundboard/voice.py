"""Stay-connected soundboard playback.

The bot joins the clicker's voice channel on the first play and stays connected so
subsequent clicks play instantly; it interrupts the current sound on a new click and
auto-disconnects after a short idle period. Kept self-contained (no dependency on the
legacy ``/soundboard`` handler) so the slash command can be retired later.
"""

import asyncio
import logging
from pathlib import Path

from discord import FFmpegPCMAudio, Interaction, PCMVolumeTransformer

from src.commands.soundboard.access import NO_ACCESS_MESSAGE, has_panel_access
from src.commands.soundboard.constants import (
    UNAVAILABLE_SOUND_MESSAGE,
    VOICE_STATE_INVALID_MESSAGE,
)
from src.commands.soundboard.volume import resolve_volume
from src.core.messaging import send_message
from src.services.soundboard import download_sound_file, get_access_role_ids, get_sounds

logger = logging.getLogger(__name__)

IDLE_DISCONNECT_SECONDS = 300  # leave voice after 5 minutes of inactivity

# Per-guild lock serializes connect/move/play so concurrent clicks don't race the
# single voice client; per-guild idle-disconnect tasks are reset on every play.
_locks: dict[int, asyncio.Lock] = {}
_idle_tasks: dict[int, asyncio.Task] = {}


def _lock_for(guild_id: int) -> asyncio.Lock:
    lock = _locks.get(guild_id)
    if lock is None:
        lock = asyncio.Lock()
        _locks[guild_id] = lock
    return lock


def _ensure_cached(file_name: str) -> Path:
    """Return the local path for a sound, fetching it into the cache if missing."""
    file_path = Path("cache/sounds") / file_name
    if not file_path.exists():
        download_sound_file(file_name)
    return file_path


def _build_source(file_path: Path, volume: float) -> PCMVolumeTransformer:
    return PCMVolumeTransformer(FFmpegPCMAudio(str(file_path)), volume=volume)


def _cancel_idle(guild_id: int) -> None:
    task = _idle_tasks.pop(guild_id, None)
    if task and not task.done():
        task.cancel()


def _arm_idle(client, guild_id: int) -> None:
    """(Re)start the idle-disconnect countdown for a guild."""
    _cancel_idle(guild_id)

    async def _idle_disconnect() -> None:
        try:
            await asyncio.sleep(IDLE_DISCONNECT_SECONDS)
        except asyncio.CancelledError:
            return
        guild = client.get_guild(guild_id)
        vc = guild.voice_client if guild else None
        if vc and vc.is_connected() and not vc.is_playing():
            try:
                await vc.disconnect()
            except Exception:
                logger.exception("Failed to idle-disconnect from voice")

    _idle_tasks[guild_id] = client.loop.create_task(_idle_disconnect())


def _on_playback_end(client, guild_id: int, error) -> None:
    """discord.py ``after`` callback (runs off the event loop) — arm the idle timer."""
    if error:
        logger.warning("Playback error in guild %s: %s", guild_id, error)
    client.loop.call_soon_threadsafe(_arm_idle, client, guild_id)


async def play_sound(interaction: Interaction, sound_name: str) -> None:
    """Play a sound in the clicker's voice channel, staying connected between plays."""
    await interaction.response.defer(ephemeral=True)

    member = interaction.user

    allowed = set(get_access_role_ids(interaction.guild.id))
    if not has_panel_access(member, allowed):
        await send_message(interaction, NO_ACCESS_MESSAGE)
        return

    if not member.voice or not member.voice.channel:
        await send_message(interaction, VOICE_STATE_INVALID_MESSAGE)
        return

    try:
        sounds = get_sounds()
    except ValueError as err:
        await send_message(interaction, str(err))
        return

    sound_entry = next((s for s in sounds if s["name"] == sound_name), None)
    if sound_entry is None:
        await send_message(interaction, UNAVAILABLE_SOUND_MESSAGE)
        return

    guild = interaction.guild
    target = member.voice.channel
    error_message: str | None = None

    async with _lock_for(guild.id):
        try:
            file_path = _ensure_cached(sound_entry["file_name"])

            vc = guild.voice_client
            if vc is None or not vc.is_connected():
                vc = await target.connect(timeout=10.0, reconnect=True)
            elif vc.channel.id != target.id:
                await vc.move_to(target)

            if vc.is_playing():
                vc.stop()

            volume = resolve_volume(member.id, float(sound_entry.get("volume", 1.0)))
            vc.play(
                _build_source(file_path, volume),
                after=lambda err: _on_playback_end(interaction.client, guild.id, err),
            )
        except Exception as e:
            logger.exception("Soundboard panel playback failed")
            error_message = f"❌ Could not play sound: {e}"

    if error_message:
        await send_message(interaction, error_message)
    else:
        await send_message(interaction, f"▶️ Playing **{sound_name}**.")
