from discord import Interaction, app_commands
from ollama import AsyncClient
from ollama import ChatResponse
import re

def setup_question(tree: app_commands.CommandTree):
    @tree.command(name="question", description="Ask a question to the bot.")

    async def question(interaction: Interaction, *, query: str):
        await interaction.response.defer(ephemeral=True)
        message = {'role': 'user', 'content': query}
        response: ChatResponse = await AsyncClient().chat(model='qwen3:1.7b', messages=[message])
        cleaned_content = re.sub(r'<think>.*?</think>', '', response['message']['content'], flags=re.DOTALL).strip()
        await interaction.followup.send(f"{cleaned_content}", ephemeral=True)
