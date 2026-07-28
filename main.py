import sys
import asyncio
import signal
import logging

from src.config import Config, validate_config
from src import DiscordBot


def setup_logging() -> None:
    """Configure root logger for the application."""
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def main() -> None:
    logger = logging.getLogger(__name__)
    guild_id = validate_config()

    bot = DiscordBot(guild_id=guild_id)

    # Handle signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(bot, logger)))

    try:
        logger.info("Starting bot")
        async with bot:
            await bot.start(Config.DISCORD_TOKEN)
    except Exception:
        logger.exception("Bot encountered a fatal error")
        sys.exit(1)


async def shutdown(bot: DiscordBot, logger: logging.Logger) -> None:
    """Handle graceful shutdown."""
    logger.info("Shutdown signal received, closing bot")
    await bot.close()


if __name__ == "__main__":
    setup_logging()
    asyncio.run(main())
