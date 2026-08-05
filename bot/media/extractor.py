import asyncio
import logging

from yt_dlp import YoutubeDL

from bot.media.platforms import Platform, resolve_platform
from bot.media.types import MediaItem, MediaKind, MediaPost

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = frozenset({"gif", "heic", "jpeg", "jpg", "png", "webp"})

YTDLP_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "noplaylist": True,
}


async def extract(url: str) -> MediaPost | None:
    """Describe the media behind a URL without fetching it.

    Returns None when the URL is not one of the supported platforms.
    """
    platform = resolve_platform(url)
    if platform is None:
        return None

    info = await asyncio.to_thread(fetch_info, url)

    return build_post(url, platform, info)


def fetch_info(url: str) -> dict:
    """Ask yt-dlp what is behind a URL.

    Blocking, so it is only ever reached through a worker thread.
    """
    with YoutubeDL(YTDLP_OPTIONS) as ydl:
        info = ydl.extract_info(url, download=False)

        return ydl.sanitize_info(info)


def build_post(source_url: str, platform: Platform, info: dict) -> MediaPost:
    """Normalize a yt-dlp result into a MediaPost.

    A single post and a carousel differ only in whether yt-dlp reported an
    "entries" list, so both collapse to the same shape here.
    """
    entries = info.get("entries")
    raw_entries = list(entries) if entries is not None else [info]
    items = tuple(build_item(entry) for entry in raw_entries if entry)

    if not items:
        logger.warning("Extraction returned no media items for %s", source_url)

    return MediaPost(
        source_url=source_url,
        platform=platform,
        title=info.get("title"),
        items=items,
    )


def build_item(entry: dict) -> MediaItem:
    """Normalize one yt-dlp entry into a MediaItem."""
    selected = selected_format(entry)
    ext = (entry.get("ext") or "").lower()

    return MediaItem(
        url=selected.get("url", ""),
        kind=MediaKind.IMAGE if ext in IMAGE_EXTENSIONS else MediaKind.VIDEO,
        ext=ext,
        protocol=(selected.get("protocol") or entry.get("protocol") or "").lower(),
        filesize=entry.get("filesize"),
        filesize_approx=entry.get("filesize_approx"),
    )


def selected_format(entry: dict) -> dict:
    """The part of a yt-dlp entry that describes the bytes to fetch."""
    requested_downloads = entry.get("requested_downloads") or []
    if requested_downloads and requested_downloads[0].get("url"):
        return requested_downloads[0]

    if entry.get("url"):
        return entry

    formats = entry.get("formats") or []
    if formats and formats[-1].get("url"):
        return formats[-1]

    return {}


def direct_url(entry: dict) -> str:
    """The address the bytes actually live at."""
    return selected_format(entry).get("url", "")
