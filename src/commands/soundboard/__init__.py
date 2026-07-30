from discord import Interaction, Permissions, Role, app_commands

from src.commands.soundboard.access import handle_access_add, handle_access_remove
from src.commands.soundboard.panel import handle_setup_panel
from src.commands.soundboard.play import handle_play
from src.services.soundboard import autocomplete_sound_name


def setup_soundboard(tree: app_commands.CommandTree):
    @tree.command(name="soundboard", description="Play a sound in your voice channel.")
    @app_commands.guild_only()
    @app_commands.describe(sound_name="Select a sound to play")
    async def soundboard_play(interaction: Interaction, sound_name: str):
        await handle_play(interaction, sound_name)

    @tree.command(
        name="soundboard-panel",
        description="Create the soundboard button panel in this channel.",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def soundboard_panel(interaction: Interaction):
        await handle_setup_panel(interaction)

    access = app_commands.Group(
        name="soundboard-access",
        description="Manage which roles can use the soundboard.",
        guild_only=True,
        default_permissions=Permissions(manage_guild=True),
    )

    @access.command(name="add", description="Allow a role to use the soundboard.")
    @app_commands.describe(role="Role to grant access")
    async def access_add(interaction: Interaction, role: Role):
        await handle_access_add(interaction, role)

    @access.command(name="remove", description="Remove a role's access to the soundboard.")
    @app_commands.describe(role="Role to revoke access from")
    async def access_remove(interaction: Interaction, role: Role):
        await handle_access_remove(interaction, role)

    tree.add_command(access)

    @soundboard_play.autocomplete("sound_name")
    async def play_sound_autocomplete(
        _interaction: Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await autocomplete_sound_name(current)
