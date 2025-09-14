import re
from pathlib import Path
from typing import Optional, Tuple, Union
from urllib.parse import urlparse, parse_qs
from yt_dlp import YoutubeDL

MAX_CLIP_SECONDS = 5 * 60
AUDIO_CODEC, AUDIO_QUALITY = "mp3", "192"

SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9 _.-]+")
YTD_BE_RE = re.compile(r'^https?://(?:www\.)?youtu\.be/(?P<id>[\w-]{11})(?:\?.*)?$', re.I)
SHORTS_RE = re.compile(r'^https?://(?:www\.|m\.)?youtube\.com/shorts/(?P<id>[\w-]{11})(?:\?.*)?$', re.I)

YTDL_META = {"quiet": True, "skip_download": True, "noplaylist": True}
YTDL_BASE = {
    "format": "bestaudio/best",
    "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": AUDIO_CODEC, "preferredquality": AUDIO_QUALITY}],
    "quiet": True, "noplaylist": True,
}

def parse_start_time(raw: str) -> Optional[int]:
    """Parse a YouTube time string (e.g., '120s') into seconds."""
    if not raw: return None
    sec = raw.replace("s", "")
    try:
        return int(sec)
    except ValueError:
        return None

def validate_youtube_url(url: str) -> Tuple[str, int]:
    """Validate and parse a YouTube URL into video ID and start time."""
    if not (YTD_BE_RE.match(url) or SHORTS_RE.match(url)):
        raise ValueError("Only short or video share links are accepted (youtu.be/... or youtube.com/shorts/...).")
    
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    start_time = 0

    if query_params.get("t"):
        raw_start = query_params["t"][0]
        start_time = max(0, parse_start_time(raw_start) or 0)
        
    video_id = parsed.path.strip("/").split("/")[-1]
    if not re.fullmatch(r"[\w-]{11}", video_id):
        raise ValueError("Invalid video ID.")
    
    return video_id, start_time

def parse_ts(v: Optional[Union[str,int]]) -> Optional[int]:
    """Parse a time string (e.g., '2:30', '120') into seconds."""
    if v is None: return None
    if isinstance(v,int): 
        if v < 0: raise ValueError("Time cannot be negative."); 
        return v
    parts = v.strip().split(":")
    if not parts or not all(p.isdigit() for p in parts): raise ValueError("Use SS or MM:SS")
    parts = [int(p) for p in parts]
    if len(parts)== 1: mm,ss=0,parts[0]
    elif len(parts)==2: mm,ss=parts
    else: raise ValueError("Use SS or MM:SS.")
    if ss>=60 or mm>=60 or min(mm,ss) < 0: raise ValueError("Invalid timestamp.")
    return mm*60 + ss

def fetch_info(url: str) -> dict:
    """Fetch metadata from a YouTube URL without downloading."""
    with YoutubeDL(YTDL_META) as ydl: return ydl.extract_info(url, download=False)

def sanitize_filename(name: str) -> str:
    """Sanitize a filename by removing invalid characters."""
    return SAFE_NAME_RE.sub("", name).strip()

def generate_output_path(outdir: Path, title: str, ext: str = ".mp3") -> Path:
    """Generate a safe output path for the audio file."""
    filename = sanitize_filename(title)
    return outdir / f"{filename}{ext}"

def validate_clip_parameters(
    duration: int,
    start_time: int,
    clip_length: int,
    max_clip_seconds: int = MAX_CLIP_SECONDS
) -> Tuple[int, int]:
    """Validate clip parameters and adjust as needed."""
    if start_time >= duration:
        raise ValueError("Start time is beyond the end of the video.")
    if clip_length > max_clip_seconds:
        clip_length = max_clip_seconds
    if start_time + clip_length > duration:
        clip_length = duration - start_time
    return start_time, clip_length

def download_clip_mp3(canonical: str, outdir: Path, startTime: int, length_opt: Optional[int], filename_opt: Optional[str]) -> Path:
    """Download a YouTube video clip as an audio file."""
    try:
        info = fetch_info(canonical)
        duration = int(info.get("duration") or 0)

        if duration <= 0:
            raise ValueError("Video duration is zero or invalid.")

        clip_length = max(1, min(clip_length or MAX_CLIP_SECONDS, MAX_CLIP_SECONDS))
        start_time, clip_length = validate_clip_parameters(duration, start_time, clip_length)

        outdir.mkdir(parents=True, exist_ok=True)
        title = filename_opt or (info.get("title") or "clip")
        output_path = generate_output_path(outdir, title)

        ydl_opts = dict(YTDL_BASE)
        ydl_opts["outtmpl"] = str(output_path.with_suffix(".%(ext)s"))
        ydl_opts["postprocessor_args"] = ["-ss", str(start_time), "-t", str(clip_length)]

        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(canonical, download=True)

        return output_path

    except Exception as e:
        raise RuntimeError(f"Failed to download clip: {e}")