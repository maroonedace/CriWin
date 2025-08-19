import io
import asyncio
from typing import Literal

import discord
from discord import app_commands, Interaction, File
from PIL import Image, ImageOps

# ---------- image helpers ----------

def _resize_image_bytes(
    image_bytes: bytes,
    width: int,
    height: int,
    mode: Literal["fit", "cover", "pad", "stretch"] = "fit",
    pad_color=(0, 0, 0, 0),  # transparent (RGBA)
) -> bytes:
    """
    Returns PNG bytes of the resized image.
    modes:
      - "fit":    keep aspect ratio, fit within (w,h) (no crop). Final image <= (w,h).
      - "cover":  keep aspect ratio, fill (w,h) by cropping overflow (like CSS cover).
      - "pad":    keep aspect ratio, fit within (w,h) then pad to exact (w,h).
      - "stretch":ignore aspect ratio, force exact (w,h).
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert("RGBA")  # robust output

        if mode == "fit":
            resized = ImageOps.contain(img, (width, height), Image.LANCZOS)
            out = resized
        elif mode == "cover":
            out = ImageOps.fit(img, (width, height), method=Image.LANCZOS, centering=(0.5, 0.5))
        elif mode == "pad":
            resized = ImageOps.contain(img, (width, height), Image.LANCZOS)
            canvas = Image.new("RGBA", (width, height), pad_color)
            x = (width - resized.width) // 2
            y = (height - resized.height) // 2
            canvas.paste(resized, (x, y))
            out = canvas
        else:  # "stretch"
            out = img.resize((width, height), Image.LANCZOS)

        buf = io.BytesIO()
        out.save(buf, format="PNG")
        buf.seek(0)
        return buf.read()

# ---------- slash command ----------
def setup_resize_image(tree: app_commands.CommandTree):
    @tree.command(
    name="resize_image",
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
    async def resize_image(
        interaction: Interaction,
        image: discord.Attachment,
        width: app_commands.Range[int, 1, 4096],
        height: app_commands.Range[int, 1, 4096],
        mode: str = "fit",
    ):
        # quick validations before acknowledging
        if not (image.content_type or "").startswith("image/"):
            return await interaction.response.send_message(
                "❌ Please attach a valid image file.", ephemeral=True, delete_after=8
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
            png_bytes = await asyncio.to_thread(_resize_image_bytes, raw, width, height, mode)

            filename = f"resized_{width}x{height}.png"
            await interaction.followup.send(file=File(io.BytesIO(png_bytes), filename=filename), ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Error processing image: {e}", ephemeral=True)