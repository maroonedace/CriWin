import logging

from bot.client import DiscordBot
from bot.config import Config


def main():
    logging.basicConfig(level=logging.INFO)
    bot = DiscordBot()
    bot.run(Config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
