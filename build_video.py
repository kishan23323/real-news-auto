"""
News-style video builder - NO EMOJIS in text clips (causes boxes).
Uses plain text alternatives that render correctly with any font.
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


def build_video(image_paths, captions, durations, audio_path, title,
                out_path="output.mp4", size=(1280, 720), lang="en"):
    W, H = size
    font = _find_font(lang=lang)
    audio = AudioFileClip(audio_path)
    total_duration = audio.duration

    BAR_H   = 160
    TOP_H   = 65

    # ── Images ───────────────────────────────────────────────────────────
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

    # ── Bottom caption bar ───────────────────────────────────────────────
    bottom_bar = (
        ColorClip(size=(W, BAR_H), color=(8, 8, 8))
        .with_opacity(0.85).with_duration(total_duration)
        .with_position(("center", H - BAR_H))
    )

    # ── Top red banner ───────────────────────────────────────────────────
    top_bar = (
        ColorClip(size=(W, TOP_H), color=(200, 20, 20))
        .with_opacity(0.93).with_duration(total_duration)
        .with_position(("center", 0))
    )

    # BREAKING NEWS label — NO emoji
    def make_text(txt, size, color, duration, pos, method="label", text_size=None):
        kw = dict(text=txt, font_size=size, color=color, method=method)
        if text_size:
            kw["size"] = text_size
        if font:
            kw["font"] = font
        return TextClip(**kw).with_duration(duration).with_position(pos)

    breaking = make_text("** BREAKING NEWS **", 28, "white", total_duration, (30, 18))
    channel  = make_text(f"[ {CHANNEL_NAME} ]", 26, "white", total_duration, (W - 260, 20))

    # ── Gold title card (first 6s) ───────────────────────────────────────
    title_bg = (
        ColorClip(size=(W, 85), color=(0, 0, 0))
        .with_opacity(0.78).with_duration(min(6, total_duration))
        .with_position(("center", TOP_H + 8))
    )
    title_clip = make_text(
        title[:120], 36, "#FFD700", min(6, total_duration),
        ("center", TOP_H + 12), method="caption", text_size=(W - 60, 80)
    )

    # ── Captions per sentence ────────────────────────────────────────────
    caption_clips = []
    t = 0.0
    for caption, dur in zip(captions, durations):
        tc = make_text(
            _wrap_caption(caption), 29, "white", dur + 0.4,
            (40, H - BAR_H + 18), method="caption", text_size=(W - 80, BAR_H - 40)
        )
        caption_clips.append(tc.with_start(t))
        t += dur

    # ── Subscribe reminder (last 8s) ─────────────────────────────────────
    sub_start = max(0, total_duration - 8)
    subscribe = make_text(
        "Subscribe to REAL NEWS for daily updates!",
        24, "#FFD700", 8, ("center", H - BAR_H - 48)
    ).with_start(sub_start)

    # ── Red accent line above caption bar ────────────────────────────────
    accent = (
        ColorClip(size=(W, 5), color=(200, 20, 20))
        .with_opacity(1.0).with_duration(total_duration)
        .with_position(("center", H - BAR_H - 5))
    )

    final = CompositeVideoClip(
        [*image_clips, bottom_bar, accent, top_bar,
         breaking, channel, title_bg, title_clip,
         *caption_clips, subscribe],
        size=size
    ).with_audio(audio)

    final.write_videofile(
        out_path, fps=24, codec="libx264",
        audio_codec="aac", preset="ultrafast",
        threads=4, logger="bar",
    )
    return out_path
