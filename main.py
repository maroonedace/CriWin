import os
import discord
from dotenv import load_dotenv
from discord import Intents, app_commands, Object

from commands.resize_image.main import resize_image
from commands.yt_to_mp3.main import setup_ytmp3

load_dotenv()
discord_token = os.getenv('DISCORD_TOKEN')
guild_id = os.getenv('GUILD_ID')
GUILD = Object(id=guild_id)

intents = Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

setup_ytmp3(tree)
resize_image(tree)

@client.event
async def setup_hook():
    tree.copy_global_to(guild=GUILD)
    await tree.sync(guild=GUILD)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

client.run(discord_token)