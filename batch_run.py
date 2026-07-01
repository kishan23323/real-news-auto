"""
Process a list of article URLs from urls.txt and auto-upload to YouTube.

File format:
    URL | topic | minutes
    minutes is optional, defaults to 6

Run:
    python batch_run.py urls.txt
"""
import sys
import os
from main import run

UPLOAD_TO_YOUTUBE = all(
    os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")
)


def parse_line(line: str):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = [p.strip() for p in line.split("|")]
    url = parts[0]
    topic = parts[1] if len(parts) > 1 else None
    try:
        minutes = float(parts[2]) if len(parts) > 2 else 6.0
    except ValueError:
        minutes = 6.0
    return url, topic, minutes


def batch_run(txt_path: str):
    if not os.path.exists(txt_path):
        print(f"File not found: {txt_path}")
        sys.exit(1)

    with open(txt_path, "r", encoding="utf-8") as f:
        entries = [parse_line(l) for l in f.readlines()]
    entries = [e for e in entries if e]

    if not entries:
        print("No valid URLs found.")
        return

    print(f"Found {len(entries)} URL(s).")
    if UPLOAD_TO_YOUTUBE:
        print("YouTube credentials found — will auto-upload.")
    print()

    results = []
    for i, (url, topic, minutes) in enumerate(entries, start=1):
        print(f"--- [{i}/{len(entries)}] {url} (target: {minutes} min) ---")
        try:
            out_path, thumb_path, title, lang = run(url, topic, minutes)
            status = "BUILT"
            if UPLOAD_TO_YOUTUBE:
                from upload_youtube import upload_video
                upload_video(
                    out_path,
                    title=title,
                    source_url=url,
                    topic=topic or "",
                    lang=lang,
                    thumbnail_path=thumb_path,
                )
                status = "UPLOADED"
            results.append((url, out_path, status))
        except Exception as e:
            print(f"  FAILED: {e}")
            results.append((url, None, f"FAILED: {e}"))
        print()

    print("=== Summary ===")
    for url, out_path, status in results:
        print(f"{status:10s}  {url}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python batch_run.py urls.txt")
        sys.exit(1)
    batch_run(sys.argv[1])
