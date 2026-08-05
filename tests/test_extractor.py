import pytest

from bot.media import extractor
from bot.media.platforms import Platform
from bot.media.types import MediaItem, MediaKind, MediaPost
from bot.media.extractor import (
    build_item,
    build_post,
    direct_url,
    extract,
    selected_format,
)

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

    def test_protocol_is_carried_through(self):
        entry = {
            "ext": "mp4",
            "url": "https://example.com/f",
            "protocol": "m3u8_native",
        }

        assert build_item(entry).protocol == "m3u8_native"

    def test_protocol_is_lowercased(self):
        entry = {"ext": "mp4", "url": "https://example.com/f", "protocol": "HTTPS"}

        assert build_item(entry).protocol == "https"

    def test_a_missing_protocol_is_empty(self):
        assert build_item({"ext": "mp4", "url": "https://example.com/f"}).protocol == ""

    def test_protocol_comes_from_the_same_place_as_the_url(self):
        """A selected HLS format under an entry that calls itself plain https.

        Reading the address from one dictionary and the protocol from another is
        exactly how a segmented stream would pass the size gate as a plain file.
        """
        entry = {
            "ext": "mp4",
            "protocol": "https",
            "requested_downloads": [
                {"url": "https://example.com/master.m3u8", "protocol": "m3u8_native"}
            ],
        }

        item = build_item(entry)

        assert item.url == "https://example.com/master.m3u8"
        assert item.protocol == "m3u8_native"

    def test_falls_back_to_the_entry_protocol(self):
        entry = {
            "ext": "mp4",
            "protocol": "http_dash_segments",
            "requested_downloads": [{"url": "https://example.com/manifest"}],
        }

        assert build_item(entry).protocol == "http_dash_segments"


class TestSelectedFormat:
    def test_prefers_requested_downloads_over_url_and_formats(self):
        entry = {
            "requested_downloads": [{"url": "https://example.com/best.mp4", "id": "rd"}],
            "url": "https://example.com/fallback.mp4",
            "formats": [{"url": "https://example.com/worst.mp4", "id": "fmt"}],
        }

        assert selected_format(entry)["id"] == "rd"

    def test_takes_the_last_format_as_the_best(self):
        entry = {
            "formats": [
                {"url": "https://example.com/worst.mp4", "id": "worst"},
                {"url": "https://example.com/best.mp4", "id": "best"},
            ],
        }

        assert selected_format(entry)["id"] == "best"

    def test_returns_an_empty_mapping_when_nothing_has_a_url(self):
        assert selected_format({}) == {}


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