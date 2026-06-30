"""
Step 5: Combine images + voiceover into a finished MP4, with a
"Real News"-style intro card and synced lower-third captions.

PERFORMANCE NOTE: this builds ONE single composite (all images and
captions placed at their exact start times) instead of a separate
composite per segment -- this is the main reason older versions took
2+ hours; this version should be dramatically faster.
"""
import platform
import os
from moviepy import (
    ImageClip,
    AudioFileClip,
    ColorClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
    vfx,
)

CHANNEL_NAME = "REAL NEWS"


def _find_font(bold=True):
    candidates = []
    if platform.system() == "Windows":
        candidates = ["C:/Windows/Fonts/arialbd.ttf"] if bold else ["C:/Windows/Fonts/arial.ttf"]
        candidates.append("C:/Windows/Fonts/arial.ttf")
    elif platform.system() == "Darwin":
        candidates = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                      "/System/Library/Fonts/Supplemental/Arial.ttf"]
    else:
        candidates = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _wrap_caption(text: str, max_words_per_line_group: int = 18) -> str:
    """Trim overly long sentences so they never overflow the caption box."""
    words = text.split()
    if len(words) > max_words_per_line_group:
        words = words[:max_words_per_line_group]
        text = " ".join(words) + "..."
    return text


def build_video(image_paths, captions, durations, audio_path, title,
                 out_path="output.mp4", size=(1280, 720)):
    """
    image_paths, captions, durations: parallel lists, one entry per segment.
    durations come from the ACTUAL spoken audio length of each caption,
    so video and voice stay in sync throughout.
    """
    font_bold = _find_font(bold=True)
    font_reg = _find_font(bold=False)
    W, H = size
    bar_height = 160

    audio = AudioFileClip(audio_path)
    total_duration = audio.duration

    # --- Build image track (each image placed at its exact start time) ---
    image_clips = []
    t = 0.0
    for img, dur in zip(image_paths, durations):
        clip = (
            ImageClip(img)
            .resized(height=H)
            .with_position("center")
            .with_start(t)
            .with_duration(dur + 0.4)
            .with_effects([vfx.CrossFadeIn(0.4)])
        )
        image_clips.append(clip)
        t += dur

    # --- Persistent lower-third bar (one clip, not rebuilt per segment) ---
    bar = (
        ColorClip(size=(W, bar_height), color=(15, 15, 15))
        .with_opacity(0.75)
        .with_duration(total_duration)
        .with_position(("center", H - bar_height))
        .with_start(0)
    )

    # --- Caption text, one TextClip per segment, placed at exact time ---
    caption_clips = []
    t = 0.0
    for caption, dur in zip(captions, durations):
        safe_text = _wrap_caption(caption)
        kwargs = dict(
            text=safe_text,
            font_size=28,
            color="white",
            size=(W - 100, bar_height - 40),
            method="caption",
        )
        if font_reg:
            kwargs["font"] = font_reg
        tc = (
            TextClip(**kwargs)
            .with_start(t)
            .with_duration(dur + 0.4)
            .with_position(("center", H - bar_height + 20))
        )
        caption_clips.append(tc)
        t += dur

    # --- Channel name badge, always visible, bottom-left of the bar ---
    badge_kwargs = dict(text=CHANNEL_NAME, font_size=22, color="#ff3b3b", method="label")
    if font_bold:
        badge_kwargs["font"] = font_bold
    badge = (
        TextClip(**badge_kwargs)
        .with_duration(total_duration)
        .with_position((30, H - bar_height - 35))
        .with_start(0)
    )

    # --- Title card, first few seconds only ---
    title_kwargs = dict(text=title, font_size=42, color="white",
                         size=(W - 100, None), method="caption")
    if font_bold:
        title_kwargs["font"] = font_bold
    title_clip = (
        TextClip(**title_kwargs)
        .with_position(("center", 30))
        .with_duration(min(5, total_duration))
        .with_start(0)
    )

    final = CompositeVideoClip(
        [*image_clips, bar, *caption_clips, badge, title_clip], size=size
    ).with_audio(audio)

    final.write_videofile(
        out_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",   # much faster encode, slightly larger file
        threads=4,
        logger="bar",
    )
    return out_path
