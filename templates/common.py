"""
templates/common.py
────────────────────
Shared building blocks used by every video template: colors, fonts,
auto-fitting text helpers, the Ken Burns zoom/pan effect, and the top
yellow / bottom dark banners that appear on all formats.

Individual template files (landscape_16_9.py, shorts_9_16.py, ...) import
from here so the same look-and-feel primitives aren't duplicated, while
each template still owns its own layout in its own file.
"""
import platform
import os
from moviepy import (
    ImageClip, ColorClip, TextClip, CompositeVideoClip, vfx,
)

CHANNEL_NAME = "REAL NEWS"

YELLOW = (255, 209, 0)
RED    = (200, 20, 20)
DARK   = (18, 18, 18)
BLACK  = (0, 0, 0)
WHITE  = (255, 255, 255)
BLUE   = (20, 70, 190)

TOP_TEXT_HI    = "आज की 50 बड़ी खबरें , मुख्य समाचार आम आदमी के काम की खबरें"
BOTTOM_TEXT_HI = "अपने दोस्तों के साथ फेसबुक और व्हाट्सएप पर शेयर जरूर करें"

# Repo-root/assets — one level up from templates/
ASSETS_DIR   = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
BUNDLED_FONT = os.path.join(ASSETS_DIR, "fonts", "NotoSansDevanagari-Bold.ttf")
IMPACT_FONT  = os.path.join(ASSETS_DIR, "fonts", "Anton-Regular.ttf")
LOGO_PATH    = os.path.join(ASSETS_DIR, "logo.png")
BADGE_PATH   = os.path.join(ASSETS_DIR, "breaking_news_badge.png")


def autofit_textclip(text, max_width, font, start_size, color="white",
                      min_size=16, step=2, method="label", max_height=None):
    """Render `text` as large as possible while guaranteeing it fits within
    max_width (and max_height if given)."""
    size = start_size
    kw = dict(text=text, color=color, method=method)
    if font:
        kw["font"] = font
    while size > min_size:
        kw["font_size"] = size
        clip = TextClip(**kw).with_duration(0.1)
        w, h = clip.size
        if w <= max_width and (max_height is None or h <= max_height):
            return clip, size
        size -= step
    kw["font_size"] = min_size
    return TextClip(**kw).with_duration(0.1), min_size


def autofit_wrapped(text, max_width, max_height, font, start_size, color,
                     min_size=14, step=2, align="left"):
    """Like autofit_textclip but for wrapped (method='caption') multi-line text."""
    size = start_size
    while size > min_size:
        kw = dict(text=text, font_size=size, color=color, method="caption",
                   size=(max_width, None), text_align=align)
        if font:
            kw["font"] = font
        clip = TextClip(**kw).with_duration(0.1)
        if clip.size[1] <= max_height:
            return clip
        size -= step
    kw = dict(text=text, font_size=min_size, color=color, method="caption",
               size=(max_width, None), text_align=align)
    if font:
        kw["font"] = font
    return TextClip(**kw).with_duration(0.1)


def find_font(bold=True):
    if os.path.exists(BUNDLED_FONT):
        return BUNDLED_FONT
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
            "/usr/share/fonts/truetype/noto/NotoSansBold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def find_impact_font():
    return IMPACT_FONT if os.path.exists(IMPACT_FONT) else find_font()


def wrap_caption(text, max_words=22):
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words]) + "..."
    return text


def load_logo_clip(target_height, duration):
    if not os.path.exists(LOGO_PATH):
        return None
    clip = ImageClip(LOGO_PATH).with_duration(duration)
    scale = target_height / clip.size[1]
    return clip.resized(scale)


def load_badge_clip(target_width, target_height, duration):
    if not os.path.exists(BADGE_PATH):
        return None
    clip = ImageClip(BADGE_PATH).with_duration(duration)
    w, h = clip.size
    scale = min(target_width / w, target_height / h)
    return clip.resized(scale)


def wrapped_text_clip(text, max_width, font, font_size, color, duration, align="center"):
    kw = dict(text=text, font_size=font_size, color=color, method="caption",
              size=(max_width, None), text_align=align)
    if font:
        kw["font"] = font
    return TextClip(**kw).with_duration(duration)


def build_banners(W, H, TOP_H, BOTTOM_H, total_duration, font):
    """Top yellow banner + bottom dark banner — shared across all templates."""
    layers = []

    layers.append(
        ColorClip(size=(W, TOP_H), color=YELLOW).with_duration(total_duration).with_position((0, 0))
    )
    logo_h = int(TOP_H * 0.65)
    logo_clip = load_logo_clip(logo_h, total_duration)
    logo_w = logo_clip.size[0] if logo_clip else 0
    if logo_clip:
        layers.append(logo_clip.with_position((W - logo_w - 16, (TOP_H - logo_h) // 2)))
    top_headline = autofit_wrapped(
        TOP_TEXT_HI, W - logo_w - 50, TOP_H - 10, font, 32, "black",
        min_size=16, align="left",
    )
    layers.append(top_headline.with_position((20, (TOP_H - top_headline.size[1]) // 2)))

    layers.append(
        ColorClip(size=(W, BOTTOM_H), color=DARK).with_duration(total_duration)
        .with_position((0, H - BOTTOM_H))
    )
    badge_h = int(BOTTOM_H * 0.95)
    badge_target_w = min(260, int(W * 0.32))
    badge_clip = load_badge_clip(badge_target_w, badge_h, total_duration)
    badge_w = badge_clip.size[0] if badge_clip else 16
    if badge_clip:
        layers.append(badge_clip.with_position((10, H - BOTTOM_H + (BOTTOM_H - badge_clip.size[1]) // 2)))
    share_text = autofit_wrapped(
        BOTTOM_TEXT_HI, W - badge_w - 60, BOTTOM_H - 10, font, 26, "white",
        min_size=14, align="left",
    )
    layers.append(share_text.with_position(
        (badge_w + 36, H - BOTTOM_H + (BOTTOM_H - share_text.size[1]) // 2)
    ))
    return layers


def ken_burns_clip(img, box_w, box_h, clip_dur, zoom_in, start_time):
    base = ImageClip(img).with_duration(clip_dur)
    iw, ih = base.size
    scale_cover = max(box_w / iw, box_h / ih)
    base = base.resized(scale_cover)
    s0, s1 = (1.0, 1.12) if zoom_in else (1.12, 1.0)

    def make_scale_fn(s0, s1, d):
        return lambda t: s0 + (s1 - s0) * (t / d if d > 0 else 0)

    kb = base.resized(make_scale_fn(s0, s1, clip_dur)).with_position("center")
    windowed = CompositeVideoClip([kb], size=(box_w, box_h)).with_duration(clip_dur)
    return windowed.with_effects([vfx.CrossFadeIn(0.4)]).with_start(start_time)
