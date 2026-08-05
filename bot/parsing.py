"""Small parsers shared across the bot."""

def positive_int(value: str | None) -> int | None:
    """Parse a value that is only meaningful when it is greater than zero."""
    if value is None:
        return None

    try:
        parsed = int(value.strip())
    except (AttributeError, ValueError):
        return None

    return parsed if parsed > 0 else None
