from .bot_leave import setup_bot_leave
from .audioclip import setup_audioclip
from .resize_image import setup_resize_image
from .play_sound import setup_play_sound
from discord import app_commands

def setup_all(tree: app_commands.CommandTree):
    setup_audioclip(tree)
    setup_resize_image(tree)
    setup_play_sound(tree)
    setup_bot_leave(tree)