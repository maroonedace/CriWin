import logging

import pytest

from bot.commands.download import download as download_module
from bot.commands.download.download import handle_download
from bot.constants import EXTRACTION_ERROR, POST_REFUSED, SIZING_ERROR
from bot.media.platforms import Platform
from bot.media.sizing import PostSize, SizeVerdict
from bot.media.types import MediaItem, MediaKind, MediaPost
from bot.messages import (
    EXTRACTION_FAILED,
    POST_EMPTY,
    POST_SIZE_UNKNOWN,
    POST_SUMMARY,
    POST_TOO_LARGE,
    UNSUPPORTED_PLATFORM,
    UNTITLED_POST,
)
from bot.units import MEGABYTE

SOURCE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

LIMIT = 50 * MEGABYTE

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


def resolves_to(total: int, verdict: SizeVerdict):
    """A stand-in resolver that answers with a fixed size."""

    async def fake_resolve(post, max_bytes=None):
        return PostSize(total, verdict, LIMIT, ())

    return fake_resolve


@pytest.fixture(autouse=True)
def accepted_size(monkeypatch):
    """Keep sizing off the network by default.

    Without this every test that reaches the resolver would probe example.com
    over the real internet, which makes the suite slow and flaky.
    """
    monkeypatch.setattr(
        download_module,
        "resolve_post_size",
        resolves_to(MEGABYTE, SizeVerdict.ACCEPTED),
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
    async def test_does_not_size_an_unsupported_url(self, interaction, monkeypatch):
        async def fake_extract(url):
            return None

        async def fail(post, max_bytes=None):
            raise AssertionError("sizing must not run when there is no post")

        monkeypatch.setattr(download_module, "extract", fake_extract)
        monkeypatch.setattr(download_module, "resolve_post_size", fail)

        await handle_download(interaction, "https://www.example.com")

        assert interaction.sent[0].content == UNSUPPORTED_PLATFORM

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


@pytest.mark.usefixtures("post")
class TestSizeGate:
    @pytest.fixture(autouse=True)
    def extraction_succeeds(self, monkeypatch, post):
        async def fake_extract(url):
            return post

        monkeypatch.setattr(download_module, "extract", fake_extract)

    @pytest.mark.asyncio
    async def test_refuses_a_post_over_the_cap(self, interaction, monkeypatch, caplog):
        caplog.set_level(logging.INFO)
        monkeypatch.setattr(
            download_module,
            "resolve_post_size",
            resolves_to(60 * MEGABYTE, SizeVerdict.TOO_LARGE),
        )

        await handle_download(interaction, SOURCE_URL)

        assert len(interaction.sent) == 1
        assert interaction.sent[0].content == POST_TOO_LARGE.format(
            size="60.0", limit="50.0"
        )
        assert interaction.sent[0].ephemeral is True
        assert POST_REFUSED in [record.msg for record in caplog.records]

    @pytest.mark.asyncio
    async def test_refuses_a_post_of_unknown_size(self, interaction, monkeypatch):
        monkeypatch.setattr(
            download_module,
            "resolve_post_size",
            resolves_to(0, SizeVerdict.UNKNOWN),
        )

        await handle_download(interaction, SOURCE_URL)

        assert interaction.sent[0].content == POST_SIZE_UNKNOWN

    @pytest.mark.asyncio
    async def test_refuses_a_post_with_no_media(self, interaction, monkeypatch):
        monkeypatch.setattr(
            download_module,
            "resolve_post_size",
            resolves_to(0, SizeVerdict.EMPTY),
        )

        await handle_download(interaction, SOURCE_URL)

        assert interaction.sent[0].content == POST_EMPTY

    @pytest.mark.asyncio
    async def test_answers_when_sizing_raises(self, interaction, monkeypatch, caplog):
        async def boom(post, max_bytes=None):
            raise RuntimeError("probe exploded")

        monkeypatch.setattr(download_module, "resolve_post_size", boom)

        await handle_download(interaction, SOURCE_URL)

        assert len(interaction.sent) == 1
        assert interaction.sent[0].content == EXTRACTION_FAILED
        assert [record.msg for record in caplog.records] == [SIZING_ERROR]
        assert "probe exploded" in caplog.text
