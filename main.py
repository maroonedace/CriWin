import os
import discord
from dotenv import load_dotenv
from commands import download_audio_as_mp3
from discord import Client, Intents, Interaction, app_commands, Object

from utils import is_valid_youtube_url

load_dotenv()
discord_token = os.getenv('DISCORD_TOKEN')
guild_id = os.getenv('GUILD_ID')
GUILD = Object(id=guild_id)

class MyClient(Client):
    def __init__(self,intents: Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    # This method is called when the bot is ready and sets up commands to be synced with the specified guild.
    async def setup_hook(self):
        self.tree.copy_global_to(guild=GUILD)
        await self.tree.sync(guild=GUILD)


intents = Intents.default()
intents.message_content = True

client = MyClient(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.tree.command(
    name="ytmp3",
    description="Download a YouTube video as MP3."
)

@app_commands.describe(url="The YouTube video URL to convert to MP3.")
async def ytmp3(interaction: Interaction, url: str):
    if not is_valid_youtube_url(url):
        return await interaction.response.send_message(
            "❌ That doesn’t look like a valid YouTube URL.", 
            ephemeral=True, 
            delete_after=10
        )
    await interaction.response.defer()
    try:
        mp3_path = download_audio_as_mp3(url, output_dir="downloads")
        file_msg = await interaction.followup.send(file=discord.File(mp3_path))
        await file_msg.delete(delay= 5 * 60)  # Delete after 5 minutes
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")

client.run(discord_token)