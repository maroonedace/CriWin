from discord import app_commands

from bot.commands.ping import setup_ping

def setup_commands(tree: app_commands.CommandTree):
    setup_ping(tree)