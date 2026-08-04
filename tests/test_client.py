import pytest

from bot.client import sync_commands
from bot.config import Config
from tests.fakes.discord import FakeCommandTree

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
