"""Covers the shared boto3 object-storage layer (src.services.storage)."""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

import src.services.storage as storage
from src.config import Config


@pytest.fixture(autouse=True)
def _reset_client_singleton():
    storage._client = None
    yield
    storage._client = None


def _existing_bucket_client():
    client = MagicMock()
    client.head_bucket.return_value = {}  # bucket already exists
    return client


def test_get_client_builds_boto3_with_config():
    fake = _existing_bucket_client()
    with patch("src.services.storage.boto3.client", return_value=fake) as mock_boto:
        client = storage.get_client()

    assert client is fake
    args, kwargs = mock_boto.call_args
    assert args[0] == "s3"
    assert kwargs["aws_access_key_id"] == Config.STORAGE_ACCESS_KEY
    assert kwargs["aws_secret_access_key"] == Config.STORAGE_SECRET_KEY
    assert kwargs["region_name"] == Config.STORAGE_REGION
    assert kwargs["endpoint_url"].endswith(str(Config.STORAGE_ENDPOINT))


def test_endpoint_scheme_follows_secure_flag(monkeypatch):
    monkeypatch.setattr(Config, "STORAGE_SECURE", False)
    assert storage._endpoint_url().startswith("http://")
    monkeypatch.setattr(Config, "STORAGE_SECURE", True)
    assert storage._endpoint_url().startswith("https://")


def test_put_bytes_calls_put_object():
    fake = _existing_bucket_client()
    with patch("src.services.storage.boto3.client", return_value=fake):
        storage.put_bytes("soundboard/x.mp3", b"data", "audio/mpeg")

    fake.put_object.assert_called_once_with(
        Bucket=Config.STORAGE_BUCKET_NAME,
        Key="soundboard/x.mp3",
        Body=b"data",
        ContentType="audio/mpeg",
    )


def test_remove_calls_delete_object():
    fake = _existing_bucket_client()
    with patch("src.services.storage.boto3.client", return_value=fake):
        storage.remove("soundboard/x.mp3")

    fake.delete_object.assert_called_once_with(
        Bucket=Config.STORAGE_BUCKET_NAME, Key="soundboard/x.mp3"
    )


def test_bucket_created_when_missing():
    fake = MagicMock()
    fake.head_bucket.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadBucket")
    with patch("src.services.storage.boto3.client", return_value=fake):
        storage.get_client()

    fake.create_bucket.assert_called_once()
