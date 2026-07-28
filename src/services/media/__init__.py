"""Media download service (yt-dlp / gallery-dl engine).

Framework-agnostic: no Discord imports. Consumed by the download command
handlers under ``src/commands/download``.
"""

from src.services.media.downloader import (
    gallery_downloader,
    is_file_too_large,
    is_instagram_url,
    is_supported_url,
    video_downloader,
)

__all__ = [
    "gallery_downloader",
    "is_file_too_large",
    "is_instagram_url",
    "is_supported_url",
    "video_downloader",
]
