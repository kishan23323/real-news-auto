"""
YouTube thumbnail generator — no emojis, full Hindi/Devanagari support.
"""
import os, platform
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CHANNEL_NAME = "REAL NEWS"
THUMB_SIZE   = (1280, 720)


def _find_font(size):
    if platform.system() == "Windows":
        candidates = [
            "C:/Windows/Fonts/NotoSansDevanagari-Bold.ttf",
            "C:/Windows/Fonts/mangal.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Bold.otf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _shadow(draw, pos, text, font, fill, shadow=(0,0,0), off=3):
    draw.text((pos[0]+off, pos[1]+off), text, font=font, fill=shadow)
    draw.text(pos, text, font=font, fill=fill)


def _wrap(text, font, draw, max_w):
    words, lines, line = text.split(), [], []
    for word in words:
        test = " ".join(line + [word])
        if draw.textbbox((0,0), test, font=font)[2] <= max_w:
            line.append(word)
        else:
            if line: lines.append(" ".join(line))
            line = [word]
    if line: lines.append(" ".join(line))
    return lines


def make_thumbnail(bg_path, title, out_path="thumbnail.jpg"):
    W, H = THUMB_SIZE
    try:
        img = Image.open(bg_path).convert("RGB").resize(THUMB_SIZE, Image.LANCZOS)
    except Exception:
        img = Image.new("RGB", THUMB_SIZE, (15, 15, 40))

    img = img.filter(ImageFilter.GaussianBlur(1.2))
    ov  = Image.new("RGBA", THUMB_SIZE, (0,0,0,0))
    d   = ImageDraw.Draw(ov)
    d.rectangle([(0,0),(W,80)],   fill=(190,15,15,220))   # top red
    d.rectangle([(0,260),(W,H)],  fill=(0,0,0,185))        # bottom dark
    result = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    draw   = ImageDraw.Draw(result)

    # top bar text — plain ASCII, no emoji
    bf = _find_font(34)
    draw.text((30, 20),  "** BREAKING NEWS **",  font=bf, fill="white")
    draw.text((W-310,22), f"[ {CHANNEL_NAME} ]", font=bf, fill="white")

    # title
    tf    = _find_font(66)
    lines = _wrap(title[:130], tf, draw, W-80)
    y = 280
    for line in lines[:3]:
        _shadow(draw, (40, y), line, tf, fill="#FFD700")
        y += draw.textbbox((0,0), line, font=tf)[3] + 12

    # bottom strip
    sf = _find_font(26)
    draw.rectangle([(0, H-55),(W, H)], fill=(20,20,20))
    draw.text((40, H-42),    "Watch Full Story",   font=sf, fill="#cccccc")
    draw.text((W-260, H-42), "SUBSCRIBE NOW",      font=sf, fill="#FFD700")

    result.save(out_path, "JPEG", quality=95)
    print(f"  Thumbnail: {out_path}")
    return out_path
