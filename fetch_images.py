"""
Step 3: Get images for the video.

Priority order:
1. Real images scraped directly from the article URL (most relevant)
2. Pexels stock images as fallback (if article has no usable images)

This means FIFA World Cup articles get actual FIFA images, not generic
stock photos of footballers.
"""
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "YOUR_PEXELS_API_KEY")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _download_image(url: str, path: str) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            with open(path, "wb") as f:
                f.write(r.content)
            return os.path.getsize(path) > 10000  # skip tiny/broken images
    except Exception:
        pass
    return False


def scrape_article_images(url: str, out_dir: str = "images", max_images: int = 15) -> list:
    """
    Pull real images from the article page itself.
    Looks for og:image, article images, and large inline images.
    """
    os.makedirs(out_dir, exist_ok=True)
    paths = []

    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")

        candidates = []

        # 1. og:image (usually the main article image / thumbnail)
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            candidates.append(og["content"])

        # 2. twitter:image
        tw = soup.find("meta", attrs={"name": "twitter:image"})
        if tw and tw.get("content"):
            candidates.append(tw["content"])

        # 3. All <img> tags inside article/main content
        for tag in ["article", "main", "div"]:
            container = soup.find(tag)
            if container:
                for img in container.find_all("img", src=True):
                    src = img["src"]
                    if not src.startswith("data:") and len(src) > 10:
                        candidates.append(urljoin(url, src))

        # deduplicate while preserving order
        seen = set()
        unique = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique.append(c)

        for i, img_url in enumerate(unique[:max_images]):
            path = os.path.join(out_dir, f"article_{i}.jpg")
            if _download_image(img_url, path):
                paths.append(path)

    except Exception as e:
        print(f"  (article image scrape failed: {e})")

    return paths


def fetch_pexels_images(query: str, count: int = 8, out_dir: str = "images") -> list:
    os.makedirs(out_dir, exist_ok=True)
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/v1/search?query={query}&per_page={count}&orientation=landscape"
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        paths = []
        for i, photo in enumerate(resp.json().get("photos", [])):
            img_url = photo["src"]["large"]
            path = os.path.join(out_dir, f"pexels_{i}.jpg")
            if _download_image(img_url, path):
                paths.append(path)
        return paths
    except Exception as e:
        print(f"  (Pexels fetch failed: {e})")
        return []


def get_images(article_url: str, topic: str, out_dir: str = "images", target: int = 20) -> list:
    """
    Main function: tries article images first, fills with Pexels if needed.
    """
    os.makedirs(out_dir, exist_ok=True)

    print("  Scraping article images...")
    paths = scrape_article_images(article_url, out_dir=out_dir, max_images=target)
    print(f"  Got {len(paths)} real article images")

    if len(paths) < target:
        needed = target - len(paths)
        print(f"  Fetching {needed} Pexels images to fill gaps...")
        pexels = fetch_pexels_images(topic, count=needed, out_dir=out_dir)
        paths.extend(pexels)

    return paths
