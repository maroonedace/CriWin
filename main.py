import os
import discord
from dotenv import load_dotenv
from commands import download_audio_as_mp3, messaging
from discord import Client, Intents, Interaction, Message, app_commands

load_dotenv()
discord_token = os.getenv('DISCORD_TOKEN')

# Initialize the Discord client with the required intents
intents = Intents.default()
intents.message_content = True

client = Client(intents=intents)
tree = app_commands.CommandTree(client)

client.tree = tree

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message: Message):
    if message.author.bot:
        return
    return await messaging(message)

@client.tree.command(
    name="mp3",
    description="Download a YouTube video as MP3."
)
@app_commands.describe(url="The YouTube video URL to convert to MP3.")
async def mp3(interaction: Interaction, url: str):
    await interaction.response.defer()
    try:
        mp3_path = download_audio_as_mp3(url, output_dir="downloads")
        # Send back the file with a followup, since you deferred
        await interaction.followup.send(file=discord.File(mp3_path))
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")

client.run(discord_token)