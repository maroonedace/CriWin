from yt_dlp import YoutubeDL
import os

max_duration_seconds: int = 7 * 60
        
def download_audio_as_mp3(youtube_url: str, output_dir: str = ".") -> str:
    """Download and convert a YouTube URL to MP3."""
    # Checking the metadata of the video to get duration
    meta_opts = {
        'quiet': True,
        'skip_download': True,      # yt-dlp option to not download file
    }
    with YoutubeDL(meta_opts) as meta_dl:
        info = meta_dl.extract_info(youtube_url, download=False)
        duration = info.get('duration') or 0
        is_live = info.get('is_live', False) or info.get('live_status') == 'is_live'
    
    if is_live:
        raise ValueError(
            f"Live streams aren’t supported. Please provide a regular uploaded video URL."
        )

        
    if duration > max_duration_seconds:
        minutes = duration // 60
        seconds = duration % 60
        raise ValueError(
            f"Video is too long: {minutes}m{seconds}s (limit is {max_duration_seconds//60}m0s)."
        )
    
    opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        base = ydl.prepare_filename(info)
        return os.path.splitext(base)[0] + ".mp3"