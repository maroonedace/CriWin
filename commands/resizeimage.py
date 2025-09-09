import io
import asyncio

import discord
from discord import app_commands, Interaction, File
from utils.resizeimage_util import resizeimage_bytes


def setup_resizeimage(tree: app_commands.CommandTree):
    @tree.command(
    name="resizeimage",
        description="Resize an image to given width/height."
    )
    
    @app_commands.describe(
        image="Upload the image to resize",
        width="Target width (px)",
        height="Target height (px)",
        mode="How to handle aspect ratio",
    )
    @app_commands.choices(
    mode=[
        app_commands.Choice(name="fit (no crop)", value="fit"),
        app_commands.Choice(name="cover (crop to fill)", value="cover"),
        app_commands.Choice(name="pad (letterbox)", value="pad"),
        app_commands.Choice(name="stretch (distort)", value="stretch"),
    ]
)
    async def resizeimage(
        interaction: Interaction,
        image: discord.Attachment,
        width: app_commands.Range[int, 1, 4096],
        height: app_commands.Range[int, 1, 4096],
        mode: str = "fit",
    ):
        # quick validations before acknowledging
        if not (image.content_type or "").startswith("image/"):
            return await interaction.response.send_message(
                "❌ Please attach a valid image file.", ephemeral=True
            )

        # (optional) size cap to avoid huge files; adjust as you like
        if image.size and image.size > 10 * 1024 * 1024:
            return await interaction.response.send_message(
                "⚠️ Image is larger than 10 MB. Please upload a smaller image.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        try:
            raw = await image.read()

            # offload Pillow work to a thread so we don't block the event loop
            png_bytes = await asyncio.to_thread(resizeimage_bytes, raw, width, height, mode)

            filename = f"resized_{width}x{height}.png"
            await interaction.followup.send(file=File(io.BytesIO(png_bytes), filename=filename), ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Error processing image: {e}", ephemeral=True)