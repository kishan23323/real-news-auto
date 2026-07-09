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


DEFAULT_STYLE = {
    "banner_color":     "#FFD100",   # top yellow banner
    "bottom_color":     "#121212",   # bottom dark banner
    "frame_color":      "#C81414",   # middle red container + BREAKING NEWS pill
    "logo_position":    "top-right", # "top-right" | "top-left"
    "logo_shape":       "circle",    # "circle" | "square"
    "corner_radius":    28,          # rounded corners on the image panel(s), in px (canvas-relative)
    "container_radius": 36,          # rounded corners on the big middle container
    "headline_size":    64,          # "BREAKING NEWS" pill starting font size
    "caption_size":     30,          # caption text starting font size
}


def resolve_style(style=None):
    """Merge a partial style dict on top of the defaults."""
    merged = dict(DEFAULT_STYLE)
    if style:
        merged.update({k: v for k, v in style.items() if v is not None})
    return merged


def _hex_to_rgb(h, fallback):
    if not h:
        return fallback
    h = h.lstrip('#')
    if len(h) != 6:
        return fallback
    try:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        return fallback


def rounded_mask_clip(w, h, radius, duration):
    """Build a moviepy mask clip with rounded corners (radius in px), or None if radius<=0."""
    if radius <= 0:
        return None
    from PIL import Image as _PILImage, ImageDraw as _PILImageDraw
    import numpy as _np
    from moviepy import ImageClip as _ImageClip
    mask_img = _PILImage.new("L", (w, h), 0)
    draw = _PILImageDraw.Draw(mask_img)
    draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    mask_arr = _np.array(mask_img).astype("float32") / 255.0
    return _ImageClip(mask_arr, is_mask=True).with_duration(duration)


