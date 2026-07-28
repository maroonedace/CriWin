"""Central application configuration.

Single source of truth for environment-derived settings. ``load_dotenv()`` is
invoked exactly once here, so importing this module is enough to make the
configuration available to the rest of the application.
"""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables once, at import time.
load_dotenv()


class Config:
    # Discord
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    GUILD_ID = os.getenv("GUILD_ID")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # PostgreSQL database (soundboard metadata)
    POSTGRES_DB = os.getenv("POSTGRES_DB", "discord_bot")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "discord_bot")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

    # Object storage (S3 / MinIO — soundboard audio)
    STORAGE_REGION = os.getenv("STORAGE_REGION")
    STORAGE_ACCESS_KEY = os.getenv("STORAGE_ACCESS_KEY")
    STORAGE_SECRET_KEY = os.getenv("STORAGE_SECRET_KEY")
    STORAGE_ENDPOINT = os.getenv("STORAGE_ENDPOINT")
    STORAGE_BUCKET_NAME = os.getenv("STORAGE_BUCKET_NAME", "soundboard")

    # Media downloads
    DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/criwin/downloads")

    # Soundboard cache (local filesystem)
    CACHE_DIR = Path("cache")
    CACHE_FILE = CACHE_DIR / "sounds_cache.json"
    CACHE_TIMESTAMP_FILE = CACHE_DIR / "sounds_cache_timestamp.txt"
    CACHE_EXPIRY_SECONDS = 300  # 5 minutes

    # Object-storage key prefix for soundboard files
    SOUNDBOARD_DIR = "soundboard"


def validate_config() -> int:
    """Validate required configuration, exiting the process if it is missing.

    Returns the parsed integer guild id.
    """
    logger = logging.getLogger(__name__)

    if not Config.DISCORD_TOKEN:
        logger.critical("DISCORD_TOKEN is not set")
        sys.exit(1)

    if not Config.GUILD_ID:
        logger.critical("GUILD_ID is not set")
        sys.exit(1)

    try:
        return int(Config.GUILD_ID)
    except (ValueError, TypeError):
        logger.critical("GUILD_ID must be a valid integer, got: %s", Config.GUILD_ID)
        sys.exit(1)
