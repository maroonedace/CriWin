"""Audio processing helpers (ffmpeg).

Used to loudness-normalize sounds at upload time so the whole soundboard sits at
a consistent baseline level; per-sound fine-tuning is layered on top at playback
via the stored ``volume`` gain.
"""

import logging
import subprocess
import tempfile
from pathlib import Path

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
                    "ffmpeg", "-y", "-i", str(src),
                    "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
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
