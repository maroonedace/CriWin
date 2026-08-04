from dotenv import load_dotenv
import os

from bot.constants import ENVIRONMENTS

load_dotenv()

class Config:
    ENVIRONMENT = os.getenv("ENVIRONMENT")
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")

    if ENVIRONMENT not in ENVIRONMENTS:
        raise ValueError(
            f"ENVIRONMENT must be one of {ENVIRONMENTS}, got {ENVIRONMENT!r}"
        )
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN is not set")

    if ENVIRONMENT == "development" and not DEV_GUILD_ID:
        raise ValueError("DEV_GUILD_ID is required when ENVIRONMENT=development")