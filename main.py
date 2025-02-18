import discord
import os
from dotenv import load_dotenv 

from commands import messaging

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
    await messaging(client, message)

client.run(token)