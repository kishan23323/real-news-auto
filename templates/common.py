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


def fit_caption_block(text, max_width, max_height, font, start_size, color,
                       min_size=14, step=2, align="center"):
    """Guarantees the returned clip fits inside (max_width, max_height):
    1) shrink font size down to min_size, 2) if still too tall, trim words
    from the end until it fits, 3) hard-clip as a final safety net so text
    can NEVER visually bleed outside its box."""
    words = text.split()
    working_text = text
    clip = autofit_wrapped(working_text, max_width, max_height, font, start_size,
                            color, min_size=min_size, step=step, align=align)
    # If even at min_size it's still too tall, progressively trim words.
    tries = 0
    while clip.size[1] > max_height and len(words) > 3 and tries < 12:
        words = words[: max(3, int(len(words) * 0.8))]
        working_text = " ".join(words) + "…"
        clip = autofit_wrapped(working_text, max_width, max_height, font, start_size,
                                color, min_size=min_size, step=step, align=align)
        tries += 1
    # Final safety net: hard-clip to max_height so nothing can ever spill out.
    if clip.size[1] > max_height:
        cropped = CompositeVideoClip([clip.with_position((0, 0))],
                                      size=(clip.size[0], max_height)).with_duration(0.1)
        return cropped
    return clip


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


def load_logo_clip(target_height, duration, logo_path=None):
    path = logo_path if logo_path and os.path.exists(logo_path) else LOGO_PATH
    if not os.path.exists(path):
        return None
    clip = ImageClip(path).with_duration(duration)
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
    # Colors & visual
    "banner_color":     "#FFD100",
    "bottom_color":     "#121212",
    "frame_color":      "#C81414",
    "body_bg":           "#000000",
    "logo_position":    "top-right",
    "logo_shape":       "circle",
    "corner_radius":    28,
    "container_radius": 36,
    "headline_size":    64,
    "caption_size":     30,
    
    # TOP BANNER
    "top_height":       108,
    "top_padding":      8,
    "top_margin_lr":    0,
    "top_fixed_text":   "आज की 50 बड़ी खबरें",   # always static, never scrolls
    "top_text":         "मुख्य समाचार आम आदमी के काम की खबरें",  # scrolls
    "top_text_size":    34,
    "top_text_color":   "#000000",
    
    # LOGO
    "logo_size":        84,
    "logo_bg":          "#FFFFFF",
    "logo_border":      "#333333",
    "logo_path":        "",   # empty = use bundled default logo.png; else path to uploaded logo
    
    # MIDDLE CONTAINER
    "mid_border_width": 0,
    
    # IMAGE AREA
    "image_border":     6,
    "image_bg":         "#FFFFFF",
    "image_gradient_alpha": 0.45,
    
    # BREAKING NEWS
    "breaking_text":    "BREAKING NEWS",
    "breaking_text_color": "#FFFFFF",
    "breaking_bg":      "#8E0E0E",
    "breaking_outline":  "#FFFFFF",
    
    # CAPTION
    "caption_radius":   12,
    
    # BOTTOM BANNER
    "bottom_height":    72,
    "bottom_padding":   8,
    "bottom_margin_lr": 0,
    "bottom_text":      "अपने दोस्तों के साथ फेसबुक और व्हाट्सएप पर शेयर जरूर करें",
    "bottom_text_size": 28,
    "bottom_text_color": "#FFFFFF",
    "bottom_logo_size": 50,
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


