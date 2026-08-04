import pytest

from bot.commands.download import download as download_module
from bot.commands.download.download import handle_download
from bot.constants import EXTRACTION_ERROR
from bot.media.platforms import Platform
from bot.media.types import MediaItem, MediaKind, MediaPost
from bot.messages import (
    EXTRACTION_FAILED,
    POST_SUMMARY,
    UNSUPPORTED_PLATFORM,
    UNTITLED_POST,
)
SOURCE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture
def post() -> MediaPost:
    return MediaPost(
        source_url=SOURCE_URL,
        platform=Platform.YOUTUBE,
        title="Test Title",
        items=(
            MediaItem(url="https://example.com/x.mp4", kind=MediaKind.VIDEO, ext="mp4"),
        ),
    )


class TestHandleDownload:
    @pytest.mark.asyncio
    async def test_reports_the_post_when_extraction_succeeds(
        self, interaction, post, monkeypatch
    ):
        extracted = []

        async def fake_extract(url):
            extracted.append(url)
            return post

        monkeypatch.setattr(download_module, "extract", fake_extract)

        await handle_download(interaction, SOURCE_URL)

        assert extracted == [SOURCE_URL]
        assert interaction.response.deferred_ephemeral is True
        assert len(interaction.sent) == 1
        assert interaction.sent[0].content == POST_SUMMARY.format(
            title="Test Title", platform=Platform.YOUTUBE, count=1
        )
        assert interaction.sent[0].ephemeral is True

    @pytest.mark.asyncio
    async def test_falls_back_to_untitled_when_the_post_has_no_title(
        self, interaction, post, monkeypatch
    ):
        async def fake_extract(url):
            return MediaPost(
                source_url=post.source_url,
                platform=post.platform,
                title=None,
                items=post.items,
            )

        monkeypatch.setattr(download_module, "extract", fake_extract)

        await handle_download(interaction, SOURCE_URL)

        assert interaction.sent[0].content == POST_SUMMARY.format(
            title=UNTITLED_POST, platform=Platform.YOUTUBE, count=1
        )

    @pytest.mark.asyncio
    async def test_refuses_an_unsupported_url(self, interaction, monkeypatch):
        async def fake_extract(url):
            return None

        monkeypatch.setattr(download_module, "extract", fake_extract)

        await handle_download(interaction, "https://www.example.com")

        assert len(interaction.sent) == 1
        assert interaction.sent[0].content == UNSUPPORTED_PLATFORM
        assert interaction.sent[0].ephemeral is True

    @pytest.mark.asyncio
    async def test_answers_when_extraction_raises(
        self, interaction, monkeypatch, caplog
    ):
        async def fake_extract(url):
            raise RuntimeError("yt-dlp exploded")

        monkeypatch.setattr(download_module, "extract", fake_extract)

        await handle_download(interaction, SOURCE_URL)

        assert len(interaction.sent) == 1
        assert interaction.sent[0].content == EXTRACTION_FAILED
        assert interaction.sent[0].ephemeral is True
        assert [record.msg for record in caplog.records] == [EXTRACTION_ERROR]
        assert "yt-dlp exploded" in caplog.text
