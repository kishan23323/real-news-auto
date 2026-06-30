"""
Step 1: Pull clean article text + title out of any news/blog URL.
Uses trafilatura, which is much better than raw BeautifulSoup at
ignoring ads, menus, and junk and just returning the article body.
"""
import trafilatura


def extract_article(url: str):
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise Exception(f"Could not download page: {url}")

    text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    if not text:
        raise Exception("Could not find article text on this page")

    metadata = trafilatura.extract_metadata(downloaded)
    title = metadata.title if metadata and metadata.title else "Untitled Article"

    return title, text


if __name__ == "__main__":
    # quick manual test
    title, text = extract_article("https://example.com")
    print("TITLE:", title)
    print("TEXT:", text[:500])
