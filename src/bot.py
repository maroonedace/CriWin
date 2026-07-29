import logging

from discord import Client, Intents, Message, Object, app_commands

from src.commands import setup_commands
from src.events import handle_dm_message

logger = logging.getLogger(__name__)


class DiscordBot(Client):
    def __init__(self, guild_id: int):
        intents = Intents.default()
        intents.voice_states = True
        intents.message_content = True

        super().__init__(intents=intents)

        self.guild = Object(id=guild_id)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        """Initialize commands and sync with Discord"""
        setup_commands(self.tree)

        logger.info("Syncing commands globally")
        await self.tree.sync()

    async def on_message(self, message: Message):
        if message.author == self.user:
            return

        if message.guild is None:
            await handle_dm_message(message)

    async def on_ready(self):
        logger.info("Logged in as %s", self.user)
