"""
Professional horizontal news TV graphic, 16:9.

┌─────────────────────────────────────────────────────────────┐
│  YELLOW BANNER (10%): Hindi headline text     [circle logo]  │
├─────────────────────────────────────────────────────────────┤
│  ┆ (padding)                                                 │
│  ┆   ┌───────────────────────┐ ┌───────────────────────┐    │
│  ┆   │                       │ │  BREAKING NEWS (red)   │    │
│  ┆   │   LEFT: image with    │ ├───────────────────────┤    │
│  ┆   │   Ken Burns zoom      │ │  YELLOW caption box    │    │
│  ┆   │   (looks like video)  │ │  (black bold text)     │    │
│  ┆   │                       │ │                        │    │
│  ┆   └───────────────────────┘ └───────────────────────┘    │
│  ┆ (padding)                       [red frame around all]   │
├─────────────────────────────────────────────────────────────┤
│  [BREAKING NEWS badge]   Hindi share-reminder text (white)   │
└─────────────────────────────────────────────────────────────┘

No emojis in TextClip strings — most fonts render them as boxes.
"""
import platform
import os
import math
import numpy as np
from PIL import Image, ImageDraw
from moviepy import (
    ImageClip, AudioFileClip, ColorClip,
    TextClip, CompositeVideoClip, vfx,
)

CHANNEL_NAME = "REAL NEWS"

YELLOW      = (255, 209, 0)
RED         = (200, 20, 20)
DARK        = (18, 18, 18)
BLACK       = (0, 0, 0)
WHITE       = (255, 255, 255)
BLUE        = (20, 70, 190)

TOP_TEXT_HI = "आज की 50 बड़ी खबरें , मुख्य समाचार आम आदमी के काम की खबरें"
BOTTOM_TEXT_HI = "अपने दोस्तों के साथ फेसबुक और व्हाट्सएप पर शेयर जरूर करें"


ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
BUNDLED_FONT = os.path.join(ASSETS_DIR, "fonts", "NotoSansDevanagari-Bold.ttf")
IMPACT_FONT  = os.path.join(ASSETS_DIR, "fonts", "Anton-Regular.ttf")   # English-only headline font
LOGO_PATH    = os.path.join(ASSETS_DIR, "logo.png")
BADGE_PATH   = os.path.join(ASSETS_DIR, "breaking_news_badge.png")


def _autofit_textclip(text, max_width, font, start_size, color="white",
                       min_size=16, step=2, method="label", max_height=None):
    """
    Render `text` as large as possible while guaranteeing it fits within
    max_width (and max_height if given) — prevents the 'text partially
    hidden/clipped' bug that happens when a font size is picked without
    checking actual rendered size.
    """
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


def _autofit_wrapped(text, max_width, max_height, font, start_size, color,
                      min_size=14, step=2, align="left"):
    """Like _autofit_textclip but for wrapped (method='caption') multi-line text."""
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


def _find_font(bold=True):
    # Bundled font first — covers Devanagari *and* Latin/numbers/symbols in one
    # file, so it renders consistently regardless of OS or what's installed
    # system-wide. (System Devanagari fonts like Windows' mangal.ttf often
    # lack Latin glyphs entirely, which is what causes English text to show
    # as boxes when loaded directly by filename.)
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


def _find_impact_font():
    return IMPACT_FONT if os.path.exists(IMPACT_FONT) else _find_font()


def _wrap_caption(text, max_words=22):
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words]) + "..."
    return text


def _load_logo_clip(target_height, duration):
    """Load the user's own logo asset, scaled to fit target_height."""
    if not os.path.exists(LOGO_PATH):
        return None
    clip = ImageClip(LOGO_PATH).with_duration(duration)
    scale = target_height / clip.size[1]
    return clip.resized(scale)


def _load_badge_clip(target_width, target_height, duration):
    """Load the user's own BREAKING NEWS badge asset, fit within target box."""
    if not os.path.exists(BADGE_PATH):
        return None
    clip = ImageClip(BADGE_PATH).with_duration(duration)
    w, h = clip.size
    scale = min(target_width / w, target_height / h)
    return clip.resized(scale)


