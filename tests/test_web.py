from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import src.web.app as webapp
from src.config import Config

AUTH = ("admin", "secret")
GUILD = 1
GUILDS = [{"guild_id": GUILD, "name": "Test Server"}, {"guild_id": 2, "name": "Other Server"}]


@pytest.fixture(autouse=True)
def _set_admin_credentials(monkeypatch):
    monkeypatch.setattr(Config, "ADMIN_USERNAME", "admin")
    monkeypatch.setattr(Config, "ADMIN_PASSWORD", "secret")


@pytest.fixture(autouse=True)
def _known_guilds(monkeypatch):
    """Sounds are per-server, so every route resolves a guild from this registry."""
    monkeypatch.setattr(webapp, "get_guilds", lambda: GUILDS)


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
    assert "Instagram" in response.text
    assert "YouTube" in response.text
    assert "/cookies/youtube" in response.text
    assert "Set" in response.text
    assert "Not set" in response.text


def test_index_defaults_to_the_first_server(client):
    with (
        patch.object(webapp, "get_sounds", return_value=[]) as get_sounds,
        patch.object(webapp, "list_cookies", return_value=[]),
    ):
        response = client.get("/", auth=AUTH)

    get_sounds.assert_called_once_with(GUILD)
    assert "Test Server" in response.text
    assert "Other Server" in response.text


def test_index_honours_the_selected_server(client):
    with (
        patch.object(webapp, "get_sounds", return_value=[]) as get_sounds,
        patch.object(webapp, "list_cookies", return_value=[]),
    ):
        client.get("/?guild_id=2", auth=AUTH)

    get_sounds.assert_called_once_with(2)


def test_index_falls_back_when_server_is_unknown(client):
    with (
        patch.object(webapp, "get_sounds", return_value=[]) as get_sounds,
        patch.object(webapp, "list_cookies", return_value=[]),
    ):
        client.get("/?guild_id=404", auth=AUTH)

    get_sounds.assert_called_once_with(GUILD)


def test_index_without_servers_skips_the_sound_query(client, monkeypatch):
    monkeypatch.setattr(webapp, "get_guilds", list)
    with (
        patch.object(webapp, "get_sounds") as get_sounds,
        patch.object(webapp, "list_cookies", return_value=[]),
    ):
        response = client.get("/", auth=AUTH)

    assert response.status_code == 200
    assert "No servers yet" in response.text
    get_sounds.assert_not_called()


