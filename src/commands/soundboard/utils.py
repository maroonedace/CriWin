import json
import os
from pathlib import Path
import time
from typing import Any, Dict, List
import psycopg2
from psycopg2.extras import RealDictCursor
from minio import Minio
from discord import app_commands
import discord
from dotenv import load_dotenv


# Setting up to load ENV values
load_dotenv()

class Config:
    # Cache configuration
    CACHE_DIR = Path("cache")
    CACHE_FILE = CACHE_DIR / "sounds_cache.json"
    CACHE_TIMESTAMP_FILE = CACHE_DIR / "sounds_cache_timestamp.txt"
    CACHE_EXPIRY_SECONDS = 300  # 5 minutes

    # PostgreSQL Database
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB = os.getenv("POSTGRES_DB", "discord_bot")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "discord_bot")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

    # MinIO S3
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
    MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "soundboard")
    MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "false").lower() == "true"

    # Soundboard directory
    SOUNDBOARD_DIR = "soundboard"


class ErrorMessages:
    DATABASE_CLIENT = "❌ Could not connect to the database client."
    S3_CLIENT = "❌ Could not connect to the storage client."
    DATABASE = "Could not connect to database."
    DOWNLOAD_SOUND = "❌ Could not download sound"
    NO_SOUNDS = "❌ No sounds available."
    UPLOAD_S3 = "Could not upload sound file to S3."
    UPLOAD_DATABASE = "Could not upload sound file to database."
    DELETE_S3 = "Could not delete sound file from S3 storage."
    DELETE_DATABASE = "Could not delete sound from database."


class Sound:
    def __init__(self, name: str, file_name: str):
        self.name = name
        self.file_name = file_name


class SoundCache:
    @staticmethod
    def ensure_cache_dir():
        """Ensure cache directory exists"""
        Config.CACHE_DIR.mkdir(exist_ok=True)
        (Config.CACHE_DIR / "sounds").mkdir(exist_ok=True)

    @staticmethod
    def is_valid() -> bool:
        """Check if cache is still valid"""
        if not Config.CACHE_TIMESTAMP_FILE.exists():
            return False

        try:
            with open(Config.CACHE_TIMESTAMP_FILE, "r") as f:
                timestamp = float(f.read().strip())
            return (time.time() - timestamp) < Config.CACHE_EXPIRY_SECONDS
        except (ValueError, IOError):
            return False

    @staticmethod
    def save(sounds_data: List[Dict[str, Any]]):
        """Save sounds data to cache"""
        SoundCache.ensure_cache_dir()

        with open(Config.CACHE_FILE, "w") as f:
            json.dump(sounds_data, f)

        with open(Config.CACHE_TIMESTAMP_FILE, "w") as f:
            f.write(str(time.time()))

    @staticmethod
    def load() -> List[Dict[str, Any]]:
        """Load sounds data from cache"""
        if not Config.CACHE_FILE.exists():
            return []

        try:
            with open(Config.CACHE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    @staticmethod
    def invalidate():
        """Invalidate the sounds cache"""
        Config.CACHE_FILE.unlink(missing_ok=True)
        Config.CACHE_TIMESTAMP_FILE.unlink(missing_ok=True)


class ClientFactory:
    _db_connection = None  # Connection pooling
    _minio_client = None

    @staticmethod
    def get_database_connection():
        """Get PostgreSQL database connection with connection pooling"""
        if ClientFactory._db_connection is None or ClientFactory._db_connection.closed:
            try:
                ClientFactory._db_connection = psycopg2.connect(
                    host=Config.POSTGRES_HOST,
                    port=Config.POSTGRES_PORT,
                    database=Config.POSTGRES_DB,
                    user=Config.POSTGRES_USER,
                    password=Config.POSTGRES_PASSWORD,
                    connect_timeout=10
                )
            except Exception as e:
                raise ValueError(f"{ErrorMessages.DATABASE_CLIENT}: {str(e)}")
        return ClientFactory._db_connection

    @staticmethod
    def get_minio_client() -> Minio:
        """Get MinIO client"""
        if ClientFactory._minio_client is None:
            try:
                ClientFactory._minio_client = Minio(
                    Config.MINIO_ENDPOINT,
                    access_key=Config.MINIO_ACCESS_KEY,
                    secret_key=Config.MINIO_SECRET_KEY,
                    secure=Config.MINIO_USE_SSL
                )
                
                # Ensure bucket exists
                if not ClientFactory._minio_client.bucket_exists(Config.MINIO_BUCKET_NAME):
                    ClientFactory._minio_client.make_bucket(Config.MINIO_BUCKET_NAME)
                    
            except Exception as e:
                raise ValueError(f"{ErrorMessages.S3_CLIENT}: {str(e)}")
        return ClientFactory._minio_client


class DatabaseOperations:
    @staticmethod
    def get_all_sounds() -> List[Dict[str, Any]]:
        """Get all sounds from database"""

        conn = ClientFactory.get_database_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT name, file_name FROM sounds ORDER BY name;")
                sound_items = cursor.fetchall()
                
                # Convert to list of dicts
                sound_items = [dict(row) for row in sound_items]
        except Exception as e:
            conn.rollback()
            raise ValueError(f"{ErrorMessages.DATABASE}: {str(e)}")

        SoundCache.save(sound_items)
        return sound_items

    @staticmethod
    def add_sound(name: str, file_name: str) -> None:
        """Add sound to database"""
        conn = ClientFactory.get_database_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO sounds (name, file_name) VALUES (%s, %s);",
                    (name, file_name)
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"{ErrorMessages.UPLOAD_DATABASE}: {str(e)}")

    @staticmethod
    def delete_sound(name: str) -> None:
        """Delete sound from database"""
        conn = ClientFactory.get_database_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM sounds WHERE name = %s;",
                    (name,)
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"{ErrorMessages.DELETE_DATABASE}: {str(e)}")


