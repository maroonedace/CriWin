from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import src.web.app as webapp
from src.config import Config

AUTH = ("admin", "secret")


@pytest.fixture(autouse=True)
def _set_admin_credentials(monkeypatch):
    monkeypatch.setattr(Config, "ADMIN_USERNAME", "admin")
    monkeypatch.setattr(Config, "ADMIN_PASSWORD", "secret")


@pytest.fixture
def client():
    return TestClient(webapp.app)


def test_index_requires_auth(client):
    assert client.get("/").status_code == 401


def test_wrong_password_rejected(client):
    assert client.get("/", auth=("admin", "wrong")).status_code == 401


def test_wrong_username_rejected(client):
    assert client.get("/", auth=("nope", "secret")).status_code == 401


def test_non_ascii_credentials_rejected_not_500(client):
    # Regression: secrets.compare_digest raises TypeError on non-ASCII str, which
    # used to surface as a 500 and stop the browser from re-prompting.
    assert client.get("/", auth=("admin", "pÃ¡sswörd")).status_code == 401


def test_unset_credentials_reject_everything(client, monkeypatch):
    monkeypatch.setattr(Config, "ADMIN_USERNAME", None)
    monkeypatch.setattr(Config, "ADMIN_PASSWORD", None)
    # Empty credentials must not authenticate when nothing is configured.
    assert client.get("/", auth=("", "")).status_code == 401


def test_index_lists_sounds_and_cookies(client):
    with (
        patch.object(
            webapp,
            "get_sounds",
            return_value=[{"name": "Boom", "file_name": "boom.mp3", "volume": 1.0}],
        ),
        patch.object(webapp, "list_cookies", return_value=["youtube"]),
    ):
        response = client.get("/", auth=AUTH)

    assert response.status_code == 200
    assert "Boom" in response.text
    assert "youtube" in response.text


def test_upload_sound_calls_service(client):
    with patch.object(webapp, "upload_sound_file", new_callable=AsyncMock) as upload:
        response = client.post(
            "/sounds",
            auth=AUTH,
            data={"name": "Boom"},
            files={"file": ("boom.mp3", b"audio-bytes", "audio/mpeg")},
            follow_redirects=False,
        )

    assert response.status_code == 303
    upload.assert_awaited_once_with("Boom", b"audio-bytes", "boom.mp3", "audio/mpeg")


def test_delete_sound_resolves_file_name(client):
    with (
        patch.object(
            webapp,
            "get_sounds",
            return_value=[{"name": "Boom", "file_name": "boom.mp3", "volume": 1.0}],
        ),
        patch.object(webapp, "delete_sound", new_callable=AsyncMock) as delete,
    ):
        response = client.post("/sounds/Boom/delete", auth=AUTH, follow_redirects=False)

    assert response.status_code == 303
    delete.assert_awaited_once_with("Boom", "boom.mp3")


def test_delete_unknown_sound_404(client):
    with (
        patch.object(webapp, "get_sounds", return_value=[]),
        patch.object(webapp, "delete_sound", new_callable=AsyncMock) as delete,
    ):
        response = client.post("/sounds/Ghost/delete", auth=AUTH, follow_redirects=False)

    assert response.status_code == 404
    delete.assert_not_called()


def test_set_volume_calls_service(client):
    with patch.object(webapp, "set_volume") as set_vol:
        response = client.post(
            "/sounds/Boom/volume", auth=AUTH, data={"volume": "0.5"}, follow_redirects=False
        )

    assert response.status_code == 303
    set_vol.assert_called_once_with("Boom", 0.5)


def test_upload_cookie_calls_service(client):
    with patch.object(webapp, "put_cookie") as put:
        response = client.post(
            "/cookies",
            auth=AUTH,
            data={"name": "youtube"},
            files={"file": ("cookies.txt", b"cookie-data", "text/plain")},
            follow_redirects=False,
        )

    assert response.status_code == 303
    put.assert_called_once_with("youtube", b"cookie-data")
