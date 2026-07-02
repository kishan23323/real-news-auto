"""
Upload video to YouTube as UNLISTED (so you can review before making public).
Includes SEO description, tags, and thumbnail.
"""
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def get_authenticated_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("youtube", "v3", credentials=creds)


def build_description(title, source_url, lang="en"):
    if lang == "hi":
        return f"""{title}

इस वीडियो में हम आपको इस विषय की पूरी जानकारी देते हैं।
Real News पर आपका स्वागत है — हर दिन ताज़ा खबरें, सटीक जानकारी।

📰 स्रोत: {source_url}

👉 चैनल को Subscribe करें: https://www.youtube.com/@RealNews-g3y
🔔 Bell Icon दबाएं ताकि कोई वीडियो न छूटे।

#RealNews #ताजाखबर #HindiNews #BreakingNews #NewsInHindi #आजकीखबर
"""
    else:
        return f"""{title}

Welcome to Real News — your daily source for accurate, fast news coverage.

📰 Source: {source_url}

👉 Subscribe: https://www.youtube.com/@RealNews-g3y
🔔 Hit the Bell Icon so you never miss an update.

#RealNews #BreakingNews #LatestNews #NewsUpdate #DailyNews
"""


def build_tags(title, topic, lang="en"):
    base = ["Real News", "Breaking News", "Latest News", "News Update", "Daily News"]
    if lang == "hi":
        base += ["Hindi News", "Aaj Ki Khabar", "Taza Khabar", "Hindi Breaking News",
                 "आज की खबर", "ताजा खबर"]
    topic_tags = [w.strip() for w in (topic or "").replace("|", " ").split() if len(w.strip()) > 2]
    title_tags = [w.strip(".,!?") for w in title.split() if len(w.strip()) > 3]
    all_tags = base + topic_tags + title_tags
    final, total = [], 0
    for tag in all_tags:
        if total + len(tag) + 1 < 490:
            final.append(tag)
            total += len(tag) + 1
    return final


def upload_video(file_path, title, source_url="", topic="", lang="en",
                  thumbnail_path=None, privacy="unlisted"):  # <-- UNLISTED by default
    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": title[:100],
            "description": build_description(title, source_url, lang),
            "tags": build_tags(title, topic, lang),
            "categoryId": "25",
        },
        "status": {"privacyStatus": privacy},
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print(f"Uploading as {privacy.upper()}...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"  Done: https://www.youtube.com/watch?v={video_id}")
    print(f"  Status: UNLISTED — go to YouTube Studio to make it public when ready.")

    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            print(f"  Thumbnail uploaded.")
        except Exception as e:
            print(f"  Thumbnail failed (need verified channel): {e}")

    return video_id


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print('Usage: python upload_youtube.py "<video>" "<title>"')
        sys.exit(1)
    upload_video(sys.argv[1], sys.argv[2])
