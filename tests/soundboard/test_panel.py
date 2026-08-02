from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.commands.soundboard import panel


def _sounds(n):
    return [{"name": f"sound{i}", "file_name": f"s{i}.mp3", "volume": 1.0} for i in range(n)]


class TestBuildPanelViews:
    # discord.ui.View() needs a running event loop (it creates a Future), and
    # build_panel_views is only ever called from async code, so these are async.
    @pytest.mark.asyncio
    async def test_first_view_reserves_a_row_for_the_volume_select(self):
        # 30 sounds: first message = 20 buttons + volume select (21), second = 10.
        views = panel.build_panel_views(_sounds(30))
        assert len(views) == 2
        assert len(views[0].children) == 21
        assert len(views[1].children) == 10

    @pytest.mark.asyncio
    async def test_empty_sounds_still_has_the_volume_select(self):
        views = panel.build_panel_views([])
        assert len(views) == 1
        assert views[0].children[0].custom_id == "soundboard:volume"

    @pytest.mark.asyncio
    async def test_first_view_has_buttons_then_the_volume_select(self):
        views = panel.build_panel_views([{"name": "My Sound", "file_name": "x.mp3", "volume": 1.0}])
        assert views[0].children[0].custom_id == "soundboard:play:My Sound"
        assert views[0].children[-1].custom_id == "soundboard:volume"


class TestSoundButton:
    def test_custom_id_round_trips_through_template(self):
        button = panel.SoundButton("O'Brien's Yell")
        assert button.custom_id == "soundboard:play:O'Brien's Yell"
        match = panel.SoundButton.__discord_ui_compiled_template__.match(button.custom_id)
        assert match is not None
        assert match["name"] == "O'Brien's Yell"


def _channel(channel_id: int, guild_id: int):
    channel = MagicMock(id=channel_id)
    channel.guild.id = guild_id
    channel.fetch_message = AsyncMock()
    channel.send = AsyncMock(return_value=MagicMock(id=1))
    return channel


@pytest.mark.asyncio
async def test_refresh_panel_noop_when_no_guild_has_one():
    with patch.object(panel, "get_all_panels", return_value=[]):
        client = MagicMock()
        await panel.refresh_panel(client)
        client.get_channel.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_panel_edits_existing_and_saves():
    existing = MagicMock(id=111)
    existing.edit = AsyncMock()
    channel = _channel(999, 777)
    channel.fetch_message = AsyncMock(return_value=existing)
    channel.send = AsyncMock()
    client = MagicMock()
    client.get_channel.return_value = channel

    with (
        patch.object(
            panel,
            "get_all_panels",
            return_value=[{"guild_id": 777, "channel_id": 999, "message_ids": [111]}],
        ),
        patch.object(panel, "get_sounds", return_value=_sounds(1)),
        patch.object(panel, "save_panel") as save,
    ):
        await panel.refresh_panel(client)

    existing.edit.assert_awaited_once()
    channel.send.assert_not_called()
    save.assert_called_once_with(777, 999, [111])


@pytest.mark.asyncio
async def test_refresh_panel_renders_only_that_guilds_sounds():
    channel = _channel(999, 777)
    client = MagicMock()
    client.get_channel.return_value = channel

    with (
        patch.object(
            panel,
            "get_all_panels",
            return_value=[{"guild_id": 777, "channel_id": 999, "message_ids": []}],
        ),
        patch.object(panel, "get_sounds", return_value=[]) as get_sounds,
        patch.object(panel, "save_panel"),
    ):
        await panel.refresh_panel(client)

    get_sounds.assert_called_once_with(777)


@pytest.mark.asyncio
async def test_refresh_panel_renders_every_guild():
    channels = {999: _channel(999, 777), 111: _channel(111, 888)}
    client = MagicMock()
    client.get_channel.side_effect = channels.get

    with (
        patch.object(
            panel,
            "get_all_panels",
            return_value=[
                {"guild_id": 777, "channel_id": 999, "message_ids": []},
                {"guild_id": 888, "channel_id": 111, "message_ids": []},
            ],
        ),
        patch.object(panel, "get_sounds", return_value=[]) as get_sounds,
        patch.object(panel, "save_panel") as save,
    ):
        await panel.refresh_panel(client)

    assert [c.args[0] for c in get_sounds.call_args_list] == [777, 888]
    assert [c.args[0] for c in save.call_args_list] == [777, 888]


@pytest.mark.asyncio
async def test_refresh_panel_continues_past_a_missing_channel():
    channel = _channel(111, 888)
    client = MagicMock()
    client.get_channel.side_effect = lambda cid: channel if cid == 111 else None
    client.fetch_channel = AsyncMock(side_effect=Exception("gone"))

    with (
        patch.object(
            panel,
            "get_all_panels",
            return_value=[
                {"guild_id": 777, "channel_id": 999, "message_ids": []},
                {"guild_id": 888, "channel_id": 111, "message_ids": []},
            ],
        ),
        patch.object(panel, "get_sounds", return_value=[]),
        patch.object(panel, "save_panel") as save,
    ):
        await panel.refresh_panel(client)

    save.assert_called_once_with(888, 111, [1])


@pytest.mark.asyncio
async def test_refresh_panel_sends_additional_messages():
    sent = [MagicMock(id=1), MagicMock(id=2)]
    channel = _channel(999, 777)
    channel.send = AsyncMock(side_effect=sent)
    client = MagicMock()
    client.get_channel.return_value = channel

    with (
        patch.object(
            panel,
            "get_all_panels",
            return_value=[{"guild_id": 777, "channel_id": 999, "message_ids": []}],
        ),
        patch.object(panel, "get_sounds", return_value=_sounds(30)),
        patch.object(panel, "save_panel") as save,
    ):
        await panel.refresh_panel(client)

    assert channel.send.await_count == 2
    save.assert_called_once_with(777, 999, [1, 2])


@pytest.mark.asyncio
async def test_setup_panel_only_clears_its_own_guilds_panel():
    interaction = MagicMock()
    interaction.guild.id = 777
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.channel = _channel(999, 777)

    with (
        patch.object(panel, "get_panel", return_value=None) as get_panel,
        patch.object(panel, "get_sounds", return_value=[]),
        patch.object(panel, "save_panel"),
    ):
        await panel.handle_setup_panel(interaction)

    get_panel.assert_called_once_with(777)
