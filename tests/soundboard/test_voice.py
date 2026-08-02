from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.commands.soundboard import voice


def _interaction(guild_id: int):
    interaction = MagicMock()
    interaction.guild.id = guild_id
    interaction.response.defer = AsyncMock()
    interaction.user.voice.channel = MagicMock()
    return interaction


@pytest.mark.asyncio
async def test_play_looks_up_sounds_in_the_clickers_guild():
    interaction = _interaction(777)

    with (
        patch.object(voice, "get_access_role_ids", return_value=[]),
        patch.object(voice, "get_sounds", return_value=[]) as get_sounds,
        patch.object(voice, "send_message", new_callable=AsyncMock),
    ):
        await voice.play_sound(interaction, "Boom")

    get_sounds.assert_called_once_with(777)


@pytest.mark.asyncio
async def test_play_rejects_a_sound_from_another_guild():
    # The panel button exists, but the sound belongs to a different server.
    interaction = _interaction(777)

    with (
        patch.object(voice, "get_access_role_ids", return_value=[]),
        patch.object(voice, "get_sounds", return_value=[]),
        patch.object(voice, "send_message", new_callable=AsyncMock) as send,
    ):
        await voice.play_sound(interaction, "Boom")

    send.assert_awaited_once_with(interaction, voice.UNAVAILABLE_SOUND_MESSAGE)
    interaction.user.voice.channel.connect.assert_not_called()
