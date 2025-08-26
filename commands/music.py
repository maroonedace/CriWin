import asyncio
import discord
from discord import app_commands, Interaction, FFmpegPCMAudio
from dataclasses import dataclass
from typing import Optional
from yt_dlp import YoutubeDL

YTDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "default_search": "ytsearch",   # lets users pass search terms
    "noplaylist": True,             # refuse playlists
    "skip_download": True,
}

FFMPEG_BEFORE = (
    "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
)

FFMPEG_OPTS = {
    "before_options": FFMPEG_BEFORE,
    "options": "-vn"
}

@dataclass
class Track:
    title: str
    url: str          # direct audio URL for ffmpeg
    webpage_url: str  # original page
    duration: Optional[int] = None
    requester_id: Optional[int] = None

def _extract_one(query: str) -> Track:
    """Resolve a URL or search to a single audio stream (no download)."""
    with YoutubeDL(YTDL_OPTS) as ydl:
        info = ydl.extract_info(query, download=False)
        if info.get("_type") == "playlist" and info.get("entries"):
            info = info["entries"][0]
        url = info["url"]
        return Track(
            title=info.get("title") or "Unknown",
            url=url,
            webpage_url=info.get("webpage_url") or info.get("original_url") or query,
            duration=info.get("duration"),
        )

class MusicPlayer:
    """Per-guild music player with a queue and a background play loop."""
    def __init__(self, guild: discord.Guild, client: discord.Client):
        self.guild = guild
        self.client = client
        self.queue: asyncio.Queue[Track] = asyncio.Queue()
        self.next_track = asyncio.Event()
        self.vc: Optional[discord.VoiceClient] = None
        self.current: Optional[Track] = None
        self.task = client.loop.create_task(self.player_loop())

    async def ensure_connected(self, channel: discord.VoiceChannel):
        if self.vc and self.vc.is_connected():
            if self.vc.channel.id != channel.id:
                await self.vc.move_to(channel)
        else:
            self.vc = await channel.connect(timeout=10.0, reconnect=True)

    async def add(self, track: Track):
        await self.queue.put(track)
        # if nothing is playing, nudge loop
        if not self.is_playing:
            self.next_track.set()

    @property
    def is_playing(self) -> bool:
        return bool(self.vc and self.vc.is_playing())

    async def player_loop(self):
        """Background loop that pulls from queue and plays."""
        while True:
            self.next_track.clear()

            # get next track (wait here until one is queued)
            self.current = await self.queue.get()

            if not self.vc or not self.vc.is_connected():
                self.current = None
                continue

            src = FFmpegPCMAudio(self.current.url, **FFMPEG_OPTS)

            done = asyncio.Event()

            def after_playing(err: Exception | None):
                if err:
                    print(f"[music] playback error: {err}")
                # signal coroutine to continue
                self.client.loop.call_soon_threadsafe(done.set)

            self.vc.play(src, after=after_playing)

            # wait for the track to finish
            await done.wait()
            self.current = None

            # If queue empty, wait until something is added
            if self.queue.empty():
                await asyncio.sleep(0.1)
                await self.next_track.wait()

# ===== Command setup =====

_players: dict[int, MusicPlayer] = {}  # guild_id -> player

def get_player(guild: discord.Guild, client: discord.Client) -> MusicPlayer:
    player = _players.get(guild.id)
    if not player:
        player = MusicPlayer(guild, client)
        _players[guild.id] = player
    return player

def setup_music(tree: app_commands.CommandTree, client: discord.Client):
    @tree.command(name="join", description="Join your voice channel.")
    async def join(interaction: Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message("❌ Join a voice channel first.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        player = get_player(interaction.guild, client)
        await player.ensure_connected(interaction.user.voice.channel)
        await interaction.followup.send(f"✅ Joined **{player.vc.channel.name}**.", ephemeral=True)

    @tree.command(name="play", description="Play a song by URL or search query.")
    @app_commands.describe(query="YouTube URL or search terms")
    async def play(interaction: Interaction, query: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message("❌ Join a voice channel first.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        player = get_player(interaction.guild, client)
        await player.ensure_connected(interaction.user.voice.channel)

        try:
            track = await asyncio.to_thread(_extract_one, query)
        except Exception as e:
            return await interaction.followup.send(f"❌ Couldn't resolve that: {e}", ephemeral=True)

        track.requester_id = interaction.user.id
        await player.add(track)

        np = f"🎶 Queued **{track.title}**"
        if player.is_playing:
            await interaction.followup.send(np + " (waiting in queue).", ephemeral=True)
        else:
            await interaction.followup.send(np + " (playing now).", ephemeral=True)

    @tree.command(name="skip", description="Skip the current track.")
    async def skip(interaction: Interaction):
        player = get_player(interaction.guild, client)
        if not player.vc or not player.is_playing:
            return await interaction.response.send_message("⚠️ Nothing is playing.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        player.vc.stop()
        player.next_track.set()
        await interaction.followup.send("⏭️ Skipped.", ephemeral=True)

    @tree.command(name="stop", description="Stop and clear the queue.")
    async def stop(interaction: Interaction):
        player = get_player(interaction.guild, client)
        await interaction.response.defer(ephemeral=True)
        # clear queue
        try:
            while True:
                player.queue.get_nowait()
                player.queue.task_done()
        except asyncio.QueueEmpty:
            pass
        if player.vc and player.is_playing:
            player.vc.stop()
        await interaction.followup.send("⏹️ Stopped and cleared queue.", ephemeral=True)

    @tree.command(name="queue", description="Show the next few tracks.")
    async def queue_cmd(interaction: Interaction):
        player = get_player(interaction.guild, client)
        if player.current is None and player.queue.empty():
            return await interaction.response.send_message("🕳️ Queue is empty.", ephemeral=True)
        # peek without draining
        items = list(player.queue._queue)  # type: ignore[attr-defined]
        lines = []
        if player.current:
            lines.append(f"▶️ **Now**: {player.current.title}")
        for i, t in enumerate(items[:10], start=1):
            lines.append(f"{i}. {t.title}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @tree.command(name="nowplaying", description="Show the current track.")
    async def nowplaying(interaction: Interaction):
        player = get_player(interaction.guild, client)
        if not player.current:
            return await interaction.response.send_message("⚠️ Nothing is playing.", ephemeral=True)
        await interaction.response.send_message(f"🎧 **Now playing**: {player.current.title}", ephemeral=True)

    @tree.command(name="leave", description="Disconnect from voice.")
    async def leave(interaction: Interaction):
        player = get_player(interaction.guild, client)
        if not player.vc or not player.vc.is_connected():
            return await interaction.response.send_message("⚠️ I'm not in a voice channel.", ephemeral=True)
        await interaction.response.send_message(f"👋 Leaving **{player.vc.channel.name}**.", ephemeral=True)
        await player.vc.disconnect()
