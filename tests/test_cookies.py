import os

import pytest

from bot.config import Config
from bot.constants import COOKIE_UNREADABLE
from bot.media.cookies import cookie_file
from bot.media.platforms import Platform

NETSCAPE_HEADER = "# Netscape HTTP Cookie File\n"


@pytest.fixture
def cookie_dir(tmp_path, monkeypatch):
    """Point COOKIE_DIR at an empty directory that exists."""
    monkeypatch.setattr(Config, "COOKIE_DIR", str(tmp_path))

    return tmp_path


def write_cookie(directory, platform: Platform):
    path = directory / f"{platform}.txt"
    path.write_text(NETSCAPE_HEADER)

    return path


class TestCookieFile:
    def test_returns_the_path_when_the_file_exists(self, cookie_dir):
        path = write_cookie(cookie_dir, Platform.INSTAGRAM)

        assert cookie_file(Platform.INSTAGRAM) == str(path)

    def test_returns_none_when_the_platform_has_no_cookie(self, cookie_dir):
        write_cookie(cookie_dir, Platform.INSTAGRAM)

        assert cookie_file(Platform.YOUTUBE) is None

    def test_returns_none_when_the_directory_is_empty(self, cookie_dir):
        assert cookie_file(Platform.YOUTUBE) is None

    def test_returns_none_when_the_directory_does_not_exist(self, monkeypatch):
        """A fresh install has no cookie directory at all. That is not an error,
        and it must not raise on the way to yt-dlp."""
        monkeypatch.setattr(Config, "COOKIE_DIR", "/nonexistent/criwin/cookies")

        assert cookie_file(Platform.YOUTUBE) is None

    def test_returns_none_when_the_path_is_a_directory(self, cookie_dir):
        (cookie_dir / f"{Platform.REDDIT}.txt").mkdir()

        assert cookie_file(Platform.REDDIT) is None

    @pytest.mark.parametrize("platform", list(Platform))
    def test_every_platform_resolves_to_its_own_file(self, cookie_dir, platform):
        path = write_cookie(cookie_dir, platform)

        assert cookie_file(platform) == str(path)
        assert cookie_file(platform).endswith(f"/{platform}.txt")

    @pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file permissions")
    def test_an_unreadable_cookie_is_reported_and_skipped(self, cookie_dir, caplog):
        path = write_cookie(cookie_dir, Platform.TIKTOK)
        path.chmod(0o000)

        assert cookie_file(Platform.TIKTOK) is None
        assert [record.msg for record in caplog.records] == [COOKIE_UNREADABLE]
