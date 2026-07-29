import discord
from discord import Interaction, app_commands

from src.commands.soundboard.add import handle_add
from src.commands.soundboard.delete import handle_delete
from src.commands.soundboard.play import handle_play
from src.services.soundboard import autocomplete_sound_name


def setup_soundboard(tree: app_commands.CommandTree):
    @tree.command(name="soundboard", description="Play a sound in your voice channel.")
    @app_commands.guild_only()
    @app_commands.describe(sound_name="Select a sound to play")
    async def soundboard_play(interaction: Interaction, sound_name: str):
        await handle_play(interaction, sound_name)

    @tree.command(name="soundboard-add", description="Add a sound to the soundboard.")
    @app_commands.describe(sound_name="Sound name", sound_file="Sound file")
    async def soundboard_add(
        interaction: Interaction, sound_name: str, sound_file: discord.Attachment
    ):
        await handle_add(interaction, sound_name, sound_file)

    @tree.command(name="soundboard-delete", description="Add a sound to the soundboard.")
    @app_commands.describe(sound_name="Sound name")
    async def soundboard_delete(interaction: Interaction, sound_name: str):
        await handle_delete(interaction, sound_name)

    @soundboard_play.autocomplete("sound_name")
    async def play_sound_autocomplete(
        _interaction: Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await autocomplete_sound_name(current)

    @soundboard_delete.autocomplete("sound_name")
    async def delete_sound_autocomplete(
        _interaction: Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await autocomplete_sound_name(current)
