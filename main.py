import discord
import os
from dotenv import load_dotenv, dotenv_values 

intents = discord.Intents.default()
intents.message_content = True

load_dotenv() 

client = discord.Client(intents=intents)

token = os.getenv('DISCORD_TOKEN')

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

client.run(token)