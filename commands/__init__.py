from commands.music import setup_music
from .bot_leave import setup_bot_leave
from .yt_to_mp3 import setup_ytmp3
from .resize_image import setup_resize_image
from .play_sound import setup_play_sound
from discord import app_commands, Client

def setup_all(tree: app_commands.CommandTree, client: Client):
    setup_ytmp3(tree)
    setup_resize_image(tree)
    setup_play_sound(tree)
    setup_bot_leave(tree)
    setup_music(tree, client)