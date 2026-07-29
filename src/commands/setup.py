from discord import app_commands

from src.commands.download import setup_download
from src.commands.leave import setup_leave
from src.commands.soundboard import setup_soundboard


def setup_commands(tree: app_commands.CommandTree):
    setup_soundboard(tree)
    setup_download(tree)
    setup_leave(tree)
