"""
Uploads video to YouTube with:
- SEO-optimized title and description
- Auto-generated tags from topic keywords
- Custom thumbnail upload
- Category: News & Politics
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


def build_description(title: str, source_url: str, lang: str = "en") -> str:
    if lang == "hi":
        return f"""{title}

इस वीडियो में हम आपको इस विषय की पूरी जानकारी देते हैं।
Real News पर आपका स्वागत है — हर दिन ताज़ा खबरें, सटीक जानकारी।

📰 स्रोत: {source_url}

👉 चैनल को Subscribe करें: https://www.youtube.com/@RealNews-g3y
🔔 Bell Icon दबाएं ताकि कोई वीडियो न छूटे।

#RealNews #ताजाखबर #HindiNews #BreakingNews #NewsInHindi
"""
    else:
        return f"""{title}

Welcome to Real News — your daily source for accurate, fast news coverage.

📰 Source: {source_url}

👉 Subscribe to our channel: https://www.youtube.com/@RealNews-g3y
🔔 Hit the Bell Icon so you never miss an update.

#RealNews #BreakingNews #LatestNews #NewsUpdate #DailyNews
"""


def build_tags(title: str, topic: str, lang: str = "en") -> list:
    base_tags = ["Real News", "Breaking News", "Latest News", "News Update", "Daily News"]
    if lang == "hi":
        base_tags += ["Hindi News", "Aaj Ki Khabar", "Taza Khabar", "Hindi Breaking News"]

    # extract topic keywords as individual tags
    topic_tags = [w.strip() for w in topic.replace("|", " ").split() if len(w.strip()) > 2]

    # extract title words as tags
    title_tags = [w.strip(".,!?") for w in title.split() if len(w.strip()) > 3]

    all_tags = base_tags + topic_tags + title_tags
    # YouTube allows max 500 chars total for tags
    final, total = [], 0
    for tag in all_tags:
        if total + len(tag) + 1 < 490:
            final.append(tag)
            total += len(tag) + 1
    return final


def upload_video(file_path: str, title: str, source_url: str = "",
                  topic: str = "", lang: str = "en",
                  thumbnail_path: str = None,
                  privacy: str = "public") -> str:
    youtube = get_authenticated_service()

    description = build_description(title, source_url, lang)
    tags = build_tags(title, topic, lang)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": "25",  # News & Politics
        },
        "status": {"privacyStatus": privacy},
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print(f"Uploading {file_path} ...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  upload progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"  Uploaded: https://www.youtube.com/watch?v={video_id}")

    # Upload custom thumbnail
    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            print(f"  Thumbnail uploaded.")
        except Exception as e:
            print(f"  Thumbnail upload failed (may need channel verification): {e}")

    return video_id
