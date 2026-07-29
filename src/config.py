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

    # Database (PostgreSQL)
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")

    # Object storage (S3)
    STORAGE_REGION = os.getenv("STORAGE_REGION")
    STORAGE_ACCESS_KEY = os.getenv("STORAGE_ACCESS_KEY")
    STORAGE_SECRET_KEY = os.getenv("STORAGE_SECRET_KEY")
    STORAGE_ENDPOINT = os.getenv("STORAGE_ENDPOINT")
    STORAGE_BUCKET_NAME = os.getenv("STORAGE_BUCKET_NAME", "soundboard")
    STORAGE_SECURE = os.getenv("STORAGE_SECURE", "false").lower() == "true"

    # Media downloads
    DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/criwin/downloads")
    COOKIE_DIR = os.getenv("COOKIE_DIR", "/criwin/cookies")

    # Soundboard cache (local filesystem)
    CACHE_DIR = Path("cache")
    CACHE_FILE = CACHE_DIR / "sounds_cache.json"
    CACHE_TIMESTAMP_FILE = CACHE_DIR / "sounds_cache_timestamp.txt"
    CACHE_EXPIRY_SECONDS = 300  # 5 minutes

    # Object-storage key prefix for soundboard files
    SOUNDBOARD_DIR = "soundboard"

    # Admin web panel
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
    ADMIN_HOST = os.getenv("ADMIN_HOST", "0.0.0.0")
    ADMIN_PORT = int(os.getenv("ADMIN_PORT", "8080"))


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
