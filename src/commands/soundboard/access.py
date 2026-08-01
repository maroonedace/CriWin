"""Role-gated access to the soundboard panel.

An admin designates the Discord role(s) that may use the panel (per guild). When a
guild has no roles configured the panel is open to everyone; otherwise a member needs
one of the configured roles to play.
"""

import logging

from discord import Interaction, Member, Role

from src.core.messaging import send_message
from src.services.soundboard import add_access_role, remove_access_role

logger = logging.getLogger(__name__)

NO_ACCESS_MESSAGE = "⛔ You don't have permission to use the soundboard."


def has_panel_access(member: Member, allowed_role_ids: set[int]) -> bool:
    """Whether ``member`` may use the panel.

    Open when no roles are configured; otherwise the member must have one of them.
    """
    if not allowed_role_ids:
        return True
    return any(role.id in allowed_role_ids for role in member.roles)


async def handle_access_add(interaction: Interaction, role: Role) -> None:
    await interaction.response.defer(ephemeral=True)
    add_access_role(interaction.guild.id, role.id)
    await send_message(interaction, f"✅ **{role.name}** can now use the soundboard.")


async def handle_access_remove(interaction: Interaction, role: Role) -> None:
    await interaction.response.defer(ephemeral=True)
    remove_access_role(interaction.guild.id, role.id)
    await send_message(interaction, f"✅ **{role.name}** can no longer use the soundboard.")
