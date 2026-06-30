# Going Fully Automated (No PC Needed)

This makes your tool run on a schedule in the cloud (GitHub's free servers)
and auto-upload to your channel: http://www.youtube.com/@RealNews-g3y

## Part A — One-time YouTube API setup (do this locally, on your PC)

1. Go to https://console.cloud.google.com -> sign in with the Google
   account that owns your YouTube channel -> create a new project
   (any name, e.g. "real-news-bot").
2. In the search bar, search "YouTube Data API v3" -> open it -> click Enable.
3. Go to "APIs & Services" -> "OAuth consent screen". Choose "External",
   fill in app name (e.g. "Real News Bot"), your email, save. Add your own
   Google account email under "Test users".
4. Go to "APIs & Services" -> "Credentials" -> "Create Credentials" ->
   "OAuth client ID" -> Application type: **Desktop app** -> Create.
5. Download the JSON file. Rename it to `client_secret.json` and put it
   in your `auto-video-tool` folder.
6. Install one more package locally:
   ```
   pip install google-auth-oauthlib
   ```
7. Run:
   ```
   python get_refresh_token.py
   ```
   A browser opens -> log in -> allow access (you may see an "unverified app"
   warning since this is your own private app -- click Advanced -> Continue).
8. The terminal prints a **refresh token**, **client ID**, and **client secret**.
   Copy all three somewhere safe (e.g. a Notepad file, NOT into the repo).

## Part B — Push your project to GitHub

1. Create a free account at https://github.com if you don't have one.
2. Create a **new private repository** (e.g. `real-news-auto`).
3. Upload your whole `auto-video-tool` folder to it (GitHub's website
   has an "upload files" button, or use `git` if you're comfortable with it).
4. **IMPORTANT**: do NOT upload `client_secret.json` or any file containing
   your refresh token. Add a `.gitignore` file with this content to be safe:
   ```
   client_secret.json
   *.mp4
   *.mp3
   images/
   voice_segments/
   ```

## Part C — Add your secrets to GitHub

1. In your repo, go to Settings -> Secrets and variables -> Actions.
2. Click "New repository secret" and add each of these one at a time:
   - `PEXELS_API_KEY` -> your Pexels key
   - `YT_CLIENT_ID` -> from step A8
   - `YT_CLIENT_SECRET` -> from step A8
   - `YT_REFRESH_TOKEN` -> from step A8

## Part D — Set your daily article list

Edit `urls.txt` in your repo with the articles you want turned into videos
that day (one per line, `| topic` optional). You'll update this file daily
with fresh news links -- this is the one manual step left.

(Later upgrade: pull links automatically from an RSS feed instead of typing
them by hand -- ask me when you're ready for that.)

## Part E — Turn on the schedule

The workflow file `.github/workflows/daily.yml` is already set to run every
day at 9:00 AM UTC. To change the time, edit the `cron` line (format is
minute hour day month weekday, in UTC).

To test it immediately instead of waiting for tomorrow:
1. Go to your repo -> "Actions" tab -> "Daily News Video" workflow
2. Click "Run workflow" (this is the `workflow_dispatch` trigger)
3. Watch it run live -- it'll show each step (install, build, upload)
4. If it succeeds, check your YouTube channel for the new video

## Costs
Everything here is free: GitHub Actions gives ~2,000 free minutes/month
on private repos (a 6-min video build takes roughly 10-20 minutes of that),
Pexels API is free, edge-tts is free, YouTube API is free within quota.

## If something fails
Click into the failed Actions run -> it shows the exact error per step.
Paste that error to me and I'll fix the relevant file.
