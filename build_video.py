"""
News-style video builder — 4-zone TV layout:

  ┌─────────────────────────────────────────────────────────┐
  │  (breathing headline tag)   BREAKING | NEWS   (logo)     │  TOP bar
  ├───────────────────────────────┬───────────────────────────┤
  │                                │                           │
  │   LEFT: image with Ken Burns  │  RIGHT: colorful caption   │  MAIN
  │   zoom/pan — looks like video │  text (numbers/currency    │
  │   not a static photo          │  highlighted in a 2nd color│
  │                                │                           │
  ├─────────────────────────────────────────────────────────┤
  │  REAL NEWS ●   <scrolling related-content ticker>          │  BOTTOM bar
  └─────────────────────────────────────────────────────────┘

No emojis inside TextClip strings (renders as boxes with most fonts).
"""
import platform
import os
import re
import math
import numpy as np
from moviepy import (
    ImageClip, AudioFileClip, ColorClip,
    TextClip, CompositeVideoClip, VideoClip, vfx,
)

CHANNEL_NAME = "REAL NEWS"

# ── Layout constants (1280x720 canvas) ────────────────────────────────────
TOP_H    = 80
BOTTOM_H = 70
OB       = 6      # outer border thickness

NUM_COLOR  = "#00E5FF"   # cyan — numbers / currency / percentages
TEXT_COLOR = "#FFD700"   # gold — everything else


def _find_font(lang="en"):
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


def _wrap_caption(text, max_words=20):
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words]) + "..."
    return text


def _pill(text, font_size, text_color, bg_color, pos, duration, font,
          pad_x=18, pad_y=10):
    kw = dict(text=text, font_size=font_size, color=text_color, method="label")
    if font:
        kw["font"] = font
    txt = TextClip(**kw).with_duration(duration)
    w, h = txt.size
    bg = (
        ColorClip(size=(w + pad_x * 2, h + pad_y * 2), color=bg_color)
        .with_opacity(0.95).with_duration(duration).with_position(pos)
    )
    txt = txt.with_position((pos[0] + pad_x, pos[1] + pad_y)).with_duration(duration)
    return [bg, txt]


def _breathing_mask(w, h, duration, period=2.2, min_alpha=0.35, max_alpha=1.0):
    """A full-white mask whose overall opacity pulses (fade in/out loop)."""
    def make_frame(t):
        alpha = min_alpha + (max_alpha - min_alpha) * (0.5 + 0.5 * math.sin(2 * math.pi * t / period))
        return np.full((h, w), alpha, dtype=np.float64)
    return VideoClip(make_frame, is_mask=True, duration=duration)


def _breathing_text(text, font_size, color, pos, duration, font):
    kw = dict(text=text, font_size=font_size, color=color, method="label")
    if font:
        kw["font"] = font
    txt = TextClip(**kw).with_duration(duration).with_position(pos)
    w, h = txt.size
    mask = _breathing_mask(w, h, duration)
    return txt.with_mask(mask)


_NUM_RE = re.compile(r"[₹$%]|\d")


def _is_numeric_token(tok):
    return bool(_NUM_RE.search(tok))


def _colored_text_panel(text, width, height, duration, font, base_size=30,
                         line_height=44, align_top=True):
    """
    Lay out `text` word-by-word inside a (width, height) box, coloring
    number/currency/percentage tokens differently from the rest.
    Returns a list of positioned clips (no background — caller adds one).
    """
    words = text.split()
    clips = []
    x, y = 14, 14
    max_w = width - 28

    for w_ in words:
        color = NUM_COLOR if _is_numeric_token(w_) else TEXT_COLOR
        kw = dict(text=w_, font_size=base_size, color=color, method="label")
        if font:
            kw["font"] = font
        tok_clip = TextClip(**kw).with_duration(duration)
        tw, th = tok_clip.size

        if x + tw > max_w and x > 14:
            x = 14
            y += line_height

        if y + th > height - 10:
            break  # ran out of vertical space — stop laying out further words

        clips.append(tok_clip.with_position((x, y)))
        x += tw + 10

    return clips


