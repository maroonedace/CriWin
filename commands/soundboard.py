import asyncio
from typing import List
from discord import Interaction, app_commands, FFmpegPCMAudio
import discord
from utils.soundboard import add_sound, delete_sound, load_sounds, list_sounds
from pathlib import Path

def setup_soundboard(tree: app_commands.CommandTree):
    # ======================
    # Helper Functions
    # ======================
    
    def autocomplete_sound_name(current: str) -> List[app_commands.Choice[str]]:
        """Generate autocomplete choices for sound names."""
        sounds = list_sounds(current)
        return [
            app_commands.Choice(name=sound["display_name"], value=sound["display_name"])
            for sound in sounds
        ]
    
    # ======================
    # Soundboard Play Command
    # ======================
    
    @tree.command(name="soundboard", description="Play a sound in your voice channel.")
    @app_commands.describe(sound_name="Select a sound to play")
    async def soundboard(interaction: Interaction, sound_name: str):
        await interaction.response.defer(ephemeral=True)
        
        # Load sound data
        data, base_dir = load_sounds()
        sounds = data.get("sounds", [])
        
        # Check if sounds exist
        if not sounds:
            return await interaction.followup.send(
                "❌ No sounds are available. Try again later.", ephemeral=True
            )
        
        # Find the requested sound
        sound_entry = next((sound for sound in sounds if sound["display_name"] == sound_name), None)
        if not sound_entry:
            return await interaction.followup.send(
                "❌ That sound isn't available. Try another.", ephemeral=True
            )
        
        file_name = sound_entry["file_name"]
        file_path = base_dir / file_name
        
        # Validate file exists
        if not file_path.exists():
            return await interaction.followup.send(
                f"❌ Sound file `{file_name}` not found.", ephemeral=True
            )
        
        # Check user's voice state
        user = interaction.user
        if not user.voice or not user.voice.channel:
            return await interaction.followup.send(
                "❌ You must be in a voice channel.", ephemeral=True
            )
        
        channel = user.voice.channel
        vc = interaction.guild.voice_client

        # Connect to voice channel
        try:
            if vc and vc.is_connected():
                await vc.move_to(channel)
            else:
                vc = await channel.connect(timeout=10.0, reconnect=True)
        except Exception as e:
            return await interaction.followup.send(f"❌ Failed to join voice channel: {e}", ephemeral=True)
        
        # Play the sound
        try:
            source = FFmpegPCMAudio(str(file_path))
            
            done = asyncio.Event()
            
            def after_playing(error: Exception = None):
                if error:
                    print(f"Error playing sound: {error}")
                interaction.client.loop.call_soon_threadsafe(done.set)
            
            vc.play(source, after=after_playing)
            await interaction.followup.send(f"▶️ Playing **{sound_name}**.", ephemeral=True)
            
            # Wait for playback to finish
            await done.wait()
            
            # Disconnect after playback
            if vc and vc.is_connected():
                await vc.disconnect()
                
        except Exception as e:
            # Ensure cleanup on error
            try:
                if vc and vc.is_connected():
                    await vc.disconnect()
            except Exception:
                pass
            await interaction.followup.send(f"❌ Could not play sound: {e}", ephemeral=True)
    
    # Autocomplete for soundboard
    @soundboard.autocomplete("sound_name")
    async def soundboard_autocomplete(_interaction: Interaction, current: str):
        return autocomplete_sound_name(current)
    
    # ======================
    # Soundboard Add Command
    # ======================
    
    @tree.command(name="soundboard_add", description="Add a sound entry to the soundboard.")
    @app_commands.describe(display_name="Display Name", file="Sound file")
    async def add_sound_cmd(
        interaction: Interaction,
        display_name: str,
        file: discord.Attachment,
    ):
        await interaction.response.defer(ephemeral=True)
        
        try:
            await add_sound(display_name.strip(), file)
            await interaction.followup.send(
                f"✅ Added **{display_name}** → `{file.filename}`", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)

    # ======================
    # Soundboard Delete Command
    # ======================
    
    @tree.command(name="soundboard_delete", description="Delete a sound entry from the soundboard.")
    @app_commands.describe(sound_name="The sound to delete")
    async def delete_sound_cmd(interaction: Interaction, sound_name: str):
        await interaction.response.defer(ephemeral=True)
        
        if delete_sound(sound_name):
            await interaction.followup.send(
                f"🗑️ Deleted sound `{sound_name}`.", 
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"⚠️ No sound with name `{sound_name}`.", 
                ephemeral=True
            )

    # Autocomplete for delete command
    @delete_sound_cmd.autocomplete("sound_name")
    async def sound_id_autocomplete(_interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        return autocomplete_sound_name(current)