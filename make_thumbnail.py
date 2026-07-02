"""
Generates an attractive YouTube thumbnail (1280x720) with:
- Article image as background
- Gradient overlay for readability
- RED "REAL NEWS" badge
- Bold title text (Hindi + English supported via Noto font)
- Breaking news style design
"""
import os
import platform
from PIL import Image, ImageDraw, ImageFont, ImageFilter


CHANNEL_NAME = "REAL NEWS"
THUMB_SIZE = (1280, 720)


def _find_font(size: int):
    if platform.system() == "Windows":
        candidates = [
            "C:/Windows/Fonts/NotoSansDevanagari-Bold.ttf",
            "C:/Windows/Fonts/mangal.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
    elif platform.system() == "Darwin":
        candidates = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf"]
    else:
        candidates = [
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Bold.otf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _draw_text_shadow(draw, pos, text, font, fill, shadow_color=(0,0,0), offset=3):
    draw.text((pos[0]+offset, pos[1]+offset), text, font=font, fill=shadow_color)
    draw.text(pos, text, font=font, fill=fill)


def _wrap_text(text, font, draw, max_width):
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


def make_thumbnail(background_image_path, title, out_path="thumbnail.jpg"):
    W, H = THUMB_SIZE

    # ── Background ────────────────────────────────────────────────────────
    try:
        img = Image.open(background_image_path).convert("RGB").resize(THUMB_SIZE, Image.LANCZOS)
    except Exception:
        img = Image.new("RGB", THUMB_SIZE, (15, 15, 40))

    # slight blur on bg for depth
    bg_blur = img.filter(ImageFilter.GaussianBlur(radius=1))

    # ── Gradient overlay (dark bottom, light top) ─────────────────────────
    overlay = Image.new("RGBA", THUMB_SIZE, (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    # dark bottom 60%
    ov_draw.rectangle([(0, 280), (W, H)], fill=(0, 0, 0, 185))
    # subtle dark top strip
    ov_draw.rectangle([(0, 0), (W, 90)], fill=(0, 0, 0, 160))

    result = bg_blur.convert("RGBA")
    result = Image.alpha_composite(result, overlay).convert("RGB")
    draw = ImageDraw.Draw(result)

    # ── Top red banner ────────────────────────────────────────────────────
    draw.rectangle([(0, 0), (W, 75)], fill=(210, 20, 20))

    badge_font = _find_font(36)
    draw.text((30, 18), f"⚡ BREAKING NEWS", font=badge_font, fill="white")

    channel_font = _find_font(30)
    ch_bbox = draw.textbbox((0, 0), CHANNEL_NAME, font=channel_font)
    ch_w = ch_bbox[2] - ch_bbox[0]
    draw.text((W - ch_w - 40, 22), f"🔴 {CHANNEL_NAME}", font=channel_font, fill="white")

    # ── Title text ────────────────────────────────────────────────────────
    title_font = _find_font(68)
    lines = _wrap_text(title[:140], title_font, draw, max_width=W - 80)

    y = 320
    for line in lines[:3]:
        _draw_text_shadow(draw, (40, y), line, title_font, fill="#FFD700", offset=3)
        bbox = draw.textbbox((0, 0), line, font=title_font)
        y += (bbox[3] - bbox[1]) + 14

    # ── Bottom watch prompt ───────────────────────────────────────────────
    small_font = _find_font(28)
    draw.text((40, H - 45), "▶  Watch Full Story", font=small_font, fill="#cccccc")
    draw.text((W - 320, H - 45), "SUBSCRIBE 🔔", font=small_font, fill="#FFD700")

    result.save(out_path, "JPEG", quality=95)
    print(f"  Thumbnail saved: {out_path}")
    return out_path
