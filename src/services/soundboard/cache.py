"""Local filesystem cache for downloaded sound files.

Only the audio files are cached. Sound metadata always comes from the database, which
is the single source of truth for what each guild owns.
"""

from src.config import Config


class FileOperations:
    @staticmethod
    def ensure_cache_dir():
        """Ensure cache directory exists"""
        Config.CACHE_DIR.mkdir(exist_ok=True)
        (Config.CACHE_DIR / "sounds").mkdir(exist_ok=True)

    @staticmethod
    def delete_local_file(file_name: str) -> None:
        """Delete local cached file"""
        file_path = Config.CACHE_DIR / "sounds" / file_name
        if file_path.exists():
            file_path.unlink()
