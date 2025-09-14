import asyncio
from typing import List, Optional
from discord import Interaction, app_commands, FFmpegPCMAudio
import discord
from utils.soundboard import add_sound, delete_sound, load_sounds, list_sounds

def setup_soundboard(tree: app_commands.CommandTree):
    # Helper for autocomplete
    def autocomplete_sound_name(current: str) -> List[app_commands.Choice[str]]:
        sounds = list_sounds(current)
        return [
            app_commands.Choice(name=sound["display_name"], value=sound["display_name"])
            for sound in sounds
        ]
        
     # Soundboard Command
    @tree.command(name="soundboard", description="Play a sound in your voice channel.")
    @app_commands.describe(
        sound_name="Select a sound to play",
    )
    async def soundboard(interaction: Interaction, sound_name: str):
        await interaction.response.defer(ephemeral=True)
        
        data, base_dir = load_sounds()
        sounds = data.get("sounds", [])
        
        if not sounds:
            return await interaction.followup.send(
                "❌ No sounds are available. Try again later.", ephemeral=True
            )
        
        file_name = next((sound["file_name"] for sound in sounds if sound["display_name"] == sound_name), None)
        if not file_name:
            return await interaction.followup.send(
                "❌ That sound isn't available. Try another.", ephemeral=True
            )
        
        user = interaction.user
        if not user.voice or not user.voice.channel:
            return await interaction.followup.send(
                "❌ You must be in a voice channel.", ephemeral=True
            )
        
        channel = user.voice.channel
        vc = interaction.guild.voice_client

        try:
            if vc and vc.is_connected():
                await vc.move_to(channel)
            else:
                vc = await channel.connect(timeout=10.0, reconnect=True)
        except Exception as e:
            return await interaction.followup.send(f"❌ Failed to join VC: {e}", ephemeral=True)
        
        source = FFmpegPCMAudio(f"{base_dir}/{file_name}")

        done = asyncio.Event()
        
        def after_playing(error: Exception = None):
            interaction.client.loop.call_soon_threadsafe(done.set)
        
        try:
            vc.play(source, after=after_playing)
            await interaction.followup.send(f"▶️ Playing **{sound_name}**.", ephemeral=True)
            await done.wait()
            await vc.disconnect()
        
        except Exception as e:
            try: await vc.disconnect()
            except Exception: pass
            await interaction.followup.send(f"❌ Could not play sound: {e}", ephemeral=True)
    
    # Autocomplete for soundboard
    @soundboard.autocomplete("sound_name")
    async def soundboard_autocomplete(_interaction: Interaction, current: str):
        return autocomplete_sound_name(current)
    
    # Soundboard Add Command
    @tree.command(name="soundboard_add", description="Add a sound entry to the soundboard.")
    @app_commands.describe(
        display_name="Display Name",
        file="Sound File",
    )
    async def add_sound_cmd(
        interaction: Interaction,
        display_name: str,
        file: discord.Attachment,
    ):
        await interaction.response.defer(ephemeral=True)
        
        try:
            await add_sound(display_name.strip(), file)
            await interaction.followup.send(f"✅ Added **{display_name}** → `{file.filename}`", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)

    # Soundboard Delete Command
    @tree.command(name="soundboard_delete", description="Delete a sound entry of the soundboard.")
    @app_commands.describe(sound_name="The sound to delete")
    async def delete_sound_cmd(interaction: Interaction, sound_name: str):
        await interaction.response.defer(ephemeral=True)
        
        if delete_sound(sound_name):
            await interaction.followup.send(f"🗑️ Deleted sound `{sound_name}`.", ephemeral=True)
        else:
            await interaction.followup.send(f"⚠️ No sound with name `{sound_name}`.", ephemeral=True)

    @delete_sound_cmd.autocomplete("sound_name")
    async def sound_id_autocomplete(interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        return autocomplete_sound_name(current)