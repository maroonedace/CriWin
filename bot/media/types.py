from dataclasses import dataclass
from enum import StrEnum

from bot.media.platforms import Platform

class MediaKind(StrEnum):
    VIDEO = "video"
    IMAGE = "image"

@dataclass(frozen=True, slots=True)
class MediaItem:
    """One downloadable file inside a post."""
    url: str
    kind: MediaKind
    ext: str
    filesize: int | None = None
    filesize_approx: int | None = None

@dataclass(frozen=True, slots=True)
class MediaPost:
    """A post, normalized so nothing downstream touches yt-dlp's dictionary."""
    source_url: str
    platform: Platform
    title: str | None
    items: tuple[MediaItem, ...]
