import asyncio
from discord import Interaction, app_commands, FFmpegPCMAudio

from sounds import sounds


def setup_play_sound(tree: app_commands.CommandTree):
    @tree.command(name="play_sound", description="Play a sound")
    
    @app_commands.describe(
        sound_name="Sound to play",
    )
    
    @app_commands.choices(
        sound_name=[
            app_commands.Choice(name="Jeff Theme Song", value="jeff"),
            app_commands.Choice(name="Shooting Stars", value="shooting_stars"),
        ]
    )
    
    async def setup_play_sound(interaction: Interaction, sound_name: str):
        vc = interaction.guild.voice_client
        user = interaction.user

        if not user.voice or not user.voice.channel:
            return await interaction.response.send_message(
                "❌ You must be in a voice channel.", ephemeral=True, delete_after=10
            )
        
        await interaction.response.defer(ephemeral=True)
        
        channel = user.voice.channel
        try:
            vc = await channel.connect(timeout=10.0, reconnect=True)
        except Exception as e:
            return await interaction.followup.send(f"❌ Failed to join VC: {e}", ephemeral=True)
        
        source = FFmpegPCMAudio(sounds[sound_name])
        
        def after_playing(error: Exception | None):
            if error:
                print(f"Playback error: {error}")
            # schedule disconnect back on the event loop
            interaction.client.loop.call_soon_threadsafe(asyncio.create_task, vc.disconnect())
        
        try:
            vc.play(source, after=after_playing)
            await interaction.followup.send(f"✅ Now playing: {sound_name}", ephemeral=True)
        
        except Exception as e:
            try:
                await vc.disconnect()
            except Exception:
                pass
            await interaction.followup.send(f"❌ Could not play sound: {e}", ephemeral=True)