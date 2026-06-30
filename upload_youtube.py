"""
Uploads a finished video to YouTube automatically -- no browser/login
needed at runtime, because it reuses the refresh token from
get_refresh_token.py (stored as GitHub Secrets in the cloud workflow).

Reads these from environment variables:
    YT_CLIENT_ID
    YT_CLIENT_SECRET
    YT_REFRESH_TOKEN
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


def upload_video(file_path: str, title: str, description: str = "",
                  tags=None, category_id: str = "25", privacy: str = "public"):
    """category_id 25 = News & Politics. privacy: 'public', 'unlisted', or 'private'."""
    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": tags or [],
            "categoryId": category_id,
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
    print(f"Done! https://www.youtube.com/watch?v={video_id}")
    return video_id


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print('Usage: python upload_youtube.py "<video_path>" "<title>" ["description"]')
        sys.exit(1)
    path = sys.argv[1]
    title = sys.argv[2]
    desc = sys.argv[3] if len(sys.argv) > 3 else ""
    upload_video(path, title, desc)
