from discord import Interaction, Permissions, Role, app_commands

from src.commands.soundboard.access import handle_access_add, handle_access_remove
from src.commands.soundboard.panel import handle_setup_panel


def setup_soundboard(tree: app_commands.CommandTree):
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
