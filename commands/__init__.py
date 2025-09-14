from .question import setup_question
from .leave import setup_leave
from .audioclip import setup_audioclip
from .soundboard import setup_soundboard
from discord import app_commands

def setup_all(tree: app_commands.CommandTree):
    setup_audioclip(tree)
    setup_soundboard(tree)
    setup_leave(tree)
    setup_question(tree)