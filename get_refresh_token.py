"""
RUN THIS ONCE, ON YOUR OWN COMPUTER ONLY (not in the cloud).

It opens a browser, asks you to log into the Google account that owns
your "Real News" YouTube channel, and grants upload permission. It then
prints a REFRESH TOKEN -- a long string that lets the automated cloud
script upload videos forever without you logging in again.

Setup before running:
1. Go to https://console.cloud.google.com -> create a free project
2. Search "YouTube Data API v3" -> click Enable
3. Go to "APIs & Services" -> "Credentials" -> "Create Credentials" ->
   "OAuth client ID" -> Application type: Desktop app
4. Download the JSON file, rename it to client_secret.json, and put it
   in this same folder.

Run:
    python get_refresh_token.py

Copy the printed refresh token -- you'll paste it into a GitHub Secret
later (see SETUP_CLOUD.md). Never commit client_secret.json or the
refresh token to GitHub.
"""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
    creds = flow.run_local_server(port=0)
    print("\n\n=== COPY THIS REFRESH TOKEN ===")
    print(creds.refresh_token)
    print("================================")
    print("\nAlso save these (needed by the upload script):")
    print("CLIENT_ID:", creds.client_id)
    print("CLIENT_SECRET:", creds.client_secret)


if __name__ == "__main__":
    main()
