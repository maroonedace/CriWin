import re
import os
import asyncio
from yt_dlp import YoutubeDL
from discord import app_commands, File, Interaction

active_downloads: set[int] = set()
max_duration_seconds: int = 7 * 60

YOUTUBE_REGEX = re.compile(
    r'^(https?://)?'
    r'((www\.)?youtu\.be/|((m|www)\.)?youtube\.com/)'
    r'((watch\?v=)|embed/|v/)?'
    r'(?P<id>[\w-]{11})'
    r'([&?].*)?$'
)

def is_valid_youtube_url(url: str) -> bool:
    return bool(YOUTUBE_REGEX.match(url))

def download_audio_as_mp3(youtube_url: str,
                          output_dir: str = ".") -> str:
    """Download and convert a YouTube URL to MP3."""
        # Checking the metadata of the video to get duration
    meta_opts = {
        'quiet': True,
        'skip_download': True,      # yt-dlp option to not download file
    }
    with YoutubeDL(meta_opts) as meta_dl:
        info = meta_dl.extract_info(youtube_url, download=False)
        duration = info.get('duration') or 0
        is_live = info.get('is_live', False) or info.get('live_status') == 'is_live'
    
    if is_live:
        raise ValueError(
            f"❌ Live streams aren't supported. Please provide a regular uploaded video URL."
        )
        
    if duration > max_duration_seconds:
        minutes = duration // 60
        seconds = duration % 60
        raise ValueError(
            f"❌ Video is too long: {minutes}m{seconds}s (limit is {max_duration_seconds//60}m0s)."
        )
        
    opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        base = ydl.prepare_filename(info)
        return os.path.splitext(base)[0] + ".mp3"

# ── The actual slash command registration ──
def setup_ytmp3(tree: app_commands.CommandTree):
    @tree.command(
        name="ytmp3",
        description="Download a YouTube video as MP3 (≤ 7 min)."
    )
    @app_commands.describe(url="The YouTube URL to convert.")
    async def ytmp3(interaction: Interaction, url: str):
        user_id = interaction.user.id

        # 1) rate‑limit per user
        if user_id in active_downloads:
            return await interaction.response.send_message(
                "⚠️ You already have a download in progress.",
                ephemeral=True
            )

        # 2) URL sanity check
        if not is_valid_youtube_url(url):
            return await interaction.response.send_message(
                "❌ That doesn't look like a valid YouTube URL.",
                ephemeral=True,
                delete_after=10
            )

        # 3) mark & defer
        active_downloads.add(user_id)
        await interaction.response.defer(ephemeral=True)

        try:
            # 4) offload blocking download to thread
            mp3_path = await asyncio.to_thread(
                download_audio_as_mp3, url, "downloads"
            )
            await interaction.followup.send(
                file=File(mp3_path),
                ephemeral=True
            )
            try:
                os.remove(mp3_path)
            except OSError as e:
            # if you want, log this error somewhere
                print(f"Failed to delete {mp3_path}: {e}")
        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
        finally:
            active_downloads.remove(user_id)