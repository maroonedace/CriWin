import pytest

from bot.media import extractor
from bot.media.platforms import Platform
from bot.media.types import MediaItem, MediaKind, MediaPost
from bot.media.extractor import build_item, build_post, extract, direct_url

SOURCE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

class TestExtract:
    @pytest.mark.parametrize(
        "url",
        ["invalid_url", "https://example.com/x", "file:///etc/passwd", ""],
    )
    @pytest.mark.asyncio
    async def test_returns_none_for_unsupported_url(self, url, monkeypatch):
        def fail(_url):
            raise AssertionError("fetch_info must not run for an unsupported URL")

        monkeypatch.setattr(extractor, "fetch_info", fail)

        assert await extract(url) is None

class TestBuildPost:
    def test_single_post_becomes_one_item(self):
        info = {"title": "Test Title", "ext": "mp4", "url": "https://example.com/x.mp4"}

        assert build_post(SOURCE_URL, Platform.YOUTUBE, info) == MediaPost(
            source_url=SOURCE_URL,
            platform=Platform.YOUTUBE,
            title="Test Title",
            items=(
                MediaItem(
                    url="https://example.com/x.mp4", kind=MediaKind.VIDEO, ext="mp4"
                ),
            ),
        )

    def test_carousel_becomes_one_item_per_entry(self):
        info = {
            "title": "Test Gallery",
            "entries": [
                {"ext": "jpg", "url": "https://example.com/1.jpg", "filesize": 100},
                {"ext": "png", "url": "https://example.com/2.png", "filesize": 200},
            ],
        }

        post = build_post(SOURCE_URL, Platform.REDDIT, info)

        assert post.items == (
            MediaItem(
                url="https://example.com/1.jpg",
                kind=MediaKind.IMAGE,
                ext="jpg",
                filesize=100,
            ),
            MediaItem(
                url="https://example.com/2.png",
                kind=MediaKind.IMAGE,
                ext="png",
                filesize=200,
            ),
        )

    def test_missing_title_is_none(self):
        info = {"ext": "mp4", "url": "https://example.com/x.mp4"}

        assert build_post(SOURCE_URL, Platform.TIKTOK, info).title is None

    def test_empty_entries_produces_no_items(self):
        assert build_post(SOURCE_URL, Platform.REDDIT, {"entries": []}).items == ()

    def test_none_entries_are_skipped(self):
        info = {
            "entries": [{"ext": "jpg", "url": "https://example.com/1.jpg"}, None],
        }

        assert len(build_post(SOURCE_URL, Platform.REDDIT, info).items) == 1


class TestBuildItem:
    @pytest.mark.parametrize(
        "ext, expected_kind",
        [
            ("mp4", MediaKind.VIDEO),
            ("webm", MediaKind.VIDEO),
            ("jpg", MediaKind.IMAGE),
            ("JPG", MediaKind.IMAGE),
            ("png", MediaKind.IMAGE),
            ("webp", MediaKind.IMAGE),
            ("", MediaKind.VIDEO),
        ],
    )
    def test_kind_follows_the_extension(self, ext, expected_kind):
        item = build_item({"ext": ext, "url": "https://example.com/f"})

        assert item.kind is expected_kind
        assert item.ext == ext.lower()

class TestDirectUrl:

    def test_prefers_requested_downloads_over_url_and_formats(self):
        entry = {
            "requested_downloads": [{"url": "https://example.com/best.mp4"}],
            "url": "https://example.com/fallback.mp4",
            "formats": [{"url": "https://example.com/worst.mp4"}],
        }

        assert direct_url(entry) == "https://example.com/best.mp4"

    def test_prefers_url_over_formats(self):
        entry = {
            "url": "https://example.com/chosen.mp4",
            "formats": [{"url": "https://example.com/worst.mp4"}],
        }

        assert direct_url(entry) == "https://example.com/chosen.mp4"

    def test_takes_the_last_format_as_the_best(self):
        entry = {
            "formats": [
                {"url": "https://example.com/worst.mp4"},
                {"url": "https://example.com/best.mp4"},
            ],
        }

        assert direct_url(entry) == "https://example.com/best.mp4"

    def test_returns_empty_string_when_no_direct_url_is_found(self):
        entry = {}
        assert direct_url(entry) == ""