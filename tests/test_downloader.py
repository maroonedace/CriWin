from pathlib import Path
from unittest.mock import patch

from src.services.media.downloader import (
    get_cookie_file,
    inject_cookies,
    is_file_too_large,
    is_instagram_url,
    is_supported_url,
)


class TestGetCookieFile:
    def test_supported_url_fetches_named_cookie(self):
        with patch(
            "src.services.media.downloader.cookies.fetch_to_cache",
            return_value=Path("/cache/cookies/youtube.txt"),
        ) as fetch:
            result = get_cookie_file("https://www.youtube.com/watch?v=abc")

        fetch.assert_called_once_with("youtube")
        assert result == "/cache/cookies/youtube.txt"

    def test_youtu_be_maps_to_youtube(self):
        with patch(
            "src.services.media.downloader.cookies.fetch_to_cache",
            return_value=Path("/c/youtube.txt"),
        ) as fetch:
            get_cookie_file("https://youtu.be/abc")

        fetch.assert_called_once_with("youtube")

    def test_instagram_url_fetches_instagram_cookie(self):
        with patch(
            "src.services.media.downloader.cookies.fetch_to_cache",
            return_value=Path("/c/instagram.txt"),
        ) as fetch:
            get_cookie_file("https://www.instagram.com/p/abc/")

        fetch.assert_called_once_with("instagram")

    def test_unsupported_url_returns_none(self):
        assert get_cookie_file("https://example.com/video") is None

    def test_missing_cookie_returns_none(self):
        with patch("src.services.media.downloader.cookies.fetch_to_cache", return_value=None):
            assert get_cookie_file("https://youtu.be/abc") is None


class TestUrlPredicates:
    def test_is_supported_url(self):
        assert is_supported_url("https://youtu.be/x") is True
        assert is_supported_url("https://example.com/x") is False

    def test_is_instagram_url(self):
        assert is_instagram_url("https://www.instagram.com/reel/x/") is True
        assert is_instagram_url("https://youtube.com/watch?v=x") is False


class TestInjectCookies:
    def test_injects_cookie_file_without_mutating_original(self):
        opts = {"quiet": True}
        result = inject_cookies(opts, "/tmp/cookies.txt")
        assert result["cookiefile"] == "/tmp/cookies.txt"
        assert "cookiefile" not in opts  # original untouched

    def test_no_cookie_returns_copy_unchanged(self):
        opts = {"quiet": True}
        result = inject_cookies(opts, None)
        assert result == {"quiet": True}
        assert result is not opts  # still a copy


class TestFileSize:
    def test_under_limit(self, tmp_path):
        f = tmp_path / "small.bin"
        f.write_bytes(b"x" * 1024)
        assert is_file_too_large(str(f), 1) is False

    def test_over_limit(self, tmp_path):
        f = tmp_path / "big.bin"
        f.write_bytes(b"x" * (2 * 1024 * 1024))
        assert is_file_too_large(str(f), 1) is True
