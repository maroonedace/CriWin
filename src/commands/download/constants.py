DOWNLOAD_SENT_TO_CHANNEL_MESSAGE = 'Download sent to channel!'
LIMIT_DOWNLOAD_MESSAGE = '⚠️ You already have a download in progress.'


def large_file_message(max_size_mb: int) -> str:
    """Message shown when a download exceeds the guild's upload limit."""
    return f"⚠️ This file is larger than the {max_size_mb}MB upload limit."
