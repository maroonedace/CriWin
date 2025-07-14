import os
from dotenv import load_dotenv
from commands import messaging
from discord import Client, Intents, Message

# import psycopg2

load_dotenv()
discord_token = os.getenv('DISCORD_TOKEN')

# Initialize the Discord client with the required intents
intents = Intents.default()
intents.message_content = True
client = Client(intents=intents)

# conn = psycopg2.connect(
#     dbname="CrimsonWinterMountain",
#     user="postgres",
#     password="bv3&dF84dac",
#     host="localhost",
#     port="5433")

# cursor = conn.cursor()

# cursor.execute('select * from users')

# records = cursor.fetchall()

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message: Message):
    if message.author.bot:
        return
    return await messaging(message)

client.run(discord_token)