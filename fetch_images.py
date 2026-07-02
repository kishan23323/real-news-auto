"""
Image fetcher — priority order:
1. YOUR OWN images from my_images/ folder (put your photos/memes here)
2. Real article images scraped from the URL
3. Pexels stock photos as fallback
"""
import os, random, shutil, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "YOUR_PEXELS_API_KEY")
MY_IMAGES_DIR  = "my_images"   # put your own photos/memes here

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    )
}


def _is_valid_image(path):
    try:
        from PIL import Image
        Image.open(path).verify()
        return os.path.getsize(path) > 8000
    except Exception:
        return False


def _download(url, path):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type",""):
            with open(path,"wb") as f: f.write(r.content)
            return _is_valid_image(path)
    except Exception:
        pass
    return False


def get_my_images(out_dir, target):
    """Copy user's own images from my_images/ folder."""
    paths = []
    if not os.path.exists(MY_IMAGES_DIR):
        os.makedirs(MY_IMAGES_DIR)
        return paths
    files = [
        f for f in os.listdir(MY_IMAGES_DIR)
        if f.lower().endswith((".jpg",".jpeg",".png",".webp"))
    ]
    random.shuffle(files)
    for i, f in enumerate(files[:target]):
        dst = os.path.join(out_dir, f"myimg_{i}.jpg")
        try:
            from PIL import Image
            Image.open(os.path.join(MY_IMAGES_DIR, f)).convert("RGB").save(dst, "JPEG")
            if _is_valid_image(dst):
                paths.append(dst)
        except Exception:
            pass
    return paths


def scrape_article_images(url, out_dir, max_images=15):
    paths = []
    try:
        r    = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        candidates = []
        for meta_prop in ["og:image", "twitter:image"]:
            tag = soup.find("meta", property=meta_prop) or soup.find("meta", attrs={"name": meta_prop})
            if tag and tag.get("content"):
                candidates.append(tag["content"])
        for container_tag in ["article","main","div"]:
            container = soup.find(container_tag)
            if container:
                for img in container.find_all("img", src=True):
                    src = img["src"]
                    if not src.startswith("data:") and len(src) > 10:
                        candidates.append(urljoin(url, src))
        seen = set()
        for i, img_url in enumerate([c for c in candidates if c not in seen and not seen.add(c)][:max_images]):
            path = os.path.join(out_dir, f"article_{i}.jpg")
            if _download(img_url, path):
                paths.append(path)
    except Exception as e:
        print(f"  (article scrape: {e})")
    return paths


def fetch_pexels(query, count, out_dir):
    paths = []
    try:
        r = requests.get(
            f"https://api.pexels.com/v1/search?query={query}&per_page={count}&orientation=landscape",
            headers={"Authorization": PEXELS_API_KEY}, timeout=20
        )
        r.raise_for_status()
        for i, photo in enumerate(r.json().get("photos",[])):
            path = os.path.join(out_dir, f"pexels_{i}.jpg")
            if _download(photo["src"]["large"], path):
                paths.append(path)
    except Exception as e:
        print(f"  (Pexels: {e})")
    return paths


def get_images(article_url, topic, out_dir="images", target=20):
    os.makedirs(out_dir, exist_ok=True)

    print("  Loading your own images from my_images/...")
    mine = get_my_images(out_dir, target // 3)
    print(f"  Your images: {len(mine)}")

    print("  Scraping article images...")
    article = scrape_article_images(article_url, out_dir, max_images=target)
    print(f"  Article images: {len(article)}")

    combined = mine + article
    if len(combined) < target:
        needed = target - len(combined)
        print(f"  Fetching {needed} Pexels images...")
        combined += fetch_pexels(topic, needed, out_dir)

    print(f"  Total images: {len(combined)}")
    return combined
