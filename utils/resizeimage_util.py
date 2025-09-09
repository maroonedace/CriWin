import io
from typing import Literal
from PIL import Image, ImageOps


def resizeimage_bytes(
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