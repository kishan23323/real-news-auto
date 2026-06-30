# Auto Video Tool — URL to Slideshow Video

Turns any article URL into a narrated slideshow video, 100% free, no API costs.

## What it does
1. Extracts article text from your link
2. Summarizes it to a short, spoken-friendly script
3. Pulls matching royalty-free images from Pexels
4. Generates a free AI voiceover (edge-tts)
5. Builds an MP4 slideshow with crossfades + title card
6. Saves it to `daily_videos/`

## One-time setup

1. Install Python 3.9+ if you don't have it.
2. Install ffmpeg (required by moviepy):
   - Windows: `winget install ffmpeg` or download from ffmpeg.org and add to PATH
   - Mac: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg`
3. Install Python packages:
   ```
   pip install -r requirements.txt
   ```
4. Get a free Pexels API key: https://www.pexels.com/api/ (instant, no card needed)
5. Set it as an environment variable:
   - Windows (PowerShell): `setx PEXELS_API_KEY "your_key_here"`
   - Mac/Linux: add `export PEXELS_API_KEY="your_key_here"` to your `.bashrc`/`.zshrc`

## Run it

```
python main.py "https://example.com/some-article" "optional image search term"
```

The image search term is optional — if you skip it, the tool uses the article title.

## Automate it daily

**Windows**: Task Scheduler → Create Basic Task → Trigger: Daily → Action: Start a program →
`python` with arguments `main.py "<url>"`, set "Start in" to this folder.

**Mac/Linux**: add a cron job:
```
crontab -e
# run every day at 9am
0 9 * * * cd /path/to/auto-video-tool && /usr/bin/python3 main.py "https://your-source-url.com" >> log.txt 2>&1
```

Since the URL changes daily, you'll likely want a small list of URLs to rotate through
(e.g. a `urls.txt` file you update each morning, or pull from an RSS feed) rather than
one hardcoded link — happy to build that next if useful.

## Before publishing to YouTube
- Don't reuse the source site's own images/text verbatim — this tool already swaps in
  Pexels stock images and summarizes (rather than copies) the text for that reason.
- Add your own short intro/outro and channel branding so it reads as original content.
- Consider crediting the source in the video description as good practice.

## Next step: auto-upload to YouTube
This requires a one-time Google Cloud OAuth setup (free, ~15 min) so the script can call
the YouTube Data API. Ask and I'll walk you through that setup plus the upload script.