def build_video(image_paths, captions, durations, audio_path, title,
                out_path="output.mp4", size=(1280, 720), lang="en"):
    W, H = size
    font = _find_font(lang=lang)
    audio = AudioFileClip(audio_path)
    total_duration = audio.duration

    MAIN_H  = H - TOP_H - BOTTOM_H
    LEFT_W  = int(W * 0.58)
    RIGHT_W = W - LEFT_W

    layers = []

    # ══════════════════════════════════════════════════════════════════
    # MAIN — LEFT: images with Ken Burns zoom (looks like video, not slides)
    # ══════════════════════════════════════════════════════════════════
    image_layers = []
    t = 0.0
    for i, (img, dur) in enumerate(zip(image_paths, durations)):
        clip_dur = dur + 0.4
        base = ImageClip(img).with_duration(clip_dur)
        # cover-fit into the left panel first
        iw, ih = base.size
        scale_cover = max(LEFT_W / iw, MAIN_H / ih)
        base = base.resized(scale_cover)

        # Ken Burns: slow continuous zoom, alternating zoom-in / zoom-out
        zoom_in = (i % 2 == 0)
        start_scale, end_scale = (1.0, 1.12) if zoom_in else (1.12, 1.0)
        def make_scale_fn(s0, s1, d):
            return lambda t: s0 + (s1 - s0) * (t / d if d > 0 else 0)
        kb = base.resized(make_scale_fn(start_scale, end_scale, clip_dur))
        kb = kb.with_position("center")

        # crop/contain into a fixed LEFT_W x MAIN_H window
        windowed = CompositeVideoClip([kb], size=(LEFT_W, MAIN_H)).with_duration(clip_dur)
        windowed = windowed.with_effects([vfx.CrossFadeIn(0.4)]).with_start(t)
        image_layers.append(windowed)
        t += dur

    left_panel = CompositeVideoClip(image_layers, size=(LEFT_W, MAIN_H)).with_duration(total_duration)
    layers.append(left_panel.with_position((0, TOP_H)))

    # ══════════════════════════════════════════════════════════════════
    # MAIN — RIGHT: colorful caption text panel
    # ══════════════════════════════════════════════════════════════════
    right_bg = (
        ColorClip(size=(RIGHT_W, MAIN_H), color=(20, 10, 40))
        .with_opacity(0.95).with_duration(total_duration)
        .with_position((LEFT_W, TOP_H))
    )
    layers.append(right_bg)

    t = 0.0
    for caption, dur in zip(captions, durations):
        clip_dur = dur + 0.3
        tok_clips = _colored_text_panel(
            _wrap_caption(caption, max_words=22), RIGHT_W, MAIN_H,
            clip_dur, font, base_size=30, line_height=44,
        )
        panel = CompositeVideoClip(tok_clips, size=(RIGHT_W, MAIN_H)).with_duration(clip_dur)
        panel = panel.with_effects([vfx.CrossFadeIn(0.3)]).with_start(t)
        panel = panel.with_position((LEFT_W, TOP_H))
        layers.append(panel)
        t += dur

    # ══════════════════════════════════════════════════════════════════
    # TOP bar
    # ══════════════════════════════════════════════════════════════════
    top_bg = (
        ColorClip(size=(W, TOP_H), color=(15, 15, 15))
        .with_opacity(0.9).with_duration(total_duration).with_position((0, 0))
    )
    layers.append(top_bg)

    # breathing headline tag (left) — comes and goes
    layers.append(_breathing_text(
        "AAJ KI BADI KHABREIN" if not font else "आज की बड़ी खबरें",
        24, "white", (16, 26), total_duration, font,
    ))

    # BREAKING NEWS split pill (center)
    breaking_kw = dict(text="BREAKING", font_size=26, color="white", method="label")
    news_kw     = dict(text="NEWS", font_size=26, color=(200, 20, 20), method="label")
    if font:
        breaking_kw["font"] = font
        news_kw["font"] = font
    breaking_txt = TextClip(**breaking_kw).with_duration(total_duration)
    news_txt     = TextClip(**news_kw).with_duration(total_duration)
    bw, bh = breaking_txt.size
    nw, nh = news_txt.size
    pad_x, pad_y = 16, 8
    total_w = (bw + 2 * pad_x) + (nw + 2 * pad_x)
    start_x = (W - total_w) // 2
    row_y = (TOP_H - (bh + 2 * pad_y)) // 2

    layers.append(ColorClip(size=(bw + 2 * pad_x, bh + 2 * pad_y), color=(190, 15, 15))
                  .with_opacity(1.0).with_duration(total_duration).with_position((start_x, row_y)))
    layers.append(ColorClip(size=(nw + 2 * pad_x, nh + 2 * pad_y), color=(255, 255, 255))
                  .with_opacity(1.0).with_duration(total_duration)
                  .with_position((start_x + bw + 2 * pad_x, row_y)))
    layers.append(breaking_txt.with_position((start_x + pad_x, row_y + pad_y)))
    layers.append(news_txt.with_position((start_x + bw + 2 * pad_x + pad_x, row_y + pad_y)))

    # logo chip (right)
    layers += _pill(CHANNEL_NAME, 20, "#FFD700", (25, 25, 25),
                     (W - 190, (TOP_H - 40) // 2), total_duration, font)

    # ══════════════════════════════════════════════════════════════════
    # BOTTOM bar — fixed channel tag + scrolling related-content ticker
    # ══════════════════════════════════════════════════════════════════
    bottom_bg = (
        ColorClip(size=(W, BOTTOM_H), color=(60, 0, 0))
        .with_opacity(0.95).with_duration(total_duration).with_position((0, H - BOTTOM_H))
    )
    layers.append(bottom_bg)

    fixed_w = 190
    layers += _pill(CHANNEL_NAME, 20, "white", (190, 15, 15),
                     (10, H - BOTTOM_H + (BOTTOM_H - 40) // 2), total_duration, font)

    ticker_kw = dict(
        text=f"  दोस्तों, रोजाना की ताजा खबरें देखने के लिए चैनल को सब्सक्राइब करें  --  {title[:100]}  --  ",
        font_size=24, color="#FFD700", method="label",
    )
    if font:
        ticker_kw["font"] = font
    ticker_txt = TextClip(**ticker_kw).with_duration(total_duration)
    tw, th = ticker_txt.size
    scroll_speed = 130
    loop_w = tw + (W - fixed_w)
    ticker_y = H - BOTTOM_H + (BOTTOM_H - th) // 2

    def ticker_pos(t):
        x = (W - fixed_w) - (t * scroll_speed) % loop_w
        return (x, ticker_y)

    # mask the ticker so it doesn't visually overlap the fixed channel chip
    ticker_clip = CompositeVideoClip(
        [ticker_txt.with_position(ticker_pos)], size=(W - fixed_w, BOTTOM_H)
    ).with_duration(total_duration).with_position((fixed_w, H - BOTTOM_H))
    layers.append(ticker_clip)

    # ══════════════════════════════════════════════════════════════════
    # Outer border frame
    # ══════════════════════════════════════════════════════════════════
    border_color = (200, 20, 20)
    layers += [
        ColorClip(size=(W, OB), color=border_color).with_duration(total_duration).with_position((0, 0)),
        ColorClip(size=(W, OB), color=border_color).with_duration(total_duration).with_position((0, H - OB)),
        ColorClip(size=(OB, H), color=border_color).with_duration(total_duration).with_position((0, 0)),
        ColorClip(size=(OB, H), color=border_color).with_duration(total_duration).with_position((W - OB, 0)),
    ]

    final = CompositeVideoClip(layers, size=size).with_audio(audio)

    final.write_videofile(
        out_path, fps=24, codec="libx264",
        audio_codec="aac", preset="ultrafast",
        threads=4, logger="bar",
    )
    return out_path
