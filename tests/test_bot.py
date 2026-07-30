from unittest.mock import AsyncMock, MagicMock, call

import pytest
from discord import Object

from src.bot import sync_commands


@pytest.fixture
def tree():
    t = MagicMock()
    t.sync = AsyncMock()
    return t


@pytest.mark.asyncio
async def test_dev_syncs_to_guild_only(tree):
    guild = Object(id=42)

    await sync_commands(tree, guild, is_dev=True)

    # Guild-scoped sync is instant; no global sync in dev.
    tree.copy_global_to.assert_called_once_with(guild=guild)
    tree.sync.assert_awaited_once_with(guild=guild)
    tree.clear_commands.assert_not_called()


@pytest.mark.asyncio
async def test_prod_clears_guild_then_syncs_globally(tree):
    guild = Object(id=42)

    await sync_commands(tree, guild, is_dev=False)

    # Empty guild sync removes stale guild duplicates, then a global sync -> one each.
    tree.clear_commands.assert_called_once_with(guild=guild)
    assert tree.sync.await_args_list == [call(guild=guild), call()]
    tree.copy_global_to.assert_not_called()
