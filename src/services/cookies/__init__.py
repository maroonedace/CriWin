"""Cookie files (yt-dlp / gallery-dl) stored in object storage.

Cookies are uploaded/refreshed through the admin panel and kept in object
storage under ``cookies/<name>.txt``. The bot fetches the current cookie into a
local cache (``COOKIE_DIR/<name>.txt``) at download time, so refreshing cookies
never requires a redeploy.
"""

from pathlib import Path

from src.config import Config
from src.services import storage

COOKIE_PREFIX = "cookies"
SUPPORTED_COOKIE_PLATFORMS: tuple[str, ...] = ("instagram", "youtube")
COOKIE_PLATFORM_LABELS = {"instagram": "Instagram", "youtube": "YouTube"}


def _object_key(name: str) -> str:
    return f"{COOKIE_PREFIX}/{name}.txt"


def _local_path(name: str) -> Path:
    return Path(Config.COOKIE_DIR) / f"{name}.txt"


def put_cookie(name: str, data: bytes) -> None:
    """Store or replace a cookie file in object storage."""
    storage.put_bytes(_object_key(name), data, "text/plain")


def fetch_to_cache(name: str) -> Path | None:
    """Fetch the current cookie for ``name`` from storage into the local cache.

    Returns the local path. If the cookie is not in storage, falls back to an
    existing local copy (e.g. a legacy mount) or ``None`` if there is none.
    """
    dest = _local_path(name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        storage.fget(_object_key(name), dest)
        return dest
    except Exception:
        return dest if dest.exists() else None


def list_cookies() -> list[str]:
    """List the logical cookie names present in object storage."""
    names = []
    for key in storage.list_keys(f"{COOKIE_PREFIX}/"):
        base = key.rsplit("/", 1)[-1]
        if base.endswith(".txt"):
            names.append(base[: -len(".txt")])
    return names
