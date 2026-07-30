from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.commands.soundboard import panel


def _sounds(n):
    return [{"name": f"sound{i}", "file_name": f"s{i}.mp3", "volume": 1.0} for i in range(n)]


class TestBuildPanelViews:
    # discord.ui.View() needs a running event loop (it creates a Future), and
    # build_panel_views is only ever called from async code, so these are async.
    @pytest.mark.asyncio
    async def test_chunks_into_25(self):
        views = panel.build_panel_views(_sounds(30))
        assert len(views) == 2
        assert len(views[0].children) == 25
        assert len(views[1].children) == 5

    def test_empty_sounds_yields_no_views(self):
        assert panel.build_panel_views([]) == []

    @pytest.mark.asyncio
    async def test_button_custom_ids_encode_name(self):
        views = panel.build_panel_views([{"name": "My Sound", "file_name": "x.mp3", "volume": 1.0}])
        assert views[0].children[0].custom_id == "soundboard:play:My Sound"


class TestSoundButton:
    def test_custom_id_round_trips_through_template(self):
        button = panel.SoundButton("O'Brien's Yell")
        assert button.custom_id == "soundboard:play:O'Brien's Yell"
        match = panel.SoundButton.__discord_ui_compiled_template__.match(button.custom_id)
        assert match is not None
        assert match["name"] == "O'Brien's Yell"


@pytest.mark.asyncio
async def test_refresh_panel_noop_when_unset():
    with patch.object(panel, "get_panel", return_value=None):
        client = MagicMock()
        await panel.refresh_panel(client)
        client.get_channel.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_panel_edits_existing_and_saves():
    existing = MagicMock(id=111)
    existing.edit = AsyncMock()
    channel = MagicMock(id=999)
    channel.fetch_message = AsyncMock(return_value=existing)
    channel.send = AsyncMock()
    client = MagicMock()
    client.get_channel.return_value = channel

    with (
        patch.object(panel, "get_panel", return_value={"channel_id": 999, "message_ids": [111]}),
        patch.object(panel, "get_sounds", return_value=_sounds(1)),
        patch.object(panel, "save_panel") as save,
    ):
        await panel.refresh_panel(client)

    existing.edit.assert_awaited_once()
    channel.send.assert_not_called()
    save.assert_called_once_with(999, [111])


@pytest.mark.asyncio
async def test_refresh_panel_sends_additional_messages():
    sent = [MagicMock(id=1), MagicMock(id=2)]
    channel = MagicMock(id=999)
    channel.send = AsyncMock(side_effect=sent)
    channel.fetch_message = AsyncMock()
    client = MagicMock()
    client.get_channel.return_value = channel

    with (
        patch.object(panel, "get_panel", return_value={"channel_id": 999, "message_ids": []}),
        patch.object(panel, "get_sounds", return_value=_sounds(30)),
        patch.object(panel, "save_panel") as save,
    ):
        await panel.refresh_panel(client)

    assert channel.send.await_count == 2
    save.assert_called_once_with(999, [1, 2])
