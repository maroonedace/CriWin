from io import BytesIO

import discord
from minio import Minio

from src.config import Config
from src.services.soundboard.cache import SoundCache
from src.services.soundboard.errors import ErrorMessages

_minio_client = None  # cached module-level client


def get_minio_client() -> Minio:
    """Get MinIO client (cached module-level singleton)."""
    global _minio_client
    if _minio_client is None:
        try:
            _minio_client = Minio(
                Config.STORAGE_ENDPOINT,
                access_key=Config.STORAGE_ACCESS_KEY,
                secret_key=Config.STORAGE_SECRET_KEY,
                region=Config.STORAGE_REGION,
                secure=Config.STORAGE_SECURE
            )

            # Ensure bucket exists
            if not _minio_client.bucket_exists(Config.STORAGE_BUCKET_NAME):
                _minio_client.make_bucket(Config.STORAGE_BUCKET_NAME)

        except Exception as e:
            raise ValueError(f"{ErrorMessages.S3_CLIENT}: {str(e)}")
    return _minio_client


class S3Operations:
    @staticmethod
    async def upload_file(file: discord.Attachment) -> None:
        """Upload file to object storage"""
        client = get_minio_client()
        try:
            file_data = await file.read()

            client.put_object(
                Config.STORAGE_BUCKET_NAME,
                f"{Config.SOUNDBOARD_DIR}/{file.filename}",
                BytesIO(file_data),
                length=len(file_data),
                content_type=file.content_type or "application/octet-stream"
            )
        except Exception as e:
            raise ValueError(f"{ErrorMessages.UPLOAD_S3}: {str(e)}")

    @staticmethod
    def delete_file(file_name: str) -> None:
        """Delete file from object storage"""
        client = get_minio_client()
        try:
            client.remove_object(
                Config.STORAGE_BUCKET_NAME,
                f"{Config.SOUNDBOARD_DIR}/{file_name}"
            )
        except Exception as e:
            raise ValueError(f"{ErrorMessages.DELETE_S3}: {str(e)}")

    @staticmethod
    def download_file(file_name: str) -> None:
        """Download file from object storage to the local cache"""
        client = get_minio_client()
        try:
            local_path = Config.CACHE_DIR / "sounds" / file_name
            SoundCache.ensure_cache_dir()

            client.fget_object(
                Config.STORAGE_BUCKET_NAME,
                f"{Config.SOUNDBOARD_DIR}/{file_name}",
                str(local_path)
            )
        except Exception as e:
            raise ValueError(f"{ErrorMessages.DOWNLOAD_SOUND}: {str(e)}")
