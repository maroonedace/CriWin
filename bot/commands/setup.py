from discord import app_commands

from bot.commands.ping import setup_ping
from bot.commands.download import setup_download

def setup_commands(tree: app_commands.CommandTree):
    setup_ping(tree)
    setup_download(tree)