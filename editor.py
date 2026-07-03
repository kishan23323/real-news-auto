"""
Video segment editor — cuts out a portion of a video,
regenerates it with fresh images/voice, and splices it back.
"""
import os, json, shutil
from moviepy import VideoFileClip, concatenate_videoclips
from main import run as full_run
from generate_voice import generate_voice_segments, combine_audio, detect_language
from fetch_images import get_images
from build_video import build_video
from summarize_text import get_sentences


def regenerate_segment(video_path: str, start: float, end: float,
                        topic: str, lang: str = "en") -> str:
    """
    Cut [start, end] out of video_path, rebuild just that segment
    with new images + voice, splice back in. Returns new video path.
    """
    clip      = VideoFileClip(video_path)
    total_dur = clip.duration
    segment_dur = end - start

    # keep parts before and after the selected segment
    before = clip.subclipped(0, start)          if start > 0.5        else None
    after  = clip.subclipped(end, total_dur)    if end < total_dur - 0.5 else None

    # generate new content for the segment duration
    # Use a short summary proportional to segment length (~1 sentence per 8s)
    n_sentences = max(2, int(segment_dur / 8))

    # re-use the topic to fetch fresh images
    seg_dir = "seg_images"
    shutil.rmtree(seg_dir, ignore_errors=True)
    images = get_images(None, topic, out_dir=seg_dir, target=n_sentences + 2)
    if not images:
        raise Exception("Could not fetch images for segment")

    # generate placeholder sentences proportional to segment length
    sentences = [f"{topic} — update {i+1}" for i in range(n_sentences)]
    voice_paths, durations = generate_voice_segments(
        sentences, out_dir="seg_voice", lang=lang
    )
    audio_path = combine_audio(voice_paths, out_path="seg_voice_combined.mp3")

    seg_out = "segment_temp.mp4"
    build_video(
        images[:n_sentences], sentences[:n_sentences],
        durations[:n_sentences], audio_path,
        title=topic, out_path=seg_out, lang=lang
    )

    # splice back together
    seg_clip  = VideoFileClip(seg_out)
    parts = [p for p in [before, seg_clip, after] if p is not None]
    final = concatenate_videoclips(parts)

    out_path = video_path.replace(".mp4", "_edited.mp4")
    final.write_videofile(out_path, fps=24, codec="libx264",
                           audio_codec="aac", preset="ultrafast",
                           threads=4, logger=None)
    clip.close()
    return out_path
