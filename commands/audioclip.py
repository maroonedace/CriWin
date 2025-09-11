import asyncio
from pathlib import Path
from typing import Optional

from discord import app_commands, File, Interaction
from utils.audioclip import parse_share_link, parse_ts, download_clip_mp3

DOWNLOAD_DIR = Path("downloads")
active_downloads: set[int] = set()

def setup_audioclip(tree: app_commands.CommandTree):
    @tree.command(
        name="audioclip",
        description=f"Turns a YouTube share link into an audio clip (up to 5 minutes)."
    )
    @app_commands.describe(
        url="YouTube Share URL",
        length="Clip length (SS, MM:SS, or HH:MM:SS). Max 5m.",
        file_name="Optional custom file name"
    )
    async def audioclip(interaction: Interaction, url: str, length: Optional[str] = None, file_name: Optional[str] = None):
        user_id = interaction.user.id

         # One-at-a-time per user
        if user_id in active_downloads:
            return await interaction.response.send_message(
                "⚠️ You already have a download in progress.", ephemeral=True
            )

        try:
            videoId, startTime = parse_share_link(url)
        except ValueError as ve:
            return await interaction.response.send_message(f"❌ {ve}", ephemeral=True)

        try:
            clip_sec = parse_ts(length)
        except ValueError as ve:
            return await interaction.response.send_message(f"❌ {ve}", ephemeral=True)


        canonical = f"https://www.youtube.com/watch?v={videoId}"

        active_downloads.add(user_id)
        await interaction.response.defer(ephemeral=True)

        try:
            mp3_path = await asyncio.to_thread(
                download_clip_mp3, canonical, DOWNLOAD_DIR, startTime, clip_sec, file_name
            )

            await interaction.followup.send(file=File(str(mp3_path)), ephemeral=True)

            # Best-effort cleanup
            try:
                mp3_path.unlink(missing_ok=True)
            except Exception as e:
                print(f"[audioclip] cleanup failed: {e}")

        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
        finally:
            active_downloads.discard(user_id)