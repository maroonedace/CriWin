from unittest.mock import patch

import src.services.cookies as cookies
from src.services.media.constants import COOKIE_DOMAINS


def test_supported_platforms_match_cookie_domains():
    assert set(COOKIE_DOMAINS.values()) == set(cookies.SUPPORTED_COOKIE_PLATFORMS)


def test_put_cookie_stores_to_object_storage():
    with patch.object(cookies.storage, "put_bytes") as put:
        cookies.put_cookie("youtube", b"cookie-data")

    put.assert_called_once_with("cookies/youtube.txt", b"cookie-data", "text/plain")


def test_fetch_to_cache_downloads_and_returns_path(tmp_path, monkeypatch):
    monkeypatch.setattr(cookies.Config, "COOKIE_DIR", str(tmp_path))

    with patch.object(cookies.storage, "fget") as fget:
        result = cookies.fetch_to_cache("youtube")

    expected = tmp_path / "youtube.txt"
    fget.assert_called_once_with("cookies/youtube.txt", expected)
    assert result == expected


def test_fetch_to_cache_falls_back_to_local_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(cookies.Config, "COOKIE_DIR", str(tmp_path))
    local = tmp_path / "youtube.txt"
    local.write_text("local-cookie")

    with patch.object(cookies.storage, "fget", side_effect=Exception("404")):
        result = cookies.fetch_to_cache("youtube")

    assert result == local


def test_fetch_to_cache_returns_none_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(cookies.Config, "COOKIE_DIR", str(tmp_path))

    with patch.object(cookies.storage, "fget", side_effect=Exception("404")):
        assert cookies.fetch_to_cache("youtube") is None


def test_list_cookies_returns_names():
    with patch.object(
        cookies.storage,
        "list_keys",
        return_value=["cookies/youtube.txt", "cookies/instagram.txt", "cookies/"],
    ):
        names = cookies.list_cookies()

    assert set(names) == {"youtube", "instagram"}
