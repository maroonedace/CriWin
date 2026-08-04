import pytest

from bot.client import sync_commands
from bot.config import Config


class FakeCommandTree:
    """Stands in for discord.app_commands.CommandTree, recording what was called.

    Both methods are keyword-only, matching the real signatures, so a call that
    would fail against discord.py fails here too.
    """

    def __init__(self):
        self.copied_to = []
        self.synced_to = []

    def copy_global_to(self, *, guild):
        self.copied_to.append(guild)

    async def sync(self, *, guild=None):
        self.synced_to.append(guild)


@pytest.mark.usefixtures("valid_config")
class TestSyncCommands:
    @pytest.mark.asyncio
    async def test_development_syncs_to_the_dev_guild(self):
        tree = FakeCommandTree()

        await sync_commands(tree)

        assert [guild.id for guild in tree.copied_to] == [123456789]
        assert [guild.id for guild in tree.synced_to] == [123456789]

    @pytest.mark.asyncio
    async def test_production_syncs_globally(self, monkeypatch):
        monkeypatch.setattr(Config, "ENVIRONMENT", "production")
        tree = FakeCommandTree()

        await sync_commands(tree)

        assert not tree.copied_to
        assert tree.synced_to == [None]
