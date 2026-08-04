import logging

from bot.client import DiscordBot
from bot.config import validate_config

def main():
    logging.basicConfig(level=logging.INFO)
    discord_token = validate_config()
    bot = DiscordBot()
    bot.run(discord_token)


if __name__ == "__main__":
    main()
