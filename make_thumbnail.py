"""
Generates a YouTube thumbnail (1280x720) using the first article image
as background, with the video title and "REAL NEWS" branding overlaid.

YouTube thumbnails with bold text + face/relevant image get dramatically
more clicks than blank or auto-generated ones.
"""
import os
import platform
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

CHANNEL_NAME = "REAL NEWS"
THUMB_SIZE = (1280, 720)


def _find_font(size: int, bold: bool = True):
    candidates = []
    if platform.system() == "Windows":
        candidates = ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"]
    elif platform.system() == "Darwin":
        candidates = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf"]
    else:
        candidates = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _wrap_text(text: str, font, draw, max_width: int) -> list:
    words = text.split()
    lines, line = [], []
    for word in words:
        test = " ".join(line + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            line.append(word)
        else:
            if line:
                lines.append(" ".join(line))
            line = [word]
    if line:
        lines.append(" ".join(line))
    return lines


def make_thumbnail(background_image_path: str, title: str, out_path: str = "thumbnail.jpg") -> str:
    # Load and resize background
    try:
        img = Image.open(background_image_path).convert("RGB")
    except Exception:
        img = Image.new("RGB", THUMB_SIZE, color=(20, 20, 60))

    img = img.resize(THUMB_SIZE, Image.LANCZOS)

    # Darken the bottom half for text readability
    overlay = Image.new("RGBA", THUMB_SIZE, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    draw_overlay.rectangle([(0, 320), (1280, 720)], fill=(0, 0, 0, 170))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay).convert("RGB")

    draw = ImageDraw.Draw(img)

    # Channel badge (top-left red bar)
    badge_font = _find_font(36, bold=True)
    draw.rectangle([(30, 25), (260, 80)], fill=(220, 30, 30))
    draw.text((50, 32), CHANNEL_NAME, font=badge_font, fill="white")

    # Title text (bottom half)
    title_font = _find_font(72, bold=True)
    lines = _wrap_text(title[:120], title_font, draw, max_width=1180)
    y = 360
    for line in lines[:3]:  # max 3 lines
        # shadow for readability
        draw.text((42, y + 2), line, font=title_font, fill=(0, 0, 0, 200))
        draw.text((40, y), line, font=title_font, fill="white")
        bbox = draw.textbbox((0, 0), line, font=title_font)
        y += (bbox[3] - bbox[1]) + 12

    img.save(out_path, "JPEG", quality=95)
    print(f"  Thumbnail saved: {out_path}")
    return out_path
