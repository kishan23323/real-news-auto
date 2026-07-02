"""
Attractive news-style video builder with:
- Hindi/Devanagari font support (Noto Sans)
- Breaking news red banner at top
- Smooth image transitions
- Professional lower-third captions
- Channel branding
"""
import platform
import os
from moviepy import (
    ImageClip,
    AudioFileClip,
    ColorClip,
    TextClip,
    CompositeVideoClip,
    vfx,
)

CHANNEL_NAME = "REAL NEWS"


def _find_font(bold=True, lang="en"):
    """Find best font supporting Hindi or English."""
    if platform.system() == "Windows":
        candidates = [
            # Noto Sans for Hindi (user must install from fonts.google.com/noto)
            "C:/Windows/Fonts/NotoSansDevanagari-Bold.ttf",
            "C:/Windows/Fonts/NotoSansDevanagari-Regular.ttf",
            "C:/Windows/Fonts/mangal.ttf",   # built-in Windows Hindi font
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
    elif platform.system() == "Darwin":
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    else:
        # Linux / GitHub Actions — Noto fonts installed via apt
        candidates = [
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Bold.otf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
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


def build_video(image_paths, captions, durations, audio_path, title,
                out_path="output.mp4", size=(1280, 720), lang="en"):
    W, H = size
    font = _find_font(lang=lang)
    audio = AudioFileClip(audio_path)
    total_duration = audio.duration

    BAR_H = 170          # caption bar height
    TOP_BAR_H = 70       # breaking news top bar

    # ── Image track ──────────────────────────────────────────────────────
    image_clips = []
    t = 0.0
    for img, dur in zip(image_paths, durations):
        clip = (
            ImageClip(img)
            .resized(height=H)
            .with_position("center")
            .with_start(t)
            .with_duration(dur + 0.5)
            .with_effects([vfx.CrossFadeIn(0.4)])
        )
        image_clips.append(clip)
        t += dur

    # ── Dark gradient overlay on bottom (always visible) ─────────────────
    bottom_bar = (
        ColorClip(size=(W, BAR_H), color=(8, 8, 8))
        .with_opacity(0.82)
        .with_duration(total_duration)
        .with_position(("center", H - BAR_H))
    )

    # ── Red "BREAKING NEWS" top banner ───────────────────────────────────
    top_bar = (
        ColorClip(size=(W, TOP_BAR_H), color=(200, 20, 20))
        .with_opacity(0.92)
        .with_duration(total_duration)
        .with_position(("center", 0))
    )

    # Breaking news label
    breaking_kwargs = dict(text="⚡ BREAKING NEWS", font_size=30, color="white", method="label")
    if font:
        breaking_kwargs["font"] = font
    breaking_label = (
        TextClip(**breaking_kwargs)
        .with_duration(total_duration)
        .with_position((30, 15))
    )

    # Channel name badge right side of top bar
    channel_kwargs = dict(text=f"🔴 {CHANNEL_NAME}", font_size=28, color="white", method="label")
    if font:
        channel_kwargs["font"] = font
    channel_badge = (
        TextClip(**channel_kwargs)
        .with_duration(total_duration)
        .with_position((W - 280, 18))
    )

    # ── Title card (first 6 seconds) ─────────────────────────────────────
    title_bg = (
        ColorClip(size=(W, 90), color=(0, 0, 0))
        .with_opacity(0.75)
        .with_duration(min(6, total_duration))
        .with_position(("center", TOP_BAR_H + 10))
    )
    title_kwargs = dict(
        text=title[:120],
        font_size=38,
        color="#FFD700",   # gold
        size=(W - 60, 85),
        method="caption",
    )
    if font:
        title_kwargs["font"] = font
    title_clip = (
        TextClip(**title_kwargs)
        .with_duration(min(6, total_duration))
        .with_position(("center", TOP_BAR_H + 15))
    )

    # ── Per-segment captions ─────────────────────────────────────────────
    caption_clips = []
    t = 0.0
    for caption, dur in zip(captions, durations):
        safe = _wrap_caption(caption)
        cap_kwargs = dict(
            text=safe,
            font_size=30,
            color="white",
            size=(W - 80, BAR_H - 50),
            method="caption",
        )
        if font:
            cap_kwargs["font"] = font
        tc = (
            TextClip(**cap_kwargs)
            .with_start(t)
            .with_duration(dur + 0.4)
            .with_position((40, H - BAR_H + 20))
        )
        caption_clips.append(tc)
        t += dur

    # ── Subscribe reminder (last 8 seconds) ──────────────────────────────
    sub_kwargs = dict(
        text="👉 Subscribe to REAL NEWS for daily updates!",
        font_size=26,
        color="#FFD700",
        method="label",
    )
    if font:
        sub_kwargs["font"] = font
    sub_start = max(0, total_duration - 8)
    subscribe_clip = (
        TextClip(**sub_kwargs)
        .with_start(sub_start)
        .with_duration(8)
        .with_position(("center", H - BAR_H - 50))
    )

    # ── Compose everything ───────────────────────────────────────────────
    final = CompositeVideoClip(
        [*image_clips, bottom_bar, top_bar, breaking_label,
         channel_badge, title_bg, title_clip,
         *caption_clips, subscribe_clip],
        size=size
    ).with_audio(audio)

    final.write_videofile(
        out_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=4,
        logger="bar",
    )
    return out_path
