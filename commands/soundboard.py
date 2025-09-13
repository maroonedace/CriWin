import asyncio
from typing import List
from discord import Interaction, app_commands, FFmpegPCMAudio
import discord
from utils.soundboard import add_sound, delete_sound, load_sounds, list_sounds

def setup_soundboard(tree: app_commands.CommandTree):
     # Soundboard Command
    @tree.command(name="soundboard", description="Play a sound in your voice channel.")
    
    @app_commands.describe(
        sound_name="Select a sound to play",
    )
    
    async def soundboard(interaction: Interaction, sound_name: str):
        data, base_dir = load_sounds()
        sounds = data.get("sounds")
        if not sounds:
            return await interaction.response.send_message(
                "❌ No sounds are available. Try again later.", ephemeral=True
            )
        file_name = next(filter(lambda sound: sound['display_name'] == sound_name, sounds), None)["file_name"]
        file_path = base_dir / file_name

        if not file_path:
            return await interaction.response.send_message(
                "❌ That sound isn't available. Try another.", ephemeral=True
            )
        
        user = interaction.user

        if not user.voice or not user.voice.channel:
            return await interaction.response.send_message(
                "❌ You must be in a voice channel.", ephemeral=True
            )
        
        await interaction.response.defer(ephemeral=True)
        
        channel = user.voice.channel
        vc = interaction.guild.voice_client

        try:
            if vc and vc.is_connected():
                await vc.move_to(channel)
            else:
                vc = await channel.connect(timeout=10.0, reconnect=True)
        except Exception as e:
            return await interaction.followup.send(f"❌ Failed to join VC: {e}", ephemeral=True)
        
        source = FFmpegPCMAudio(file_path)

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
        
    @soundboard.autocomplete("sound_name")
    async def soundboard_autocomplete(_interaction: Interaction, current: str):
        sounds = list_sounds(current)
        options = []
        for sound in sounds:
            display_name = sound.get("display_name")
            options.append(app_commands.Choice(name=display_name, value=display_name))
        return options
    
    # Soundboard Add Command
    @tree.command(name="soundboard_add", description="Add a sound entry to the soundboard.")
    @app_commands.describe(
        display_name="Display Name",
        file="Sound file",
    )
    async def add_sound_cmd(
        interaction: Interaction,
        display_name: str,
        file: discord.Attachment,
    ):
        await interaction.response.defer(ephemeral=True)
        print(file.content_type)
        try:
            await add_sound(display_name.strip(), file)
        except Exception as e:
            return await interaction.followup.send(f"❌ {e}", ephemeral=True)

        await interaction.followup.send(f"✅ Added **{display_name}** → `{file.filename}`", ephemeral=True)

    # Soundboard Delete Command
    @tree.command(name="soundboard_delete", description="Delete a sound entry of the soundboard.")
    @app_commands.describe(sound_name="The sound to delete")
    async def delete_sound_cmd(interaction: Interaction, sound_name: str):
        await interaction.response.defer(ephemeral=True)
        ok = delete_sound(sound_name)
        if not ok:
            return await interaction.followup.send(f"⚠️ No sound with Name `{sound_name}`.", ephemeral=True)
        await interaction.followup.send(f"🗑️ Deleted sound `{sound_name}`.", ephemeral=True)

    @delete_sound_cmd.autocomplete("sound_name")
    async def sound_id_autocomplete(interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        sounds = list_sounds(current)
        options = []
        for sound in sounds:
            display_name = sound.get("display_name")
            options.append(app_commands.Choice(name=display_name, value=display_name))
        return options