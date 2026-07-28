from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import src.commands.download.download_audio as audio_mod
from src.commands.download.constants import LIMIT_DOWNLOAD_MESSAGE, large_file_message
from src.commands.download.limits import get_max_upload_mb


class TestGetMaxUploadMb:
    def test_outside_guild_uses_default(self):
        interaction = MagicMock()
        interaction.guild = None
        assert get_max_upload_mb(interaction) == 10

    @pytest.mark.parametrize("tier,expected", [(0, 10), (1, 10), (2, 50), (3, 100)])
    def test_boost_tiers(self, tier, expected):
        interaction = MagicMock()
        interaction.guild.premium_tier = tier
        assert get_max_upload_mb(interaction) == expected

    def test_unknown_tier_falls_back_to_default(self):
        interaction = MagicMock()
        interaction.guild.premium_tier = 99
        assert get_max_upload_mb(interaction) == 10


def test_large_file_message_reports_actual_cap():
    assert "50MB" in large_file_message(50)
    assert "100MB" in large_file_message(100)


@pytest.fixture
def interaction():
    i = MagicMock()
    i.user.id = 42
    i.guild.premium_tier = 0  # 10 MB cap
    i.response.defer = AsyncMock()
    i.followup.send = AsyncMock()
    return i


@pytest.mark.asyncio
async def test_second_concurrent_download_is_blocked(interaction):
    active_downloads = {42}  # user already downloading
    with patch.object(audio_mod, "send_message", new_callable=AsyncMock) as send, \
         patch.object(audio_mod, "video_downloader") as downloader:
        await audio_mod.handle_download_audio(interaction, active_downloads, "http://x", False)

    send.assert_awaited_once_with(interaction, LIMIT_DOWNLOAD_MESSAGE)
    downloader.assert_not_called()


@pytest.mark.asyncio
async def test_oversized_file_is_rejected_with_actual_cap(interaction, tmp_path):
    active_downloads = set()
    downloaded = tmp_path / "out.mp3"
    downloaded.write_bytes(b"x")

    with patch.object(audio_mod, "video_downloader", return_value=downloaded), \
         patch.object(audio_mod, "is_file_too_large", return_value=True), \
         patch.object(audio_mod, "send_message", new_callable=AsyncMock) as send:
        await audio_mod.handle_download_audio(interaction, active_downloads, "http://x", False)

    send.assert_awaited_once_with(interaction, large_file_message(10))
    assert 42 not in active_downloads  # single-flight slot released
