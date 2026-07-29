import os
import logging
import subprocess
from pathlib import Path
from typing import Union
from urllib.parse import urlparse

from PIL import Image
from yt_dlp import YoutubeDL
from gallery_dl import config, job

from src.services import cookies
from src.services.media.constants import (
    COOKIE_DOMAINS,
    LIVE_STREAM_MESSAGE,
    URL_INVALID_MESSAGE,
    UNSUPPORTED_URL_MESSAGE,
    YTDL_AUDIO,
    YTDL_META,
    YTDL_VIDEO,
    VIDEO_EXTENSIONS,
    DOWNLOAD_DIR,
)

logger = logging.getLogger(__name__)


def _cookie_name(url: str) -> str | None:
    """Return the logical cookie name for the URL's host, if supported."""
    hostname = urlparse(url).hostname or ""
    for domain, name in COOKIE_DOMAINS.items():
        if hostname == domain or hostname.endswith(f".{domain}"):
            return name
    return None


def is_supported_url(url: str) -> bool:
    """Check if the URL belongs to a supported platform."""
    return _cookie_name(url) is not None


def get_cookie_file(url: str) -> str | None:
    """Fetch the current cookie for the URL's platform into the local cache and
    return its path, or None if unsupported or no cookie is available."""
    name = _cookie_name(url)
    if name is None:
        return None
    path = cookies.fetch_to_cache(name)
    return str(path) if path else None

def is_instagram_url(url: str) -> bool:
    """Check if the URL is from Instagram."""
    hostname = urlparse(url).hostname or ""
    return hostname == "instagram.com" or hostname.endswith(".instagram.com")


def is_file_too_large(file_path: str, max_size_mb: int) -> bool:
    """Check if the file exceeds the given size limit."""
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    return file_size_mb > max_size_mb


def inject_cookies(opts: dict, cookie_file: str | None) -> dict:
    """Return a copy of the yt-dlp options with the cookie file injected."""
    opts = dict(opts)
    if cookie_file is not None:
        opts["cookiefile"] = cookie_file
    return opts


def convert_to_mp4(file_path: Path) -> Path:
    """Convert a video file to mp4, attempting stream copy first then re-encode."""
    mp4_path = file_path.with_suffix(".mp4")

    # Probe the source codecs
    probe = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-show_entries", "stream=codec_name",
            "-of", "csv=p=0",
            str(file_path),
        ],
        capture_output=True,
        text=True,
    )

    codecs = [line.strip() for line in probe.stdout.splitlines() if line.strip()]
    copy_safe = all(c in ("h264", "aac", "mp3") for c in codecs)

    if copy_safe and file_path.suffix.lower() == ".mp4":
        return file_path
    
    mp4_path = file_path.with_name(f"{file_path.stem}_converted.mp4")

    if copy_safe:
        cmd = [
            "ffmpeg", "-i", str(file_path),
            "-c", "copy", "-movflags", "+faststart",
            "-y", str(mp4_path),
        ]
    else:
        cmd = [
            "ffmpeg", "-i", str(file_path),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            "-y", str(mp4_path),
        ]

    result = subprocess.run(cmd, capture_output=True)

    if result.returncode == 0:
        file_path.unlink()
        final_path = file_path.with_suffix(".mp4")
        mp4_path.rename(final_path)
        return final_path

    logger.warning("Failed to convert %s to mp4", file_path)
    return file_path


def convert_to_png(file_path: Path) -> Path | None:
    """Convert an image file to PNG format."""
    try:
        with Image.open(file_path) as img:
            stem = file_path.stem.rstrip(".")
            png_path = file_path.parent / f"{stem}.png"
            img.save(png_path, "PNG")
            return png_path
    except Exception:
        logger.exception("Failed to convert %s to PNG", file_path)
        return None


def video_downloader(url: str, is_video_download: bool) -> Path:
    """Download media from the given URL using yt-dlp and return the file path."""
    if not is_supported_url(url):
        raise ValueError(UNSUPPORTED_URL_MESSAGE)

    cookie_file = get_cookie_file(url)

    try:
        meta_opts = inject_cookies(YTDL_META, cookie_file)
        ydl = YoutubeDL(meta_opts)
        video_info = ydl.extract_info(url, download=False)

        is_live = video_info.get("is_live", False)
        was_live = video_info.get("was_live", False)
        if is_live or was_live:
            raise ValueError(LIVE_STREAM_MESSAGE)

        base_opts = YTDL_VIDEO if is_video_download else YTDL_AUDIO
        download_opts = inject_cookies(base_opts, cookie_file)

        with YoutubeDL(download_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_name = ydl.prepare_filename(info)

        if is_video_download:
            return Path(file_name)

        audio_file_name = f"{os.path.splitext(file_name)[0]}.mp3"
        return Path(audio_file_name)

    except ValueError:
        raise

    except Exception as error:
        logger.exception("Download failed for URL: %s", url)
        raise ValueError(URL_INVALID_MESSAGE) from error


def gallery_downloader(url: str) -> Union[list[Path], Path]:
    """Download media from Instagram using gallery-dl. Returns a single Path for
    videos or a list of Paths for images."""
    download_path = Path(DOWNLOAD_DIR).resolve()
    download_path.mkdir(parents=True, exist_ok=True)

    config.load()
    config.set((), "base-directory", str(download_path))

    instagram_cookie = cookies.fetch_to_cache("instagram")
    if instagram_cookie is not None:
        config.set(
            ("extractor",),
            "instagram",
            {"cookies": str(instagram_cookie)},
        )

    try:
        download_job = job.DownloadJob(url)
        download_job.run()
    except Exception as error:
        logger.exception("Gallery download failed for URL: %s", url)
        raise ValueError(URL_INVALID_MESSAGE) from error

    downloaded_files = [f for f in download_path.rglob("*") if f.is_file()]

    if not downloaded_files:
        raise ValueError(URL_INVALID_MESSAGE)

    videos = [f for f in downloaded_files if f.suffix.lower() in VIDEO_EXTENSIONS]
    images = [f for f in downloaded_files if f.suffix.lower() not in VIDEO_EXTENSIONS]

    # Convert videos to mp4
    converted_videos = []
    for video in videos:
        converted_videos.append(convert_to_mp4(video))
    
    # Convert all images to PNG
    converted_images = []
    for file_path in images:
        if file_path.suffix.lower() == ".png":
            converted_images.append(file_path)
            continue

        png_path = convert_to_png(file_path)
        if png_path is not None:
            converted_images.append(png_path)
            file_path.unlink()
        else:
            converted_images.append(file_path)
        
    all_files = converted_videos + converted_images

    # Return single video or list of files
    if len(all_files) == 1 and all_files[0].suffix.lower() == ".mp4":
        return all_files[0]

    return all_files[::-1]