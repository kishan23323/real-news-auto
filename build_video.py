"""
News-style video builder - NO EMOJIS in text clips (causes boxes).
Uses plain text alternatives that render correctly with any font.

Adds a "breaking news" TV-style frame:
  - Red outer border around the whole video
  - Top-left "REAL NEWS" badge + top-right logo chip
  - Centered "BREAKING NEWS" split pill
  - Gold headline title card with a white border (first 6s)
  - Scrolling gold ticker strip above the caption bar
"""
import platform
import os
from moviepy import (
    ImageClip, AudioFileClip, ColorClip,
    TextClip, CompositeVideoClip, vfx,
)

CHANNEL_NAME = "REAL NEWS"


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


def _wrap_caption(text, max_words=16):
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words]) + "..."
    return text


def _pill(text, font_size, text_color, bg_color, pos, duration, font,
          pad_x=18, pad_y=10):
    """A background chip + centered text, positioned together."""
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


def build_video(image_paths, captions, durations, audio_path, title,
                out_path="output.mp4", size=(1280, 720), lang="en"):
    W, H = size
    font = _find_font(lang=lang)
    audio = AudioFileClip(audio_path)
    total_duration = audio.duration

    BAR_H    = 160   # bottom caption bar
    TICKER_H = 40    # scrolling ticker strip
    OB       = 8     # outer border thickness

    # ── Background images ───────────────────────────────────────────────
    image_clips = []
    t = 0.0
    for img, dur in zip(image_paths, durations):
        clip = (
            ImageClip(img).resized(height=H).with_position("center")
            .with_start(t).with_duration(dur + 0.5)
            .with_effects([vfx.CrossFadeIn(0.4)])
        )
        image_clips.append(clip)
        t += dur

    layers = list(image_clips)

    # ── Outer red border frame ──────────────────────────────────────────
    border_color = (200, 20, 20)
    layers += [
        ColorClip(size=(W, OB), color=border_color).with_opacity(1.0)
        .with_duration(total_duration).with_position((0, 0)),
        ColorClip(size=(W, OB), color=border_color).with_opacity(1.0)
        .with_duration(total_duration).with_position((0, H - OB)),
        ColorClip(size=(OB, H), color=border_color).with_opacity(1.0)
        .with_duration(total_duration).with_position((0, 0)),
        ColorClip(size=(OB, H), color=border_color).with_opacity(1.0)
        .with_duration(total_duration).with_position((W - OB, 0)),
    ]

    # ── Top strip background (behind badges) ────────────────────────────
    top_bar = (
        ColorClip(size=(W - 2 * OB, 55), color=(15, 15, 15))
        .with_opacity(0.85).with_duration(total_duration)
        .with_position((OB, OB))
    )
    layers.append(top_bar)

    # Top-left "REAL NEWS" badge
    layers += _pill(CHANNEL_NAME, 26, "white", (190, 15, 15),
                     (OB + 12, OB + 8), total_duration, font)

    # Top-right logo chip
    layers += _pill("REAL | NEWS", 22, "#FFD700", (25, 25, 25),
                     (W - OB - 210, OB + 8), total_duration, font)

    # ── Centered "BREAKING NEWS" split pill ─────────────────────────────
    breaking_kw = dict(text="BREAKING", font_size=30, color="white", method="label")
    news_kw     = dict(text="NEWS", font_size=30, color=(200, 20, 20), method="label")
    if font:
        breaking_kw["font"] = font
        news_kw["font"] = font
    breaking_txt = TextClip(**breaking_kw).with_duration(total_duration)
    news_txt     = TextClip(**news_kw).with_duration(total_duration)
    bw, bh = breaking_txt.size
    nw, nh = news_txt.size
    pad_x, pad_y = 20, 10
    total_w = (bw + 2 * pad_x) + (nw + 2 * pad_x)
    start_x = (W - total_w) // 2
    row_y = OB + 55 + 10

    breaking_bg = (
        ColorClip(size=(bw + 2 * pad_x, bh + 2 * pad_y), color=(190, 15, 15))
        .with_opacity(1.0).with_duration(total_duration)
        .with_position((start_x, row_y))
    )
    news_bg = (
        ColorClip(size=(nw + 2 * pad_x, nh + 2 * pad_y), color=(255, 255, 255))
        .with_opacity(1.0).with_duration(total_duration)
        .with_position((start_x + bw + 2 * pad_x, row_y))
    )
    breaking_txt = breaking_txt.with_position((start_x + pad_x, row_y + pad_y))
    news_txt     = news_txt.with_position((start_x + bw + 2 * pad_x + pad_x, row_y + pad_y))
    layers += [breaking_bg, news_bg, breaking_txt, news_txt]

    # ── Gold title card with white border (first 6s) ────────────────────
    title_y = row_y + bh + 2 * pad_y + 12
    title_h = 90
    title_dur = min(6, total_duration)
    title_border = (
        ColorClip(size=(W - 2 * OB - 20, title_h), color=(255, 255, 255))
        .with_opacity(0.9).with_duration(title_dur)
        .with_position((OB + 10, title_y))
    )
    title_bg = (
        ColorClip(size=(W - 2 * OB - 26, title_h - 6), color=(0, 0, 0))
        .with_opacity(0.85).with_duration(title_dur)
        .with_position((OB + 13, title_y + 3))
    )
    title_kw = dict(
        text=title[:120], font_size=34, color="#FFD700", method="caption",
        size=(W - 2 * OB - 60, title_h - 20),
    )
    if font:
        title_kw["font"] = font
    title_clip = TextClip(**title_kw).with_duration(title_dur).with_position(
        (OB + 30, title_y + 10)
    )
    layers += [title_border, title_bg, title_clip]

    # ── Scrolling gold ticker (above caption bar) ────────────────────────
    ticker_y = H - BAR_H - TICKER_H
    ticker_bg = (
        ColorClip(size=(W - 2 * OB, TICKER_H), color=(60, 0, 0))
        .with_opacity(0.9).with_duration(total_duration)
        .with_position((OB, ticker_y))
    )
    layers.append(ticker_bg)

    ticker_kw = dict(
        text=f"  {CHANNEL_NAME} : दोस्तों, रोजाना की ताजा खबरें देखने के लिए चैनल को सब्सक्राइब करें  --  {title[:80]}  ",
        font_size=24, color="#FFD700", method="label",
    )
    if font:
        ticker_kw["font"] = font
    ticker_txt = TextClip(**ticker_kw).with_duration(total_duration)
    tw, th = ticker_txt.size
    scroll_speed = 140  # px/sec
    loop_w = tw + W

    def ticker_pos(t):
        x = W - (t * scroll_speed) % loop_w
        y = ticker_y + (TICKER_H - th) // 2
        return (x, y)

    ticker_txt = ticker_txt.with_position(ticker_pos)
    layers.append(ticker_txt)

    # ── Bottom caption bar ───────────────────────────────────────────────
    bottom_bar = (
        ColorClip(size=(W - 2 * OB, BAR_H), color=(8, 8, 8))
        .with_opacity(0.9).with_duration(total_duration)
        .with_position((OB, H - BAR_H))
    )
    layers.append(bottom_bar)

    caption_clips = []
    t = 0.0
    for caption, dur in zip(captions, durations):
        cap_kw = dict(
            text=_wrap_caption(caption), font_size=29, color="white",
            method="caption", size=(W - 2 * OB - 40, BAR_H - 40),
        )
        if font:
            cap_kw["font"] = font
        tc = TextClip(**cap_kw).with_duration(dur + 0.4).with_position(
            (OB + 20, H - BAR_H + 18)
        ).with_start(t)
        caption_clips.append(tc)
        t += dur
    layers += caption_clips

    # ── Subscribe reminder (last 8s, above ticker) ───────────────────────
    sub_start = max(0, total_duration - 8)
    sub_kw = dict(
        text="Subscribe to REAL NEWS for daily updates!",
        font_size=24, color="#FFD700", method="label",
    )
    if font:
        sub_kw["font"] = font
    subscribe = TextClip(**sub_kw).with_duration(8).with_position(
        (0, ticker_y - 36)
    ).with_start(sub_start)
    layers.append(subscribe)

    final = CompositeVideoClip(layers, size=size).with_audio(audio)

    final.write_videofile(
        out_path, fps=24, codec="libx264",
        audio_codec="aac", preset="ultrafast",
        threads=4, logger="bar",
    )
    return out_path