class S3Operations:
    @staticmethod
    async def upload_file(file: discord.Attachment) -> None:
        """Upload file to MinIO"""
        client = ClientFactory.get_minio_client()
        try:
            file_data = await file.read()
            from io import BytesIO
            
            client.put_object(
                Config.MINIO_BUCKET_NAME,
                f"{Config.SOUNDBOARD_DIR}/{file.filename}",
                BytesIO(file_data),
                length=len(file_data),
                content_type=file.content_type or "application/octet-stream"
            )
        except Exception as e:
            raise ValueError(f"{ErrorMessages.UPLOAD_S3}: {str(e)}")

    @staticmethod
    def delete_file(file_name: str) -> None:
        """Delete file from MinIO"""
        client = ClientFactory.get_minio_client()
        try:
            client.remove_object(
                Config.MINIO_BUCKET_NAME,
                f"{Config.SOUNDBOARD_DIR}/{file_name}"
            )
        except Exception as e:
            raise ValueError(f"{ErrorMessages.DELETE_S3}: {str(e)}")

    @staticmethod
    def download_file(file_name: str) -> None:
        """Download file from MinIO"""
        client = ClientFactory.get_minio_client()
        try:
            local_path = Config.CACHE_DIR / "sounds" / file_name
            SoundCache.ensure_cache_dir()
            
            client.fget_object(
                Config.MINIO_BUCKET_NAME,
                f"{Config.SOUNDBOARD_DIR}/{file_name}",
                str(local_path)
            )
        except Exception as e:
            raise ValueError(f"{ErrorMessages.DOWNLOAD_SOUND}: {str(e)}")


class FileOperations:
    @staticmethod
    def delete_local_file(file_name: str) -> None:
        """Delete local cached file"""
        file_path = Config.CACHE_DIR / "sounds" / file_name
        if file_path.exists():
            file_path.unlink()


def get_sounds() -> List[Dict[str, Any]]:
    """Get all sounds (cached or from database)"""
    return DatabaseOperations.get_all_sounds()


async def upload_sound_file(name: str, file: discord.Attachment) -> None:
    """Upload sound file to S3 and database"""
    try:
        await S3Operations.upload_file(file)
        DatabaseOperations.add_sound(name, file.filename)
        SoundCache.invalidate()
    except Exception as e:
        raise ValueError(f"Could not upload sound file: {e}")


async def delete_sound(name: str, file_name: str) -> None:
    """Delete sound from S3, database, and local cache"""
    try:
        S3Operations.delete_file(file_name)
        DatabaseOperations.delete_sound(name)
        FileOperations.delete_local_file(file_name)
        SoundCache.invalidate()
    except Exception as e:
        raise ValueError(f"Could not delete sound file: {e}")


def download_sound_file(file_name: str) -> None:
    """Download sound file from S3 to local cache"""
    S3Operations.download_file(file_name)


async def autocomplete_sound_name(current: str) -> List[app_commands.Choice[str]]:
    """Generate autocomplete choices for sound names"""
    try:
        sounds = get_sounds()
        filtered_sounds = [
            sound for sound in sounds if current.lower() in sound["name"].lower()
        ]
        return [
            app_commands.Choice(name=sound["name"], value=sound["name"])
            for sound in filtered_sounds[:25]  # Discord limit
        ]
    except Exception:
        return []
