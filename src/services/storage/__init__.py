"""Generic object storage (S3 API via boto3).

Works against MinIO (dev) or AWS S3 (prod) — the only difference is the
``endpoint_url`` and credentials. Callers deal in opaque object keys and bytes;
nothing here knows about soundboard, cookies, or Discord.
"""

import boto3
from botocore.exceptions import ClientError

from src.config import Config

_client = None


def _endpoint_url() -> str:
    scheme = "https" if Config.STORAGE_SECURE else "http"
    return f"{scheme}://{Config.STORAGE_ENDPOINT}"


def get_client():
    """Return a cached boto3 S3 client, creating the bucket if it is missing."""
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=_endpoint_url(),
            aws_access_key_id=Config.STORAGE_ACCESS_KEY,
            aws_secret_access_key=Config.STORAGE_SECRET_KEY,
            region_name=Config.STORAGE_REGION,
        )
        _ensure_bucket(_client)
    return _client


def _ensure_bucket(client) -> None:
    bucket = Config.STORAGE_BUCKET_NAME
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        params = {"Bucket": bucket}
        region = Config.STORAGE_REGION
        if region and region != "us-east-1":
            params["CreateBucketConfiguration"] = {"LocationConstraint": region}
        client.create_bucket(**params)


def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """Upload raw bytes to ``key``."""
    get_client().put_object(
        Bucket=Config.STORAGE_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def fget(key: str, dest_path) -> None:
    """Download the object at ``key`` to a local path."""
    get_client().download_file(Config.STORAGE_BUCKET_NAME, key, str(dest_path))


def remove(key: str) -> None:
    """Delete the object at ``key``."""
    get_client().delete_object(Bucket=Config.STORAGE_BUCKET_NAME, Key=key)


def presigned_url(key: str, expires_in: int = 3600) -> str:
    """Return a time-limited GET URL for ``key`` (e.g. for the admin panel)."""
    return get_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": Config.STORAGE_BUCKET_NAME, "Key": key},
        ExpiresIn=expires_in,
    )