def test_upload_sound_calls_service(client):
    with (
        patch.object(webapp, "get_sounds", return_value=[]),
        patch.object(webapp, "upload_sound_file", new_callable=AsyncMock) as upload,
    ):
        response = client.post(
            "/sounds",
            auth=AUTH,
            data={"name": "Boom", "guild_id": GUILD},
            files={"file": ("boom.mp3", b"audio-bytes", "audio/mpeg")},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == f"/?guild_id={GUILD}"
    upload.assert_awaited_once_with(GUILD, "Boom", b"audio-bytes", "boom.mp3", "audio/mpeg")


def test_upload_to_unknown_server_404(client):
    with (
        patch.object(webapp, "get_sounds", return_value=[]),
        patch.object(webapp, "upload_sound_file", new_callable=AsyncMock) as upload,
    ):
        response = client.post(
            "/sounds",
            auth=AUTH,
            data={"name": "Boom", "guild_id": 404},
            files={"file": ("boom.mp3", b"audio-bytes", "audio/mpeg")},
            follow_redirects=False,
        )

    assert response.status_code == 404
    upload.assert_not_awaited()


def test_upload_invalid_name_rejected(client):
    with (
        patch.object(webapp, "get_sounds", return_value=[]),
        patch.object(webapp, "upload_sound_file", new_callable=AsyncMock) as upload,
    ):
        response = client.post(
            "/sounds",
            auth=AUTH,
            data={"name": "bad~name", "guild_id": GUILD},
            files={"file": ("boom.mp3", b"audio-bytes", "audio/mpeg")},
            follow_redirects=False,
        )

    assert response.status_code == 400
    upload.assert_not_awaited()


def test_upload_duplicate_name_rejected(client):
    with (
        patch.object(
            webapp,
            "get_sounds",
            return_value=[{"name": "Boom", "file_name": "boom.mp3", "volume": 1.0}],
        ),
        patch.object(webapp, "upload_sound_file", new_callable=AsyncMock) as upload,
    ):
        response = client.post(
            "/sounds",
            auth=AUTH,
            data={"name": "Boom", "guild_id": GUILD},
            files={"file": ("boom2.mp3", b"audio-bytes", "audio/mpeg")},
            follow_redirects=False,
        )

    assert response.status_code == 400
    upload.assert_not_awaited()


def test_duplicate_name_allowed_in_another_server(client):
    # Display names are unique per server, so the same name may exist in each.
    def sounds_for(guild_id):
        return [{"name": "Boom", "file_name": "1_boom.mp3", "volume": 1.0}] if guild_id == 1 else []

    with (
        patch.object(webapp, "get_sounds", side_effect=sounds_for),
        patch.object(webapp, "upload_sound_file", new_callable=AsyncMock) as upload,
    ):
        response = client.post(
            "/sounds",
            auth=AUTH,
            data={"name": "Boom", "guild_id": 2},
            files={"file": ("boom.mp3", b"audio-bytes", "audio/mpeg")},
            follow_redirects=False,
        )

    assert response.status_code == 303
    upload.assert_awaited_once_with(2, "Boom", b"audio-bytes", "boom.mp3", "audio/mpeg")


def test_delete_sound_resolves_file_name(client):
    with (
        patch.object(
            webapp,
            "get_sounds",
            return_value=[{"name": "Boom", "file_name": "1_boom.mp3", "volume": 1.0}],
        ),
        patch.object(webapp, "delete_sound", new_callable=AsyncMock) as delete,
    ):
        response = client.post(
            "/sounds/Boom/delete", auth=AUTH, data={"guild_id": GUILD}, follow_redirects=False
        )

    assert response.status_code == 303
    delete.assert_awaited_once_with(GUILD, "Boom", "1_boom.mp3")


def test_delete_unknown_sound_404(client):
    with (
        patch.object(webapp, "get_sounds", return_value=[]),
        patch.object(webapp, "delete_sound", new_callable=AsyncMock) as delete,
    ):
        response = client.post(
            "/sounds/Ghost/delete", auth=AUTH, data={"guild_id": GUILD}, follow_redirects=False
        )

    assert response.status_code == 404
    delete.assert_not_called()


def test_delete_sound_from_another_server_404(client):
    # The sound exists, but not in the server the request names.
    def sounds_for(guild_id):
        return [{"name": "Boom", "file_name": "1_boom.mp3", "volume": 1.0}] if guild_id == 1 else []

    with (
        patch.object(webapp, "get_sounds", side_effect=sounds_for),
        patch.object(webapp, "delete_sound", new_callable=AsyncMock) as delete,
    ):
        response = client.post(
            "/sounds/Boom/delete", auth=AUTH, data={"guild_id": 2}, follow_redirects=False
        )

    assert response.status_code == 404
    delete.assert_not_called()


def test_rename_sound_calls_service(client):
    with (
        patch.object(
            webapp,
            "get_sounds",
            return_value=[{"name": "Boom", "file_name": "1_boom.mp3", "volume": 1.0}],
        ),
        patch.object(webapp, "rename_sound") as rename,
    ):
        response = client.post(
            "/sounds/Boom/rename",
            auth=AUTH,
            data={"new_name": "Bang", "guild_id": GUILD},
            follow_redirects=False,
        )

    assert response.status_code == 303
    rename.assert_called_once_with(GUILD, "Boom", "Bang")


def test_rename_unknown_sound_404(client):
    with (
        patch.object(webapp, "get_sounds", return_value=[]),
        patch.object(webapp, "rename_sound") as rename,
    ):
        response = client.post(
            "/sounds/Ghost/rename",
            auth=AUTH,
            data={"new_name": "Boo", "guild_id": GUILD},
            follow_redirects=False,
        )

    assert response.status_code == 404
    rename.assert_not_called()


def test_rename_invalid_name_rejected(client):
    with (
        patch.object(
            webapp,
            "get_sounds",
            return_value=[{"name": "Boom", "file_name": "1_boom.mp3", "volume": 1.0}],
        ),
        patch.object(webapp, "rename_sound") as rename,
    ):
        response = client.post(
            "/sounds/Boom/rename",
            auth=AUTH,
            data={"new_name": "bad~name", "guild_id": GUILD},
            follow_redirects=False,
        )

    assert response.status_code == 400
    rename.assert_not_called()


def test_rename_duplicate_name_rejected(client):
    with (
        patch.object(
            webapp,
            "get_sounds",
            return_value=[
                {"name": "Boom", "file_name": "1_boom.mp3", "volume": 1.0},
                {"name": "Bang", "file_name": "1_bang.mp3", "volume": 1.0},
            ],
        ),
        patch.object(webapp, "rename_sound") as rename,
    ):
        response = client.post(
            "/sounds/Boom/rename",
            auth=AUTH,
            data={"new_name": "Bang", "guild_id": GUILD},
            follow_redirects=False,
        )

    assert response.status_code == 400
    rename.assert_not_called()


def test_set_volume_calls_service(client):
    with patch.object(webapp, "set_volume") as set_vol:
        response = client.post(
            "/sounds/Boom/volume",
            auth=AUTH,
            data={"volume": "0.5", "guild_id": GUILD},
            follow_redirects=False,
        )

    assert response.status_code == 303
    set_vol.assert_called_once_with(GUILD, "Boom", 0.5)


def test_upload_cookie_calls_service(client):
    with patch.object(webapp, "put_cookie") as put:
        response = client.post(
            "/cookies/youtube",
            auth=AUTH,
            files={"file": ("cookies.txt", b"cookie-data", "text/plain")},
            follow_redirects=False,
        )

    assert response.status_code == 303
    put.assert_called_once_with("youtube", b"cookie-data")


def test_upload_cookie_unknown_platform_404(client):
    with patch.object(webapp, "put_cookie") as put:
        response = client.post(
            "/cookies/tiktok",
            auth=AUTH,
            files={"file": ("cookies.txt", b"cookie-data", "text/plain")},
            follow_redirects=False,
        )

    assert response.status_code == 404
    put.assert_not_called()
