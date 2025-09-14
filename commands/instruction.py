from discord import Interaction, app_commands
from ollama import AsyncClient, ChatResponse
import asyncio

# Use a lock to ensure only one instruction is processed at a time
instruction_lock = asyncio.Lock()

# Set a timeout for the model call (e.g., 1 seconds)
MAX_MODEL_RESPONSE_TIME = 1  # seconds

def setup_instruction(tree: app_commands.CommandTree):
    @tree.command(name="instruction", description="Give simple instructions to the bot.")
    @app_commands.describe(
        statement="Your instructions",
    )

    async def instruction(interaction: Interaction, *, statement: str):
        await interaction.response.defer(ephemeral=True)
        
        async with instruction_lock:
            try:
                # Set a timeout for the model call
                response = await asyncio.wait_for(
                    AsyncClient().chat(
                        model='qwen3:0.6b', 
                        messages=[{'role': 'user', 'content': statement}], 
                        think=False
                    ),
                    timeout=MAX_MODEL_RESPONSE_TIME
                )
                await interaction.followup.send(f"{response['message']['content']}", ephemeral=True)
            except asyncio.TimeoutError:
                # Handle timeout: model didn't respond in time
                await interaction.followup.send("⏳ The model took too long to respond. Please try again later.", ephemeral=True)
            except Exception as e:
                # Handle other errors (e.g., model not available)
                await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)
