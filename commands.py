from discord import Message
from yt_dlp import YoutubeDL
import os

async def messaging(message: Message):
    if message.content.startswith('$hello'):
        print(message.author.id)
        await message.channel.send('Hello!')
        
def download_audio_as_mp3(youtube_url: str, output_dir: str = ".") -> str:
    """Download and convert a YouTube URL to MP3."""
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