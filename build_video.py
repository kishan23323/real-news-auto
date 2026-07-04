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


def _find_font(bold=True):
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


def _wrap_caption(text, max_words=22):
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words]) + "..."
    return text


def _make_circle_logo(diameter=64, tmp_dir="/tmp"):
    """Blue ring, red fill, white triangle in the center — 'REAL NEWS' icon."""
    size = diameter * 4  # supersample for smooth edges, downscale at the end
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, size - 1, size - 1], fill=BLUE + (255,))
    ring = int(size * 0.10)
    d.ellipse([ring, ring, size - 1 - ring, size - 1 - ring], fill=RED + (255,))
    # white triangle pointing right, centered
    cx, cy = size / 2, size / 2
    tw, th = size * 0.30, size * 0.34
    pts = [(cx - tw / 2, cy - th / 2), (cx - tw / 2, cy + th / 2), (cx + tw / 2, cy)]
    d.polygon(pts, fill=WHITE + (255,))
    img = img.resize((diameter, diameter), Image.LANCZOS)
    path = os.path.join(tmp_dir, "_real_news_logo.png")
    img.save(path)
    return path


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
    # TOP: yellow banner + circular logo
    # ══════════════════════════════════════════════════════════════
    layers.append(
        ColorClip(size=(W, TOP_H), color=YELLOW).with_duration(total_duration).with_position((0, 0))
    )
    logo_path = _make_circle_logo(diameter=int(TOP_H * 0.75), tmp_dir=tmp_dir)
    logo_clip = (
        ImageClip(logo_path).with_duration(total_duration)
        .with_position((W - int(TOP_H * 0.75) - 130, (TOP_H - int(TOP_H * 0.75)) // 2))
    )
    layers.append(logo_clip)
    logo_kw = dict(text=CHANNEL_NAME, font_size=20, color="black", method="label")
    if font:
        logo_kw["font"] = font
    logo_text = TextClip(**logo_kw).with_duration(total_duration)
    layers.append(logo_text.with_position(
        (W - 120, (TOP_H - logo_text.size[1]) // 2)
    ))
    top_headline = _wrapped_text_clip(
        TOP_TEXT_HI, W - int(TOP_H * 0.75) - 160, font, 26, "black", total_duration, align="left",
    )
    layers.append(top_headline.with_position((20, (TOP_H - top_headline.size[1]) // 2)))

    # ══════════════════════════════════════════════════════════════
    # BOTTOM: dark banner + red/black BREAKING NEWS badge + white text
    # ══════════════════════════════════════════════════════════════
    layers.append(
        ColorClip(size=(W, BOTTOM_H), color=DARK).with_duration(total_duration)
        .with_position((0, H - BOTTOM_H))
    )
    badge_h = int(BOTTOM_H * 0.6)
    badge_y = H - BOTTOM_H + (BOTTOM_H - badge_h) // 2
    layers += _pill(
        "BREAKING NEWS", 20, "white", RED, (16, badge_y), total_duration, font,
        pad_x=14, pad_y=8, outline_color=BLACK, outline_w=4,
    )
    # figure out badge width to place the share-text after it
    badge_probe_kw = dict(text="BREAKING NEWS", font_size=20, color="white", method="label")
    if font:
        badge_probe_kw["font"] = font
    badge_w = TextClip(**badge_probe_kw).with_duration(0.1).size[0] + 2 * 14 + 2 * 4
    share_text = _wrapped_text_clip(
        BOTTOM_TEXT_HI, W - badge_w - 60, font, 22, "white", total_duration, align="left",
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
    breaking_h = int(CONTENT_H * 0.16)
    layers.append(
        ColorClip(size=(HALF_W, breaking_h), color=RED).with_duration(total_duration)
        .with_position((right_x, content_y))
    )
    bn_kw = dict(text="BREAKING NEWS", font_size=32, color="white", method="label")
    if font:
        bn_kw["font"] = font
    bn_txt = TextClip(**bn_kw).with_duration(total_duration)
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