def pill_clip(text, font, font_size, bg_hex, fg_hex, pad_x, pad_y, duration, min_size=18):
    """Rounded-pill background behind bold text — used for the BREAKING NEWS badge."""
    txt, used_size = autofit_textclip(text, 10_000, font, font_size, color=fg_hex,
                                       min_size=min_size, method="label")
    txt = txt.with_duration(duration)
    tw, th = txt.size
    box_w, box_h = tw + pad_x * 2, th + pad_y * 2
    bg = ColorClip(size=(box_w, box_h), color=_hex_to_rgb(bg_hex, RED)).with_duration(duration)
    radius = box_h // 2
    mask = rounded_mask_clip(box_w, box_h, radius, duration)
    if mask is not None:
        bg = bg.with_mask(mask)
    return CompositeVideoClip(
        [bg, txt.with_position(((box_w - tw) // 2, (box_h - th) // 2))],
        size=(box_w, box_h),
    ).with_duration(duration)


def circular_logo_clip(diameter, duration, ring_color="#333333", ring_width=5):
    """Logo inside a white circle with a solid ring border, mimicking a
    dashed circular frame without needing per-frame dash rendering."""
    from PIL import Image as _PILImage, ImageDraw as _PILImageDraw
    import numpy as _np
    from moviepy import ImageClip as _ImageClip

    canvas = _PILImage.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    draw = _PILImageDraw.Draw(canvas)
    draw.ellipse([0, 0, diameter - 1, diameter - 1], fill=(255, 255, 255, 255))
    ring_rgb = _hex_to_rgb(ring_color, (51, 51, 51))
    draw.ellipse([0, 0, diameter - 1, diameter - 1], outline=ring_rgb + (255,), width=ring_width)
    bg_clip = _ImageClip(_np.array(canvas)).with_duration(duration)

    layers = [bg_clip]
    if os.path.exists(LOGO_PATH):
        inner = diameter - ring_width * 4
        logo = ImageClip(LOGO_PATH).with_duration(duration)
        scale = inner / max(logo.size)
        logo = logo.resized(scale)
        lx = (diameter - logo.size[0]) // 2
        ly = (diameter - logo.size[1]) // 2
        layers.append(logo.with_position((lx, ly)))
    return CompositeVideoClip(layers, size=(diameter, diameter)).with_duration(duration)


def gradient_overlay_clip(w, h, duration, strength=0.45):
    """Soft dark gradient (transparent → dark → transparent, top to bottom)
    laid over an image panel for text legibility, matching the reference's
    linear-gradient overlay on the main image."""
    from PIL import Image as _PILImage
    import numpy as _np
    from moviepy import ImageClip as _ImageClip

    grad = _np.zeros((h, 1), dtype="float32")
    band_top, band_bot = int(h * 0.10), int(h * 0.90)
    for y in range(h):
        if y < band_top:
            grad[y] = 0
        elif y > band_bot:
            grad[y] = 0
        else:
            rel = (y - band_top) / max(1, (band_bot - band_top))
            grad[y] = strength * (1 - abs(rel * 2 - 1))
    alpha = _np.tile(grad, (1, w))
    rgb = _np.zeros((h, w, 3), dtype="uint8")
    overlay = _ImageClip(rgb).with_duration(duration)
    mask = _ImageClip((alpha * 255).astype("uint8"), is_mask=True).with_duration(duration)
    return overlay.with_mask(mask.resized(new_size=(w, h)) if mask.size != (w, h) else mask)


def marquee_clip(text, font, font_size, color, box_w, box_h, duration, speed=140, align_v="center"):
    """Continuously right-to-left scrolling text clipped to a (box_w, box_h)
    window — mimics the reference's <marquee> banners."""
    txt, _ = autofit_textclip(text, 100_000, font, font_size, color=color,
                               min_size=14, method="label", max_height=box_h)
    tw, th = txt.size
    y = 0 if align_v == "top" else (box_h - th) // 2
    period = max(1, box_w + tw)

    def pos(t):
        x = box_w - ((t * speed) % period)
        return (x, y)

    scrolling = txt.with_duration(duration).with_position(pos)
    return CompositeVideoClip([scrolling], size=(box_w, box_h)).with_duration(duration)


def wrapped_text_clip(text, max_width, font, font_size, color, duration, align="center"):
    kw = dict(text=text, font_size=font_size, color=color, method="caption",
              size=(max_width, None), text_align=align)
    if font:
        kw["font"] = font
    return TextClip(**kw).with_duration(duration)


def build_banners(W, H, TOP_H, BOTTOM_H, total_duration, font, style=None):
    """Top banner + bottom banner — shared across all templates. Colors,
    logo shape/position, and marquee text come from `style` (see
    DEFAULT_STYLE), matching the reference HTML design."""
    style = resolve_style(style)
    banner_rgb = _hex_to_rgb(style["banner_color"], YELLOW)
    bottom_rgb = _hex_to_rgb(style["bottom_color"], DARK)
    logo_left = style["logo_position"] == "top-left"
    circular = style["logo_shape"] == "circle"

    layers = []

    layers.append(
        ColorClip(size=(W, TOP_H), color=banner_rgb).with_duration(total_duration).with_position((0, 0))
    )
    logo_d = int(TOP_H * 0.78)
    if circular:
        logo_clip = circular_logo_clip(logo_d, total_duration)
    else:
        logo_clip = load_logo_clip(logo_d, total_duration)
    logo_w = logo_clip.size[0] if logo_clip else 0
    logo_pad = 14
    logo_x = logo_pad if logo_left else W - logo_w - logo_pad
    logo_y = (TOP_H - (logo_clip.size[1] if logo_clip else 0)) // 2
    if logo_clip:
        layers.append(logo_clip.with_position((logo_x, logo_y)))

    text_x = logo_w + logo_pad * 2 if logo_left else 20
    text_w = W - logo_w - logo_pad * 2 - 20
    headline = marquee_clip(TOP_TEXT_HI, font, 34, "black", text_w, TOP_H - 10, total_duration, speed=110)
    layers.append(headline.with_position((text_x, (TOP_H - headline.size[1]) // 2)))

    layers.append(
        ColorClip(size=(W, BOTTOM_H), color=bottom_rgb).with_duration(total_duration)
        .with_position((0, H - BOTTOM_H))
    )
    badge_h = int(BOTTOM_H * 0.82)
    badge_target_w = min(260, int(W * 0.30))
    badge_clip = load_badge_clip(badge_target_w, badge_h, total_duration)
    badge_w = badge_clip.size[0] if badge_clip else 16
    badge_y = H - BOTTOM_H + (BOTTOM_H - (badge_clip.size[1] if badge_clip else 0)) // 2
    if badge_clip:
        layers.append(badge_clip.with_position((14, badge_y)))
    share_w = W - badge_w - 60
    share_text = marquee_clip(BOTTOM_TEXT_HI, font, 28, "white", share_w, BOTTOM_H - 14, total_duration, speed=130)
    layers.append(share_text.with_position((badge_w + 36, H - BOTTOM_H + (BOTTOM_H - share_text.size[1]) // 2)))
    return layers


def ken_burns_clip(img, box_w, box_h, clip_dur, zoom_in, start_time, corner_radius=0):
    base = ImageClip(img).with_duration(clip_dur)
    iw, ih = base.size
    scale_cover = max(box_w / iw, box_h / ih)
    base = base.resized(scale_cover)
    s0, s1 = (1.0, 1.12) if zoom_in else (1.12, 1.0)

    def make_scale_fn(s0, s1, d):
        return lambda t: s0 + (s1 - s0) * (t / d if d > 0 else 0)

    kb = base.resized(make_scale_fn(s0, s1, clip_dur)).with_position("center")
    windowed = CompositeVideoClip([kb], size=(box_w, box_h)).with_duration(clip_dur)
    mask = rounded_mask_clip(box_w, box_h, corner_radius, clip_dur)
    if mask is not None:
        windowed = windowed.with_mask(mask)
    return windowed.with_effects([vfx.CrossFadeIn(0.4)]).with_start(start_time)
