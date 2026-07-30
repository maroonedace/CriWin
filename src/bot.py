import logging

from discord import Client, Intents, Message, Object, app_commands

from src.commands import setup_commands
from src.config import Config
from src.events import handle_dm_message

logger = logging.getLogger(__name__)

# Environments that use fast guild-scoped command sync instead of global.
DEV_ENVIRONMENTS = {"dev", "development"}


async def sync_commands(tree: app_commands.CommandTree, guild: Object, is_dev: bool) -> None:
    """Register the bot's application commands with Discord.

    Dev: copy the global commands into the test guild and sync there. Guild-scoped
    commands propagate instantly, so edits show up immediately while testing (global
    copies may also linger in dev, so a command can appear twice there — acceptable).

    Production: guarantee exactly one of each. First push an empty guild command set to
    delete any stale guild-scoped commands (left over from an earlier guild sync) so
    they stop doubling up with the global copies, then sync globally.
    """
    if is_dev:
        tree.copy_global_to(guild=guild)
        await tree.sync(guild=guild)
    else:
        tree.clear_commands(guild=guild)
        await tree.sync(guild=guild)
        await tree.sync()


class DiscordBot(Client):
    def __init__(self, guild_id: int):
        intents = Intents.default()
        intents.voice_states = True
        intents.message_content = True

        super().__init__(intents=intents)

        self.guild = Object(id=guild_id)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        """Initialize commands and sync with Discord."""
        setup_commands(self.tree)

        is_dev = Config.ENVIRONMENT.lower() in DEV_ENVIRONMENTS
        mode = "dev (guild-scoped, instant)" if is_dev else "production (global)"
        logger.info("Syncing commands: %s", mode)
        await sync_commands(self.tree, self.guild, is_dev)

    async def on_message(self, message: Message):
        if message.author == self.user:
            return

        if message.guild is None:
            await handle_dm_message(message)

    async def on_ready(self):
        logger.info("Logged in as %s", self.user)
