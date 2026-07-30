import logging
import os
from pathlib import Path
from urllib.parse import urlparse

from gallery_dl import config, job
from yt_dlp import YoutubeDL

from src.services import cookies
from src.services.media.constants import (
    COOKIE_DOMAINS,
    DOWNLOAD_DIR,
    LIVE_STREAM_MESSAGE,
    UNSUPPORTED_URL_MESSAGE,
    URL_INVALID_MESSAGE,
    VIDEO_EXTENSIONS,
    YTDL_AUDIO,
    YTDL_META,
    YTDL_VIDEO,
)
from src.services.processing import convert_to_mp4, convert_to_png

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


def video_downloader(url: str, is_video_download: bool) -> Path:
    """Download media from the given URL using yt-dlp and return the file path."""
    if not is_supported_url(url):
        raise ValueError(UNSUPPORTED_URL_MESSAGE)

    cookie_file = get_cookie_file(url)
    if cookie_file is None:
        logger.warning("No %s cookie configured; the download may fail.", _cookie_name(url))

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


def gallery_downloader(url: str) -> list[Path] | Path:
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
    else:
        logger.warning(
            "No Instagram cookie configured; the download will likely be blocked by a "
            "login redirect."
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
