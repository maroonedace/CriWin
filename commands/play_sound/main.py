import asyncio
from discord import Interaction, app_commands, FFmpegPCMAudio

from sounds import sounds


def play_sound(tree: app_commands.CommandTree):
    @tree.command(name="play_sound", description="Plays a sound")
    
    async def play_sound(interaction: Interaction):
        user = interaction.user
        if user.voice:
            channel = user.voice.channel
            vc = await channel.connect()
            sound_path = sounds["shooting_stars"]
            source = FFmpegPCMAudio(sound_path)
            def after_playing(error):
            # This runs in a separate thread, so use run_coroutine_threadsafe
                if error:
                    print(f"Error while playing: {error}")
                fut = asyncio.run_coroutine_threadsafe(vc.disconnect(), interaction.client.loop)
                try:
                    fut.result()  # block to surface exceptions
                except Exception as e:
                    print(f"Failed to disconnect: {e}")
            vc.play(source, after=after_playing)