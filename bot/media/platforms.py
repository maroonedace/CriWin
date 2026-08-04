from enum import StrEnum
from urllib.parse import urlparse

class Platform(StrEnum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    REDDIT = "reddit"
    INSTAGRAM = "instagram"


PLATFORM_BY_DOMAIN = {
    "youtube.com": Platform.YOUTUBE,
    "youtu.be": Platform.YOUTUBE,
    "tiktok.com": Platform.TIKTOK,
    "reddit.com": Platform.REDDIT,
    "redd.it": Platform.REDDIT,
    "instagram.com": Platform.INSTAGRAM,
}

def resolve_platform(url: str) -> Platform | None:
    """Return the platform behind a URL, or None when it is not supported."""
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None

    for domain, platform in PLATFORM_BY_DOMAIN.items():
        if parsed.hostname == domain or parsed.hostname.endswith(f".{domain}"):
            return platform

    return None