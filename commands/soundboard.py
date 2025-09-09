import asyncio
from discord import Interaction, app_commands, FFmpegPCMAudio

import json

with open("./sounds/sounds.json", "r") as file:
    data = json.load(file)

soundFiles = []

for sound in data.values():
    soundFiles.append(app_commands.Choice(name=sound["name"], value=sound["file_path"]))


def setup_soundboard(tree: app_commands.CommandTree):
    @tree.command(name="soundboard", description="Play a sound in your voice channel.")
    
    @app_commands.describe(
        sound_name="Select a sound to play",
    )
    
    @app_commands.choices(
        sound_name=soundFiles
    )
    
    async def soundboard(interaction: Interaction, sound_name: str):
        vc = interaction.guild.voice_client
        user = interaction.user

        if not user.voice or not user.voice.channel:
            return await interaction.response.send_message(
                "❌ You must be in a voice channel.", ephemeral=True
            )
        
        await interaction.response.defer(ephemeral=True)
        
        channel = user.voice.channel
        try:
            vc = await channel.connect(timeout=10.0, reconnect=True)
        except Exception as e:
            return await interaction.followup.send(f"❌ Failed to join VC: {e}", ephemeral=True)
        
        source = FFmpegPCMAudio(sound_name)
        
        def after_playing(error: Exception | None):
            if error:
                print(f"Playback error: {error}")
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