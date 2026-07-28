import os
from pathlib import Path

from src.config import Config

DOWNLOAD_DIR = Config.DOWNLOAD_DIR
COOKIE_DIR = Config.COOKIE_DIR

YOUTUBE_COOKIE_FILE = str(Path(COOKIE_DIR) / "www.youtube.com_cookies.txt")
INSTAGRAM_COOKIE_FILE = str(Path(COOKIE_DIR) / "www.instagram.com_cookies.txt")

COOKIE_MAP = {
    "youtube.com": YOUTUBE_COOKIE_FILE,
    "youtu.be": YOUTUBE_COOKIE_FILE,
    "instagram.com": INSTAGRAM_COOKIE_FILE,
}

DEFAULT_UPLOAD_LIMIT_MB = 10

BOOST_LEVEL_UPLOAD_SIZE = {
    0: 10,
    1: 10,
    2: 50,
    3: 100,
}

VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".avi", ".mov"}

# yt-dlp base configurations (cookie file is injected at download time)
YTDL_META = {
    "quiet": True,
    "skip_download": True,
    "noplaylist": True,
}

YTDL_AUDIO = {
    "format": "bestaudio/best",
    "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }
    ],
    "postprocessor_args": {
        "FFmpegExtractAudio": ["-ar", "44100"],
    },
    "quiet": True,
    "noplaylist": True,
}

YTDL_VIDEO = {
    "format": "(bestvideo[vcodec^=avc1][height<=480]+bestaudio[acodec^=mp4a])/best[vcodec^=avc1][height<=480]/best",
    "merge_output_format": "mp4",
    "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
    "quiet": True,
    "noplaylist": True,
    "postprocessors": [{
        "key": "FFmpegVideoConvertor",
        "preferedformat": "mp4",
    }],
    "writethumbnail": False,
    "embedmetadata": True,
}

# User-facing messages
LIVE_STREAM_MESSAGE = "⚠️ This is a live stream."
URL_INVALID_MESSAGE = "⚠️ This URL is invalid or the video could not be downloaded."
UNSUPPORTED_URL_MESSAGE = "⚠️ This URL is not from a supported platform."