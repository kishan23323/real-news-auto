"""
Step 3: Get royalty-free images relevant to the topic.

Instead of one generic search term for the whole video, this now takes
a LIST of queries (one per segment of the script) so each image actually
matches what's being said at that moment -- much more relevant for
news-style content (e.g. "FIFA World Cup 2026 stadium", "football fans
celebrating", "soccer player kicking ball" instead of one repeated image).

Get a FREE API key at: https://www.pexels.com/api/  (no credit card)
Then set it as an environment variable: PEXELS_API_KEY
"""
import os
import requests

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "YOUR_PEXELS_API_KEY")


def _search_one(query: str, out_path: str) -> bool:
    """Fetch a single best-matching image for one query. Returns True on success."""
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/v1/search?query={query}&per_page=1&orientation=landscape"
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    photos = resp.json().get("photos", [])
    if not photos:
        return False
    img_url = photos[0]["src"]["large"]
    img_bytes = requests.get(img_url, timeout=20).content
    with open(out_path, "wb") as f:
        f.write(img_bytes)
    return True


def fetch_images_for_queries(queries, out_dir: str = "images", fallback_query: str = "news"):
    """
    queries: list of search phrases, one per image/segment you want.
    Returns a list of file paths, same length as queries (skips ones that fail).
    """
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for i, q in enumerate(queries):
        out_path = os.path.join(out_dir, f"image_{i}.jpg")
        try:
            ok = _search_one(q, out_path)
            if not ok:
                ok = _search_one(fallback_query, out_path)
            if ok:
                paths.append(out_path)
        except Exception as e:
            print(f"  (image fetch failed for '{q}': {e})")
    return paths


# Backwards-compatible simple version (single topic, N images)
def fetch_images(query: str, count: int = 5, out_dir: str = "images"):
    os.makedirs(out_dir, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/v1/search?query={query}&per_page={count}&orientation=landscape"
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    paths = []
    for i, photo in enumerate(data.get("photos", [])):
        img_url = photo["src"]["large"]
        img_bytes = requests.get(img_url, timeout=20).content
        path = os.path.join(out_dir, f"image_{i}.jpg")
        with open(path, "wb") as f:
            f.write(img_bytes)
        paths.append(path)
    return paths
