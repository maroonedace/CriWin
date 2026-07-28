import json
import time
from typing import Any, Dict, List

from src.config import Config


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


class FileOperations:
    @staticmethod
    def delete_local_file(file_name: str) -> None:
        """Delete local cached file"""
        file_path = Config.CACHE_DIR / "sounds" / file_name
        if file_path.exists():
            file_path.unlink()
