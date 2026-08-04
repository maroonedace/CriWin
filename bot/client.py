import logging

from discord import Client, Intents, Object, app_commands
from bot.config import Config
from bot.commands.setup import setup_commands

logger = logging.getLogger(__name__)

async def sync_commands(tree: app_commands.CommandTree):
    is_dev = Config.ENVIRONMENT.lower() == "development"
    if is_dev:
        dev_guild_id = Object(id=int(Config.DEV_GUILD_ID))
        tree.copy_global_to(guild=dev_guild_id)
        await tree.sync(guild=dev_guild_id)
    else:
        await tree.sync()

class DiscordBot(Client):
    def __init__(self):
        intents = Intents.default()

        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)
    
    async def setup_hook(self):
        """Initialize commands and sync with Discord."""
        setup_commands(self.tree)

        await sync_commands(self.tree)
    
    async def on_ready(self):
        logger.info("Logged in as %s", self.user)