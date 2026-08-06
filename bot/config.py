import logging
import os
import sys

from dotenv import load_dotenv

from bot.constants import (
    ENVIRONMENTS,
    INVALID_ENVIRONMENT,
    INVALID_MAX_POST_MB,
    MISSING_DEV_GUILD_ID,
    MISSING_TOKEN,
    NON_NUMERIC_DEV_GUILD_ID,
    CONFIG_VALIDATED,
)
from bot.parsing import positive_int

load_dotenv()

logger = logging.getLogger(__name__)

class Config:
    ENVIRONMENT = os.getenv("ENVIRONMENT", "").lower()
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")

    MAX_POST_MB = positive_int(os.getenv("MAX_POST_MB", "50"))
    COOKIE_DIR = os.getenv("COOKIE_DIR", "/mnt/criwin/cookies")

def validate_config() -> str:
    """Validate required configuration, exiting the process if it is missing.

    Returns the validated Discord token.
    """

    if not Config.DISCORD_TOKEN:
        logger.critical(MISSING_TOKEN)
        sys.exit(1)

    if Config.ENVIRONMENT not in ENVIRONMENTS:
        logger.critical(INVALID_ENVIRONMENT, ENVIRONMENTS, Config.ENVIRONMENT)
        sys.exit(1)

    if Config.MAX_POST_MB is None:
        logger.critical(INVALID_MAX_POST_MB, os.getenv("MAX_POST_MB"))
        sys.exit(1)

    if Config.ENVIRONMENT == "development":
        if not Config.DEV_GUILD_ID:
            logger.critical(MISSING_DEV_GUILD_ID)
            sys.exit(1)
        try:
            int(Config.DEV_GUILD_ID)
        except ValueError:
            logger.critical(NON_NUMERIC_DEV_GUILD_ID, Config.DEV_GUILD_ID)
            sys.exit(1)

    logger.info(CONFIG_VALIDATED, Config.ENVIRONMENT)
    return Config.DISCORD_TOKEN
