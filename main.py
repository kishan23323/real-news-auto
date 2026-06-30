"""
The full pipeline, run from the command line:

    python main.py "https://example.com/article" "optional image topic" [minutes]

Example for a 6-minute video:
    python main.py "https://example.com/article" "FIFA World Cup" 6

Produces: daily_videos/video_YYYY-MM-DD_<title>.mp4
"""
import sys
import os
from datetime import datetime

from extract_article import extract_article
from summarize_text import summarize, get_sentences
from fetch_images import fetch_images_for_queries
from generate_voice import generate_voice_segments, combine_audio
from build_video import build_video

OUTPUT_DIR = "daily_videos"
AVG_SECONDS_PER_SENTENCE = 8  # rough estimate, used only to size the summary


def build_segment_queries(sentences, topic_hint):
    queries = []
    for s in sentences:
        short = " ".join(s.split()[:6])
        queries.append(f"{topic_hint} {short}".strip())
    return queries


def run(url: str, image_query: str = None, target_minutes: float = 6.0):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("1/5 Extracting article...")
    title, text = extract_article(url)
    topic_hint = image_query or title

    print("2/5 Summarizing...")
    target_seconds = target_minutes * 60
    desired_sentences = max(8, int(target_seconds / AVG_SECONDS_PER_SENTENCE))
    summary = summarize(text, num_sentences=desired_sentences)
    sentences = get_sentences(summary)
    if not sentences:
        raise Exception("Could not produce a summary from this article")

    print(f"3/5 Generating voice for {len(sentences)} sentences (exact timing)...")
    voice_paths, durations = generate_voice_segments(sentences)
    combined_audio = combine_audio(voice_paths, out_path="voice_combined.mp3")

    print(f"4/5 Fetching {len(sentences)} relevant images...")
    queries = build_segment_queries(sentences, topic_hint)
    images = fetch_images_for_queries(queries, fallback_query=topic_hint)
    if not images:
        raise Exception("No images found -- try a different topic/search term")

    # keep captions/durations aligned 1-to-1 with however many images we got
    captions = sentences[: len(images)]
    durations = durations[: len(images)]

    print("5/5 Building video...")
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = "".join(c if c.isalnum() else "_" for c in title)[:40].strip("_")
    out_path = os.path.join(OUTPUT_DIR, f"video_{date_str}_{slug}.mp4")
    build_video(images, captions, durations, combined_audio, title, out_path=out_path)

    print(f"\nDone! Saved to: {out_path}")
    return out_path, title


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python main.py "<article_url>" ["image topic"] [minutes]')
        sys.exit(1)

    url_arg = sys.argv[1]
    query_arg = sys.argv[2] if len(sys.argv) > 2 else None
    minutes_arg = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
    run(url_arg, query_arg, minutes_arg)
