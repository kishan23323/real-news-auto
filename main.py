"""
Full pipeline: URL → extract → summarize → voice → images → video → thumbnail

Usage:
    python main.py "<url>" "<topic>" [minutes]

Example:
    python main.py "https://thehindu.com/..." "FIFA World Cup 2026" 6
"""
import sys
import os
from datetime import datetime

from extract_article import extract_article
from summarize_text import summarize, get_sentences
from fetch_images import get_images
from generate_voice import generate_voice_segments, combine_audio, detect_language
from build_video import build_video
from make_thumbnail import make_thumbnail

OUTPUT_DIR = "daily_videos"
AVG_SECONDS_PER_SENTENCE = 8


def run(url: str, topic: str = None, target_minutes: float = 6.0):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("1/6 Extracting article...")
    title, text = extract_article(url)
    topic_hint = topic or title
    print(f"  Title: {title}")

    print("2/6 Detecting language and summarizing...")
    lang = detect_language(text)
    print(f"  Language detected: {'Hindi' if lang == 'hi' else 'English'}")
    desired_sentences = max(8, int((target_minutes * 60) / AVG_SECONDS_PER_SENTENCE))
    summary = summarize(text, num_sentences=desired_sentences)
    sentences = get_sentences(summary)
    if not sentences:
        raise Exception("Could not summarize this article")
    print(f"  {len(sentences)} sentences")

    print("3/6 Generating voice (per sentence for exact sync)...")
    voice_paths, durations = generate_voice_segments(sentences, lang=lang)
    combined_audio = combine_audio(voice_paths, out_path="voice_combined.mp3")

    print(f"4/6 Fetching real article images + stock fill...")
    images = get_images(url, topic_hint, target=max(len(sentences), 20))
    if not images:
        raise Exception("No images found")
    print(f"  Total images: {len(images)}")

    # align captions + durations to available images
    n = min(len(images), len(sentences))
    images = images[:n]
    captions = sentences[:n]
    durations = durations[:n]

    print("5/6 Building video...")
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = "".join(c if c.isalnum() else "_" for c in title)[:40].strip("_")
    out_path = os.path.join(OUTPUT_DIR, f"video_{date_str}_{slug}.mp4")
    build_video(images, captions, durations, combined_audio, title, out_path=out_path)

    print("6/6 Creating thumbnail...")
    thumb_path = os.path.join(OUTPUT_DIR, f"thumb_{date_str}_{slug}.jpg")
    make_thumbnail(images[0], title, out_path=thumb_path)

    print(f"\nDone!")
    print(f"  Video:     {out_path}")
    print(f"  Thumbnail: {thumb_path}")
    return out_path, thumb_path, title, lang


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python main.py "<url>" "<topic>" [minutes]')
        sys.exit(1)
    url_arg = sys.argv[1]
    topic_arg = sys.argv[2] if len(sys.argv) > 2 else None
    minutes_arg = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
    run(url_arg, topic_arg, minutes_arg)
