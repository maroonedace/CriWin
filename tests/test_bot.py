from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from discord import Object

from src.bot import record_guilds, sync_commands


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


def _guild(guild_id: int, name: str):
    guild = MagicMock()
    guild.id = guild_id
    guild.name = name
    return guild


def test_record_guilds_upserts_each():
    with patch("src.bot.upsert_guild") as upsert:
        record_guilds([_guild(1, "A"), _guild(2, "B")])

    assert upsert.call_args_list == [call(1, "A"), call(2, "B")]


def test_record_guilds_survives_database_error():
    # A registry write failing must not break startup or a join event.
    with patch("src.bot.upsert_guild", side_effect=[ValueError("db down"), None]) as upsert:
        record_guilds([_guild(1, "A"), _guild(2, "B")])

    assert upsert.call_count == 2
