# Update: template selection + one-file-per-template

I don't have push access to your GitHub repo, so here are the updated files
to drop into `real-news-auto`. I pulled your current `main` branch, made
the changes below, and test-rendered them end-to-end (ffmpeg + moviepy) to
confirm they work before handing them over.

## What was wrong

`build_video.py` already had a `TEMPLATES` registry (`landscape_16_9`,
`shorts_9_16`, `square_1_1`), but:
- All three templates lived in one 420-line file.
- `app.py` never asked which one to use — after image approval it went
  straight into `build_video(...)` with the hardcoded default
  `landscape_16_9`, and it always rendered just that one.

## What changed

**1. New `templates/` folder — one file per template**
```
templates/
  __init__.py        # registry + shared render/assembly logic
  common.py           # shared fonts, autofit text, Ken Burns, banners
  landscape_16_9.py   # 16:9 layout
  shorts_9_16.py      # 9:16 layout
  square_1_1.py       # 1:1 (reuses the 9:16 stacked layout, own size)
```
Adding a new format later = add one file here + register it in
`templates/__init__.py`. Nothing else needs to change.

**2. `build_video.py`** is now a thin wrapper around `templates/`. It
accepts a `templates=[...]` list and builds each selected one, e.g.:
```python
build_video(images, captions, durations, audio_path, title,
            out_path="video.mp4", templates=["landscape_16_9", "square_1_1"])
```
Passing multiple templates writes one file per template
(`video_landscape_16_9.mp4`, `video_square_1_1.mp4`, ...).

**3. `app.py`** — added a new pipeline stage between image approval and
video build:
- After you approve images, a **"Choose Template(s)"** panel now appears
  with a checkbox per template (label + resolution), instead of jumping
  straight to frame building.
- New route `/approve_templates/<job_id>` receives your selection.
- The pipeline then builds **only** the template(s) you checked. If you
  pick more than one, the first opens automatically in the editor and the
  rest are saved alongside it (they show up in the Library tab too).

## How to apply

From your repo root:
```bash
git checkout main
git pull

# copy these files in, overwriting the old ones
cp path/to/app.py .
cp path/to/build_video.py .
cp -r path/to/templates .

git add app.py build_video.py templates/
git commit -m "Add template selection step; split templates into their own files"
git push
```

If you'd rather I open the PR myself, share a token/collaborator access
and I'll push a branch directly.
