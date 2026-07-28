from unittest.mock import MagicMock, patch

import pytest

import src.services.soundboard.storage as storage
from src.config import Config


@pytest.fixture(autouse=True)
def _reset_client_singleton():
    storage._minio_client = None
    yield
    storage._minio_client = None


def test_get_minio_client_passes_config():
    fake_client = MagicMock()
    fake_client.bucket_exists.return_value = True

    with patch(
        "src.services.soundboard.storage.Minio",
        return_value=fake_client,
    ) as mock_minio:
        client = storage.get_minio_client()

    assert client is fake_client
    mock_minio.assert_called_once_with(
        Config.STORAGE_ENDPOINT,
        access_key=Config.STORAGE_ACCESS_KEY,
        secret_key=Config.STORAGE_SECRET_KEY,
        region=Config.STORAGE_REGION,
        secure=Config.STORAGE_SECURE,
    )
    fake_client.bucket_exists.assert_called_once_with(Config.STORAGE_BUCKET_NAME)


def test_get_minio_client_creates_bucket_when_missing():
    fake_client = MagicMock()
    fake_client.bucket_exists.return_value = False

    with patch(
        "src.services.soundboard.storage.Minio",
        return_value=fake_client,
    ):
        storage.get_minio_client()

    fake_client.make_bucket.assert_called_once_with(Config.STORAGE_BUCKET_NAME)


def test_get_minio_client_is_cached():
    fake_client = MagicMock()
    fake_client.bucket_exists.return_value = True

    with patch(
        "src.services.soundboard.storage.Minio",
        return_value=fake_client,
    ) as mock_minio:
        storage.get_minio_client()
        storage.get_minio_client()

    mock_minio.assert_called_once()
