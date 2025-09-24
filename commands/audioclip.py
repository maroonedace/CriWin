import asyncio
from pathlib import Path
from typing import Optional
from discord import app_commands, File, Interaction
from utils.audioclip import validate_youtube_url, parse_ts, download_clip_mp3

DOWNLOAD_DIR = Path("downloads")
active_downloads: set[int] = set()

def setup_audioclip(tree: app_commands.CommandTree):
    @tree.command(
        name="audioclip",
        description="Turns a YouTube share link into an mp3 audio clip (up to 5 minutes)."
    )
    @app_commands.describe(
        url="YouTube Share URL",
        length="Clip length (SS, MM:SS, or HH:MM:SS). Max 5m.",
        file_name="Optional custom file name"
    )
    async def audioclip(
        interaction: Interaction, 
        url: str, 
        length: Optional[str] = None, 
        file_name: Optional[str] = None
    ):
        user_id = interaction.user.id

        # One-at-a-time per user
        if user_id in active_downloads:
            return await interaction.response.send_message(
                "⚠️ You already have a download in progress.", 
                ephemeral=True
            )

        # Validate YouTube URL
        try:
            video_id, start_time = validate_youtube_url(url)
        except ValueError as ve:
            return await interaction.response.send_message(
                f"❌ Invalid URL: {ve}", 
                ephemeral=True
            )

        # Parse clip length
        try:
            clip_sec = parse_ts(length)
        except ValueError as ve:
            return await interaction.response.send_message(
                f"❌ Invalid time format: {ve}", 
                ephemeral=True
            )

        # Construct canonical URL
        canonical_url = f"https://www.youtube.com/watch?v={video_id}"

        # Defer response and add to active downloads
        await interaction.response.defer(ephemeral=True)
        active_downloads.add(user_id)

        try:
            # Download the clip in a separate thread
            mp3_path = await asyncio.to_thread(
                download_clip_mp3, 
                canonical_url, 
                DOWNLOAD_DIR, 
                start_time, 
                clip_sec, 
                file_name
            )

            # Send the file to the user
            await interaction.followup.send(
                file=File(str(mp3_path)), 
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Download failed: {str(e)}", 
                ephemeral=True
            )
        finally:
            # Cleanup: remove from active downloads and delete file
            active_downloads.discard(user_id)
            try:
                if 'mp3_path' in locals() and mp3_path.exists():
                    mp3_path.unlink(missing_ok=True)
            except Exception as e:
                print(f"[audioclip] cleanup failed: {e}")