def _pill(text, font_size, text_color, bg_color, pos, duration, font,
          pad_x=16, pad_y=8, outline_color=None, outline_w=0):
    kw = dict(text=text, font_size=font_size, color=text_color, method="label")
    if font:
        kw["font"] = font
    txt = TextClip(**kw).with_duration(duration)
    w, h = txt.size
    clips = []
    bw, bh = w + pad_x * 2, h + pad_y * 2
    if outline_color and outline_w:
        clips.append(
            ColorClip(size=(bw + outline_w * 2, bh + outline_w * 2), color=outline_color)
            .with_duration(duration)
            .with_position((pos[0] - outline_w, pos[1] - outline_w))
        )
    clips.append(ColorClip(size=(bw, bh), color=bg_color).with_duration(duration).with_position(pos))
    clips.append(txt.with_position((pos[0] + pad_x, pos[1] + pad_y)).with_duration(duration))
    return clips


def _wrapped_text_clip(text, max_width, font, font_size, color, duration,
                        align="center"):
    kw = dict(text=text, font_size=font_size, color=color, method="caption",
              size=(max_width, None), text_align=align)
    if font:
        kw["font"] = font
    return TextClip(**kw).with_duration(duration)


def build_video(image_paths, captions, durations, audio_path, title,
                out_path="output.mp4", size=(1280, 720), lang="hi", tmp_dir="/tmp"):
    W, H = size
    font = _find_font()
    audio = AudioFileClip(audio_path)
    total_duration = audio.duration

    TOP_H    = round(H * 0.10)
    BOTTOM_H = round(H * 0.10)
    MID_H    = H - TOP_H - BOTTOM_H         # the red-framed area (80%)

    RED_BORDER   = 8
    PAD_TB       = round(MID_H * 0.10)      # empty space top/bottom inside red box
    CONTENT_H    = MID_H - 2 * PAD_TB
    SIDE_MARGIN  = 16
    GAP          = 10
    HALF_W       = (W - 2 * SIDE_MARGIN - GAP) // 2

    layers = []

    # ══════════════════════════════════════════════════════════════
    # TOP: yellow banner + user's own circular logo
    # ══════════════════════════════════════════════════════════════
    layers.append(
        ColorClip(size=(W, TOP_H), color=YELLOW).with_duration(total_duration).with_position((0, 0))
    )
    logo_h = int(TOP_H * 0.65)   # "Medium" size per style spec
    logo_clip = _load_logo_clip(logo_h, total_duration)
    logo_w = logo_clip.size[0] if logo_clip else 0
    if logo_clip:
        layers.append(logo_clip.with_position((W - logo_w - 16, (TOP_H - logo_h) // 2)))
    top_headline = _autofit_wrapped(
        TOP_TEXT_HI, W - logo_w - 50, TOP_H - 10, font, 32, "black",
        min_size=18, align="left",
    )
    layers.append(top_headline.with_position((20, (TOP_H - top_headline.size[1]) // 2)))

    # ══════════════════════════════════════════════════════════════
    # BOTTOM: dark banner + user's own BREAKING NEWS badge + white text
    # ══════════════════════════════════════════════════════════════
    layers.append(
        ColorClip(size=(W, BOTTOM_H), color=DARK).with_duration(total_duration)
        .with_position((0, H - BOTTOM_H))
    )
    badge_h = int(BOTTOM_H * 0.95)   # "Large" size per style spec
    badge_clip = _load_badge_clip(260, badge_h, total_duration)
    badge_w = badge_clip.size[0] if badge_clip else 16
    if badge_clip:
        layers.append(badge_clip.with_position((10, H - BOTTOM_H + (BOTTOM_H - badge_clip.size[1]) // 2)))
    share_text = _autofit_wrapped(
        BOTTOM_TEXT_HI, W - badge_w - 60, BOTTOM_H - 10, font, 26, "white",
        min_size=16, align="left",
    )
    layers.append(share_text.with_position(
        (badge_w + 36, H - BOTTOM_H + (BOTTOM_H - share_text.size[1]) // 2)
    ))

    # ══════════════════════════════════════════════════════════════
    # MIDDLE: red frame + left image (Ken Burns) + right news box
    # ══════════════════════════════════════════════════════════════
    # red frame (drawn as border strips — a clean sharp rectangle;
    # at this resolution a 5px corner radius would be visually imperceptible,
    # so it's simplified to a crisp rectangular frame for reliability)
    frame_y = TOP_H
    layers += [
        ColorClip(size=(W, RED_BORDER), color=RED).with_duration(total_duration).with_position((0, frame_y)),
        ColorClip(size=(W, RED_BORDER), color=RED).with_duration(total_duration).with_position((0, frame_y + MID_H - RED_BORDER)),
        ColorClip(size=(RED_BORDER, MID_H), color=RED).with_duration(total_duration).with_position((0, frame_y)),
        ColorClip(size=(RED_BORDER, MID_H), color=RED).with_duration(total_duration).with_position((W - RED_BORDER, frame_y)),
    ]

    content_y = frame_y + PAD_TB
    left_x  = SIDE_MARGIN
    right_x = SIDE_MARGIN + HALF_W + GAP

    # ── LEFT: images with Ken Burns zoom (video-like motion) ──────
    image_layers = []
    t = 0.0
    for i, (img, dur) in enumerate(zip(image_paths, durations)):
        clip_dur = dur + 0.4
        base = ImageClip(img).with_duration(clip_dur)
        iw, ih = base.size
        scale_cover = max(HALF_W / iw, CONTENT_H / ih)
        base = base.resized(scale_cover)

        zoom_in = (i % 2 == 0)
        s0, s1 = (1.0, 1.12) if zoom_in else (1.12, 1.0)
        def make_scale_fn(s0, s1, d):
            return lambda t: s0 + (s1 - s0) * (t / d if d > 0 else 0)
        kb = base.resized(make_scale_fn(s0, s1, clip_dur)).with_position("center")

        windowed = CompositeVideoClip([kb], size=(HALF_W, CONTENT_H)).with_duration(clip_dur)
        windowed = windowed.with_effects([vfx.CrossFadeIn(0.4)]).with_start(t)
        image_layers.append(windowed)
        t += dur

    left_panel = CompositeVideoClip(image_layers, size=(HALF_W, CONTENT_H)).with_duration(total_duration)
    layers.append(left_panel.with_position((left_x, content_y)))

    # ── RIGHT: red "BREAKING NEWS" box + yellow caption box ────────
    breaking_h = int(CONTENT_H * 0.18)   # slightly taller to fit a bigger headline
    layers.append(
        ColorClip(size=(HALF_W, breaking_h), color=RED).with_duration(total_duration)
        .with_position((right_x, content_y))
    )
    impact_font = _find_impact_font()
    bn_txt, _ = _autofit_textclip(
        "BREAKING NEWS", HALF_W - 30, impact_font, start_size=64, color="white",
        min_size=22, max_height=breaking_h - 14,
    )
    bn_txt = bn_txt.with_duration(total_duration)
    layers.append(bn_txt.with_position(
        (right_x + (HALF_W - bn_txt.size[0]) // 2, content_y + (breaking_h - bn_txt.size[1]) // 2)
    ))

    yellow_gap = 8
    yellow_y = content_y + breaking_h + yellow_gap
    yellow_h = CONTENT_H - breaking_h - yellow_gap
    layers.append(
        ColorClip(size=(HALF_W, yellow_h), color=YELLOW).with_duration(total_duration)
        .with_position((right_x, yellow_y))
    )

    t = 0.0
    for caption, dur in zip(captions, durations):
        clip_dur = dur + 0.3
        cap_clip = _wrapped_text_clip(
            _wrap_caption(caption), HALF_W - 40, font, 30, "black", clip_dur, align="center",
        )
        cap_clip = cap_clip.with_effects([vfx.CrossFadeIn(0.3)]).with_start(t)
        cap_clip = cap_clip.with_position(
            (right_x + 20, yellow_y + max(10, (yellow_h - cap_clip.size[1]) // 2))
        )
        layers.append(cap_clip)
        t += dur

    # ══════════════════════════════════════════════════════════════
    final = CompositeVideoClip(layers, size=size).with_audio(audio)
    final.write_videofile(
        out_path, fps=24, codec="libx264",
        audio_codec="aac", preset="ultrafast",
        threads=4, logger="bar",
    )
    return out_path
