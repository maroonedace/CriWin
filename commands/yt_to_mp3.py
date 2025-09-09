import re
import asyncio
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlparse, parse_qs

from yt_dlp import YoutubeDL
from discord import app_commands, File, Interaction

MAX_CLIP_SECONDS = 5 * 60
DOWNLOAD_DIR = Path("downloads")
AUDIO_CODEC = "mp3"
AUDIO_QUALITY = "192"  # kbps

active_downloads: set[int] = set()

YOUTUBE_REGEX = re.compile(
    r'^(https?://)?'
    r'((www\.)?youtu\.be/|((m|www)\.)?youtube\.com/)'
    r'((watch\?v=)|embed/|v/|shorts/)?'
    r'(?P<id>[\w-]{11})'
    r'([&?].*)?$'
)

def is_valid_youtube_url(url: str) -> bool:
    return bool(YOUTUBE_REGEX.match(url))

def is_playlist_url(url: str) -> bool:
    try:
        p = urlparse(url)
        qs = parse_qs(p.query)
        return "list" in qs or p.path.strip("/").startswith("playlist")
    except Exception:
        return False


YTDL_META_OPTS = {
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
    }

YTDL_DL_OPTS = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": AUDIO_CODEC,
            "preferredquality": AUDIO_QUALITY,
        }],
        "quiet": True,
        "noplaylist": True,
    }

def fetch_info(url: str) -> dict:
    with YoutubeDL(YTDL_META_OPTS) as ydl:
        info = ydl.extract_info(url, download=False)
    return info

def parse_ts(value: Optional[Union[str, int]]) -> Optional[int]:
    """
    Accepts None, int seconds, or "SS"/"MM:SS"/"HH:MM:SS".
    Returns seconds (int) or None if value is None.
    Raises ValueError on invalid input.
    """
    if value is None:
        return None
    if isinstance(value, int):
        if value < 0:
            raise ValueError("Time cannot be negative.")
        return value
    s = value.strip()
    if not s:
        return None
    if s.isdigit():
        secs = int(s)
        if secs < 0:
            raise ValueError("Time cannot be negative.")
        return secs
    parts = s.split(":")
    if not all(p.isdigit() for p in parts):
        raise ValueError("Time must be SS, MM:SS, or HH:MM:SS.")
    parts = [int(p) for p in parts]
    if len(parts) == 2:
        mm, ss = parts
        hh = 0
    elif len(parts) == 3:
        hh, mm, ss = parts
    else:
        raise ValueError("Time must be SS, MM:SS, or HH:MM:SS.")
    if ss >= 60 or mm >= 60 or min(hh, mm, ss) < 0:
        raise ValueError("Invalid timestamp.")
    return hh * 3600 + mm * 60 + ss

def download_audio_as_mp3(url: str, output_dir: Path, start_sec: int = 0, clip_sec: Optional[int] = None) -> Path:
    """
    Validate duration & live, then download+convert to MP3.
    Returns the final MP3 file path.
    """
    info = fetch_info(url)
    duration = int(info.get("duration") or 0)
    is_live = info.get("is_live", False) or info.get("live_status") == "is_live"

    if is_live:
        raise ValueError("Live streams aren't supported. Please provide a regular video URL.")

    # Defaults & caps
    start = max(0, int(start_sec))
    length = clip_sec if clip_sec is not None else MAX_CLIP_SECONDS
    length = max(1, min(int(length), MAX_CLIP_SECONDS))

    # If video duration known, cap to end
    if duration:
        if start >= duration:
            raise ValueError("Start time is beyond the end of the video.")
        if start + length > duration:
            length = duration - start  # trim to video end

    output_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = dict(YTDL_DL_OPTS)
    ydl_opts["outtmpl"] = str(output_dir / "%(title)s.%(ext)s")
    ydl_opts["postprocessor_args"] = ["-ss", str(start), "-t", str(length)]

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        original_path = Path(ydl.prepare_filename(info))  # e.g. .webm or .m4a
        mp3_path = original_path.with_suffix(".mp3")
        return mp3_path

def setup_ytmp3(tree: app_commands.CommandTree):
    @tree.command(
        name="ytmp3",
        description=f"Download a YouTube video as MP3."
    )
    @app_commands.describe(
        url="YouTube URL (single video only)",
        start="Start time (SS, MM:SS, or HH:MM:SS). Default 0.",
        length="Clip length (SS, MM:SS, or HH:MM:SS). Max 5m.",
    )
    async def yt_to_mp3(interaction: Interaction, url: str, start: Optional[str] = None, length: Optional[str] = None):
        user_id = interaction.user.id

         # One-at-a-time per user
        if user_id in active_downloads:
            return await interaction.response.send_message(
                "⚠️ You already have a download in progress.", ephemeral=True
            )

        # URL validation
        if not is_valid_youtube_url(url) or is_playlist_url(url):
            return await interaction.response.send_message(
                "🚫 Only single YouTube video URLs are supported (no playlists).",
                ephemeral=True,
            )

          # Parse times (fail fast with a friendly message)
        try:
            start_sec = parse_ts(start) or 0
            clip_sec = parse_ts(length)  # None means use default in downloader
        except ValueError as ve:
            return await interaction.response.send_message(f"❌ {ve}", ephemeral=True)

        active_downloads.add(user_id)
        await interaction.response.defer(ephemeral=True)

        try:
            # Run blocking work off-thread
            mp3_path = await asyncio.to_thread(
                download_audio_as_mp3, url, DOWNLOAD_DIR, start_sec, clip_sec
            )

            await interaction.followup.send(file=File(str(mp3_path)), ephemeral=True)

            # Best-effort cleanup
            try:
                mp3_path.unlink(missing_ok=True)
            except Exception as e:
                print(f"[ytmp3] cleanup failed: {e}")

        except Exception as e:
            # Friendly error to user; log full details to console if needed
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
        finally:
            active_downloads.discard(user_id)