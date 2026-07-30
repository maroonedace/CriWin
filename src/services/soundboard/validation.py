"""Shared soundboard display-name rules.

Lives in the (Discord-free) service layer so the bot command handlers
(``src/commands/soundboard``) and the FastAPI admin panel (``src/web``) validate
sound names from a single source of truth.
"""

import re

# Display names: letters, digits, spaces, and _ ' - up to 64 characters.
NAME_RE = re.compile(r"^[a-zA-Z0-9 _'-]{1,64}$")

INVALID_NAME_MESSAGE = "Display Name is invalid. It must be no more than 64 characters."
DUPLICATE_NAME_MESSAGE = "❌ A sound with that Display Name already exists."


def is_valid_name(name: str) -> bool:
    """Return ``True`` if ``name`` is an acceptable soundboard display name."""
    return bool(NAME_RE.match(name))
