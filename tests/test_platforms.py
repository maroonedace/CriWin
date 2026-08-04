import pytest

from bot.media.platforms import Platform, resolve_platform


class TestResolvePlatform:
    @pytest.mark.parametrize(
        "url, expected_platform",
        [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", Platform.YOUTUBE),
            ("https://www.tiktok.com/@user/video/1234567890", Platform.TIKTOK),
            ("https://www.instagram.com/user/posts/1234567890", Platform.INSTAGRAM),
            ("https://www.reddit.com/r/subreddit/comments/1234567890", Platform.REDDIT),
            ("https://youtu.be/dQw4w9WgXcQ", Platform.YOUTUBE),
            ("https://m.youtube.com/watch?v=x", Platform.YOUTUBE),
            ("https://vm.tiktok.com/ZM123/", Platform.TIKTOK),
            ("https://old.reddit.com/r/x/comments/y", Platform.REDDIT),
            ("https://redd.it/abc", Platform.REDDIT),
        ],
    )
    def test_returns_the_platform_for_a_supported_url(self, url, expected_platform):
        assert resolve_platform(url) == expected_platform

    @pytest.mark.parametrize(
        "url",
        [
            "https://evil-youtube.com/watch?v=x",
            "https://youtube.com.evil.com/watch?v=x",
            "https://notreddit.com/r/x",
        ],
    )
    def test_returns_none_for_a_lookalike_hostname(self, url):
        assert resolve_platform(url) is None

    def test_returns_none_for_a_non_http_scheme(self):
        assert resolve_platform("ftp://www.example.com") is None

    @pytest.mark.parametrize("url", ["https://www.example.com/", "https://"])
    def test_returns_none_for_an_unsupported_host(self, url):
        assert resolve_platform(url) is None