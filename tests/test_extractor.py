import os

import pytest
from yt_dlp import YoutubeDL

from bot.media import extractor
from bot.media.platforms import Platform
from bot.media.types import MediaItem, MediaKind, MediaPost
from bot.media.extractor import (
    build_item,
    build_post,
    direct_url,
    extract,
    selected_format,
    ytdlp_options,
)

SOURCE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

class TestExtract:
    @pytest.mark.parametrize(
        "url",
        ["invalid_url", "https://example.com/x", "file:///etc/passwd", ""],
    )
    @pytest.mark.asyncio
    async def test_returns_none_for_unsupported_url(self, url, monkeypatch):
        def fail(*_args):
            raise AssertionError("fetch_info must not run for an unsupported URL")

        monkeypatch.setattr(extractor, "fetch_info", fail)

        assert await extract(url) is None

    @pytest.mark.asyncio
    async def test_passes_the_platform_to_fetch_info(self, monkeypatch):
        """fetch_info needs the platform to pick the right cookie file."""
        seen = []

        def fake_fetch(url, platform):
            seen.append((url, platform))
            return {"ext": "mp4", "url": "https://example.com/x.mp4"}

        monkeypatch.setattr(extractor, "fetch_info", fake_fetch)

        await extract(SOURCE_URL)

        assert seen == [(SOURCE_URL, Platform.YOUTUBE)]


class TestYtdlpOptions:
    def test_omits_cookiefile_entirely_when_there_is_no_cookie(self, monkeypatch):
        monkeypatch.setattr(extractor, "cookie_file", lambda platform: None)

        assert "cookiefile" not in ytdlp_options(Platform.YOUTUBE)

    def test_passes_the_cookie_file_when_one_exists(self, monkeypatch):
        monkeypatch.setattr(
            extractor, "cookie_file", lambda platform: f"/cookies/{platform}.txt"
        )

        options = ytdlp_options(Platform.INSTAGRAM)

        assert options["cookiefile"] == "/cookies/instagram.txt"

    def test_keeps_the_shared_options(self, monkeypatch):
        monkeypatch.setattr(extractor, "cookie_file", lambda platform: "/c/x.txt")

        options = ytdlp_options(Platform.YOUTUBE)

        assert options["skip_download"] is True
        assert options["noplaylist"] is True

    def test_does_not_mutate_the_module_level_options(self, monkeypatch):
        """A cookie leaking into the shared dictionary would authenticate every
        later extraction, on every platform, for the life of the process."""
        monkeypatch.setattr(extractor, "cookie_file", lambda platform: "/c/x.txt")

        ytdlp_options(Platform.YOUTUBE)

        assert "cookiefile" not in extractor.YTDLP_OPTIONS

    def test_one_platform_cookie_does_not_reach_another(self, monkeypatch):
        monkeypatch.setattr(
            extractor,
            "cookie_file",
            lambda platform: "/c/ig.txt" if platform is Platform.INSTAGRAM else None,
        )

        assert ytdlp_options(Platform.INSTAGRAM)["cookiefile"] == "/c/ig.txt"
        assert "cookiefile" not in ytdlp_options(Platform.YOUTUBE)


class TestFetchInfo:
    """The wire between the options and yt-dlp."""

    @pytest.fixture
    def fake_ytdlp(self, monkeypatch):
        received = {}

        class FakeYoutubeDL:
            def __init__(self, options):
                received.update(options)

            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                return False

            def extract_info(self, url, download):
                assert download is False
                return {"ext": "mp4", "url": url}

            def sanitize_info(self, info):
                return info

        monkeypatch.setattr(extractor, "ReadOnlyCookieYoutubeDL", FakeYoutubeDL)

        return received

    def test_hands_the_cookie_file_to_ytdlp(self, fake_ytdlp, monkeypatch):
        monkeypatch.setattr(extractor, "cookie_file", lambda platform: "/c/ig.txt")

        extractor.fetch_info("https://instagram.com/p/x", Platform.INSTAGRAM)

        assert fake_ytdlp["cookiefile"] == "/c/ig.txt"
        assert fake_ytdlp["skip_download"] is True

    def test_omits_the_cookie_file_when_there_is_none(self, fake_ytdlp, monkeypatch):
        monkeypatch.setattr(extractor, "cookie_file", lambda platform: None)

        extractor.fetch_info(SOURCE_URL, Platform.YOUTUBE)

        assert "cookiefile" not in fake_ytdlp


class TestCookieWriteBack:
    """yt-dlp rewrites the cookie file on close unless it is stopped.

    These run against the real library rather than a fake, because the whole
    point is yt-dlp's behaviour and not our wrapper's.
    """

    @pytest.fixture
    def cookie(self, tmp_path):
        path = tmp_path / "instagram.txt"
        path.write_text(
            "# Netscape HTTP Cookie File\n"
            ".instagram.com\tTRUE\t/\tTRUE\t0\tsessionid\tabc123\n"
        )

        return path

    def options(self, cookie):
        return {"quiet": True, "no_warnings": True, "cookiefile": str(cookie)}

    def test_the_cookie_file_is_left_untouched(self, cookie):
        before = cookie.read_bytes()

        with extractor.ReadOnlyCookieYoutubeDL(self.options(cookie)):
            pass

        assert cookie.read_bytes() == before

    def test_the_plain_library_would_rewrite_it(self, cookie):
        """Pins the reason the subclass exists. If yt-dlp ever stops writing
        cookies back, or renames save_cookies, this is what notices."""
        before = cookie.read_bytes()

        with YoutubeDL(self.options(cookie)):
            pass

        assert cookie.read_bytes() != before

    @pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file permissions")
    def test_closing_does_not_raise_on_an_unwritable_cookie(self, cookie):
        """The container failure: the mount is read-only, so the write-back
        that used to happen raised OSError after extraction had succeeded."""
        cookie.chmod(0o444)

        with extractor.ReadOnlyCookieYoutubeDL(self.options(cookie)):
            pass


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