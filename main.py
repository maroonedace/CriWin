import os
import discord
from dotenv import load_dotenv
from discord import Intents, app_commands, Object
from commands import setup_all

load_dotenv()
discord_token = os.getenv('DISCORD_TOKEN')
guild_id = os.getenv('GUILD_ID')
GUILD = Object(id=guild_id)

intents = Intents.default()
intents.voice_states = True  
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

setup_all(tree, client)

@client.event
async def setup_hook():
    tree.copy_global_to(guild=GUILD)
    await tree.sync(guild=GUILD)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

client.run(discord_token)