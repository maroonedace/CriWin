from src.services.media.downloader import (
    get_cookie_file,
    inject_cookies,
    is_file_too_large,
    is_instagram_url,
    is_supported_url,
)
from src.services.media.constants import INSTAGRAM_COOKIE_FILE, YOUTUBE_COOKIE_FILE


class TestCookieResolution:
    def test_youtube_domain(self):
        assert get_cookie_file("https://www.youtube.com/watch?v=abc") == YOUTUBE_COOKIE_FILE

    def test_youtu_be_domain(self):
        assert get_cookie_file("https://youtu.be/abc") == YOUTUBE_COOKIE_FILE

    def test_instagram_domain(self):
        assert get_cookie_file("https://www.instagram.com/p/abc/") == INSTAGRAM_COOKIE_FILE

    def test_unsupported_domain_returns_none(self):
        assert get_cookie_file("https://example.com/video") is None


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
