import re
from pathlib import Path
from typing import Optional, Tuple, Union
from urllib.parse import urlparse, parse_qs
from yt_dlp import YoutubeDL

MAX_CLIP_SECONDS = 5 * 60
DEFAULT_CLIP_SECONDS = 30
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

def parse_share_link(url: str) -> Tuple[str, int]:
    if not (YTD_BE_RE.match(url) or SHORTS_RE.match(url)):
        raise ValueError("Only share links are accepted (youtu.be/... or youtube.com/shorts/...).")
    p = urlparse(url); qs = parse_qs(p.query)
    if "list" in qs: raise ValueError("Playlist links are not supported.")
    start = 0
    if qs.get("t"): start = max(0, _parse_t(qs["t"][0]) or 0)
    vid = p.path.strip("/").split("/")[-1]
    if not re.fullmatch(r"[\w-]{11}", vid): raise ValueError("Invalid video id.")
    return vid, start

def _parse_t(raw: str) -> Optional[int]:
    s = (raw or "").strip().lower()
    if not s: return None
    if s.isdigit(): return int(s)
    h=m=sec=0; num=""
    for ch in s:
        if ch.isdigit(): num += ch
        elif ch=="h" and num: h,num=int(num), ""
        elif ch=="m" and num: m,num=int(num), ""
        elif ch=="s" and num: sec,num=int(num), ""
        else: return None
    if num: sec=int(num)
    return h*3600 + m*60 + sec

def parse_ts(v: Optional[Union[str,int]]) -> Optional[int]:
    if v is None: return None
    if isinstance(v,int): 
        if v<0: raise ValueError("Time cannot be negative."); 
        return v
    parts = v.strip().split(":")
    if not parts or not all(p.isdigit() for p in parts): raise ValueError("Use SS, MM:SS, or HH:MM:SS.")
    parts = [int(p) for p in parts]
    if len(parts)==1: hh,mm,ss=0,0,parts[0]
    elif len(parts)==2: hh,mm,ss=0,parts[0],parts[1]
    elif len(parts)==3: hh,mm,ss=parts
    else: raise ValueError("Use SS, MM:SS, or HH:MM:SS.")
    if ss>=60 or mm>=60 or min(hh,mm,ss)<0: raise ValueError("Invalid timestamp.")
    return hh*3600 + mm*60 + ss

def safe_filename(name: str, ext=".mp3") -> str:
    b = name.strip()
    if b.lower().endswith(ext): b = b[:-len(ext)]
    b = SAFE_NAME_RE.sub("_", b)
    b = re.sub(r"\s+"," ", b).strip(" ._-") or "clip"
    return f"{b[:100]}{ext}"

def uniquify(path: Path) -> Path:
    if not path.exists(): return path
    i=1; stem,ext=path.stem, path.suffix
    while True:
        c = path.with_name(f"{stem}-{i}{ext}")
        if not c.exists(): return c
        i += 1

def fetch_info(url: str) -> dict:
    with YoutubeDL(YTDL_META) as ydl: return ydl.extract_info(url, download=False)

def download_clip_mp3(canonical: str, outdir: Path, start: int, length_opt: Optional[int], desired: Optional[str]) -> Path:
    info = fetch_info(canonical)
    if info.get("is_live") or info.get("live_status") == "is_live":
        raise ValueError("Live streams aren’t supported.")
    duration = int(info.get("duration") or 0)

    start = max(0, int(start))
    length = length_opt if length_opt is not None else DEFAULT_CLIP_SECONDS
    length = max(1, min(int(length), MAX_CLIP_SECONDS))
    if duration:
        if start >= duration: raise ValueError("Start time is beyond the end of the video.")
        if start + length > duration: length = duration - start

    outdir.mkdir(parents=True, exist_ok=True)
    base = desired or (info.get("title") or "clip")
    target = uniquify(outdir / safe_filename(base, ".mp3"))

    ydl_opts = dict(YTDL_BASE)
    ydl_opts["outtmpl"] = str(target.with_suffix(".%(ext)s"))
    ydl_opts["postprocessor_args"] = ["-ss", str(start), "-t", str(length)]
    with YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(canonical, download=True)
    return target