"""Media processing helpers (ffmpeg + Pillow).

Pure, framework-agnostic transforms shared across the app:

- ``normalize_audio`` loudness-normalizes soundboard uploads at upload time so the
  whole board sits at a consistent baseline (per-sound gain is layered on at
  playback via the stored ``volume``).
- ``convert_to_mp4`` / ``convert_to_png`` transcode downloaded media into
  Discord-friendly formats.

No Discord, no network, no yt-dlp — just bytes/files in, bytes/files out.
"""

import logging
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

# EBU R128 integrated loudness target (LUFS). -14 is a common streaming target.
TARGET_LUFS = -14.0


def normalize_audio(data: bytes, suffix: str = ".mp3", target_lufs: float = TARGET_LUFS) -> bytes:
    """Loudness-normalize audio bytes with ffmpeg's ``loudnorm`` filter.

    ``suffix`` (e.g. ".mp3", ".wav") preserves the container format. Returns the
    original bytes unchanged if ffmpeg is unavailable or fails, so an upload is
    never lost to a normalization error.
    """
    suffix = suffix or ".mp3"
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"in{suffix}"
        dst = Path(tmp) / f"out{suffix}"
        src.write_bytes(data)

        try:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(src),
                    "-af",
                    f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
                    str(dst),
                ],
                capture_output=True,
            )
        except FileNotFoundError:
            logger.warning("ffmpeg not found; storing original audio unnormalized")
            return data

        if result.returncode != 0 or not dst.exists():
            logger.warning("loudnorm failed (rc=%s); storing original audio", result.returncode)
            return data

        return dst.read_bytes()


def convert_to_mp4(file_path: Path) -> Path:
    """Convert a video file to mp4, attempting stream copy first then re-encode."""
    mp4_path = file_path.with_suffix(".mp4")

    # Probe the source codecs
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "csv=p=0",
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
            "ffmpeg",
            "-i",
            str(file_path),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            "-y",
            str(mp4_path),
        ]
    else:
        cmd = [
            "ffmpeg",
            "-i",
            str(file_path),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            "-y",
            str(mp4_path),
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