def pill_clip(text, font, font_size, bg_hex, fg_hex, pad_x, pad_y, duration, min_size=18,
              outline_hex="#FFFFFF", outline_width=3):
    """Rounded-pill background behind bold text — used for the BREAKING NEWS badge.
    Always draws a contrasting outline so the box stays visible even if bg_hex
    happens to match the color behind it."""
    txt, used_size = autofit_textclip(text, 10_000, font, font_size, color=fg_hex,
                                       min_size=min_size, method="label")
    txt = txt.with_duration(duration)
    tw, th = txt.size
    box_w, box_h = tw + pad_x * 2, th + pad_y * 2
    radius = box_h // 2

    from PIL import Image as _PILImage, ImageDraw as _PILImageDraw
    import numpy as _np
    from moviepy import ImageClip as _ImageClip

    bg_rgb = _hex_to_rgb(bg_hex, RED)
    outline_rgb = _hex_to_rgb(outline_hex, WHITE)
    canvas = _PILImage.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = _PILImageDraw.Draw(canvas)
    draw.rounded_rectangle([0, 0, box_w - 1, box_h - 1], radius=radius,
                            fill=bg_rgb + (255,),
                            outline=outline_rgb + (255,) if outline_width > 0 else None,
                            width=outline_width)
    bg = _ImageClip(_np.array(canvas)).with_duration(duration)

    return CompositeVideoClip(
        [bg, txt.with_position(((box_w - tw) // 2, (box_h - th) // 2))],
        size=(box_w, box_h),
    ).with_duration(duration)


def circular_logo_clip(diameter, duration, ring_color="#333333", ring_width=5, logo_path=None):
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

    path = logo_path if logo_path and os.path.exists(logo_path) else LOGO_PATH
    layers = [bg_clip]
    if os.path.exists(path):
        inner = diameter - ring_width * 4
        logo = ImageClip(path).with_duration(duration)
        scale = inner / max(logo.size)
        logo = logo.resized(scale)
        lx = (diameter - logo.size[0]) // 2
        ly = (diameter - logo.size[1]) // 2
        layers.append(logo.with_position((lx, ly)))
    return CompositeVideoClip(layers, size=(diameter, diameter)).with_duration(duration)


def gradient_overlay_clip(w, h, duration, strength=0.45):
    """Edge vignette: TOP and BOTTOM strips darken slightly for legibility,
    the large MIDDLE area (where the subject is) stays fully clear."""
    from PIL import Image as _PILImage
    import numpy as _np
    from moviepy import ImageClip as _ImageClip

    grad = _np.zeros((h, 1), dtype="float32")
    top_band = 0.16     # top 16% fades from strength -> 0
    bottom_band = 0.16  # bottom 16% fades from 0 -> strength
    for y in range(h):
        rel = y / max(1, h - 1)  # 0 (top) to 1 (bottom)
        if rel < top_band:
            grad[y] = strength * (1 - rel / top_band)
        elif rel > 1 - bottom_band:
            grad[y] = strength * ((rel - (1 - bottom_band)) / bottom_band)
        else:
            grad[y] = 0.0  # main/middle area stays clear

    alpha = _np.tile(grad, (1, w))
    rgb = _np.zeros((h, w, 3), dtype="uint8")
    overlay = _ImageClip(rgb).with_duration(duration)
    mask = _ImageClip((alpha * 255).astype("uint8"), is_mask=True).with_duration(duration)
    return overlay.with_mask(mask.resized(new_size=(w, h)) if mask.size != (w, h) else mask)


def marquee_clip(text, font, font_size, color, box_w, box_h, duration, speed=140, align_v="center", force_scroll=False):
    """Right-to-left scrolling text clipped to a (box_w, box_h) window.
    By default, if the text already fits it stays static (no scrolling).
    Pass force_scroll=True to always scroll regardless of fit (e.g. for
    banners that should visibly move even when short)."""
    txt, _ = autofit_textclip(text, 100_000, font, font_size, color=color,
                               min_size=14, method="label", max_height=box_h)
    tw, th = txt.size
    y = 0 if align_v == "top" else (box_h - th) // 2

    if tw <= box_w and not force_scroll:
        static = txt.with_duration(duration).with_position(((box_w - tw) // 2, y))
        return CompositeVideoClip([static], size=(box_w, box_h)).with_duration(duration)

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
    """Top banner + bottom banner — reads all properties from style dict."""
    style = resolve_style(style)
    banner_rgb = _hex_to_rgb(style["banner_color"], YELLOW)
    bottom_rgb = _hex_to_rgb(style["bottom_color"], DARK)
    logo_left = style["logo_position"] == "top-left"
    circular = style["logo_shape"] == "circle"
    
    # Read text and styling properties
    top_text = style.get("top_text", TOP_TEXT_HI)
    top_text_size = style.get("top_text_size", 34)
    top_text_color = _hex_to_rgb(style.get("top_text_color", "#000000"), BLACK)
    top_padding = max(0, int(style.get("top_padding", 8)))
    top_margin_lr = max(0, int(style.get("top_margin_lr", 0)))
    
    bottom_text = style.get("bottom_text", BOTTOM_TEXT_HI)
    bottom_text_size = style.get("bottom_text_size", 28)
    bottom_text_color = _hex_to_rgb(style.get("bottom_text_color", "#FFFFFF"), WHITE)
    bottom_padding = max(0, int(style.get("bottom_padding", 8)))
    bottom_margin_lr = max(0, int(style.get("bottom_margin_lr", 0)))
    bottom_logo_size = style.get("bottom_logo_size", 50)
    
    logo_size = min(style.get("logo_size", int(TOP_H * 0.78)), TOP_H - 8)
    logo_bg = _hex_to_rgb(style.get("logo_bg", "#FFFFFF"), WHITE)
    logo_border = _hex_to_rgb(style.get("logo_border", "#333333"), (51, 51, 51))

    layers = []

    layers.append(
        ColorClip(size=(W, TOP_H), color=banner_rgb).with_duration(total_duration).with_position((0, 0))
    )
    
    if circular:
        logo_clip = circular_logo_clip(logo_size, total_duration, ring_color=style.get("logo_border", "#333333"),
                                        logo_path=style.get("logo_path") or None)
    else:
        logo_clip = load_logo_clip(logo_size, total_duration, logo_path=style.get("logo_path") or None)
    
    logo_w = logo_clip.size[0] if logo_clip else 0
    logo_pad = 14 + top_margin_lr
    logo_x = logo_pad if logo_left else W - logo_w - logo_pad
    logo_y = (TOP_H - (logo_clip.size[1] if logo_clip else 0)) // 2
    if logo_clip:
        layers.append(logo_clip.with_position((logo_x, logo_y)))

    text_x = logo_w + logo_pad * 2 if logo_left else 20 + top_margin_lr
    text_w = W - logo_w - logo_pad * 2 - 20 - top_margin_lr
    text_h = max(20, TOP_H - top_padding * 2)

    top_fixed_text = style.get("top_fixed_text", "")
    fixed_w = 0
    if top_fixed_text:
        fixed_clip, _ = autofit_textclip(top_fixed_text, text_w, font, top_text_size,
                                          color=top_text_color, min_size=14, method="label", max_height=text_h)
        fixed_clip = fixed_clip.with_duration(total_duration)
        fixed_w = fixed_clip.size[0]
        layers.append(fixed_clip.with_position((text_x, (TOP_H - fixed_clip.size[1]) // 2)))

    scroll_gap = 24 if top_fixed_text else 0
    scroll_x = text_x + fixed_w + scroll_gap
    scroll_w = max(40, text_w - fixed_w - scroll_gap)
    headline = marquee_clip(top_text, font, top_text_size, top_text_color, scroll_w, text_h,
                             total_duration, speed=110, force_scroll=True)
    layers.append(headline.with_position((scroll_x, (TOP_H - headline.size[1]) // 2)))

    layers.append(
        ColorClip(size=(W, BOTTOM_H), color=bottom_rgb).with_duration(total_duration)
        .with_position((0, H - BOTTOM_H))
    )

    # Bottom-left logo (real logo, not a possibly-missing badge image)
    if circular:
        bottom_logo_clip = circular_logo_clip(min(bottom_logo_size, BOTTOM_H - 8), total_duration,
                                               ring_color=style.get("logo_border", "#333333"),
                                               logo_path=style.get("logo_path") or None)
    else:
        bottom_logo_clip = load_logo_clip(min(bottom_logo_size, BOTTOM_H - 8), total_duration,
                                           logo_path=style.get("logo_path") or None)
    blogo_w = bottom_logo_clip.size[0] if bottom_logo_clip else 0
    blogo_x = 14 + bottom_margin_lr
    blogo_y = H - BOTTOM_H + (BOTTOM_H - (bottom_logo_clip.size[1] if bottom_logo_clip else 0)) // 2
    if bottom_logo_clip:
        layers.append(bottom_logo_clip.with_position((blogo_x, blogo_y)))

    share_x = blogo_w + 36 + bottom_margin_lr
    share_w = W - blogo_w - 60 - bottom_margin_lr
    share_h = max(16, BOTTOM_H - bottom_padding * 2)
    share_text = marquee_clip(bottom_text, font, bottom_text_size, bottom_text_color, share_w, share_h, total_duration, speed=130, force_scroll=True)
    layers.append(share_text.with_position((share_x, H - BOTTOM_H + (BOTTOM_H - share_text.size[1]) // 2)))
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
