"""
templates package
──────────────────
Every video format lives in its own file in this folder:

    landscape_16_9.py   → YouTube / TV (16:9)
    shorts_9_16.py      → Shorts / Reels / Status (9:16)
    square_1_1.py       → Feed post (1:1)

Add a new format by adding a new file here that defines KEY, LABEL,
SIZE, and a build_body(...) function, then registering it in
_TEMPLATE_MODULES below. Nothing else needs to change — app.py and
build_video.py both read the registry dynamically.
"""
from moviepy import AudioFileClip, CompositeVideoClip

from . import common
from . import landscape_16_9
from . import shorts_9_16
from . import square_1_1

_TEMPLATE_MODULES = [landscape_16_9, shorts_9_16, square_1_1]

# key -> {"label": ..., "size": (W, H), "module": module}
TEMPLATES = {
    mod.KEY: {"label": mod.LABEL, "size": mod.SIZE, "module": mod}
    for mod in _TEMPLATE_MODULES
}


def list_templates():
    """Return [{key, label, size}] for the UI's template picker, in a stable order."""
    return [
        {"key": key, "label": info["label"], "size": info["size"]}
        for key, info in TEMPLATES.items()
    ]


def render(template_key, image_paths, captions, durations, audio_path,
           out_path, lang="hi", style=None):
    """Build a single video for one template and write it to out_path.
    `style` (see common.DEFAULT_STYLE) overrides colors, logo position,
    corner radius, and font sizes."""
    if template_key not in TEMPLATES:
        raise ValueError(f"Unknown template '{template_key}'. Choose from: {list(TEMPLATES.keys())}")

    info = TEMPLATES[template_key]
    W, H = info["size"]
    build_body = info["module"].build_body

    font = common.find_font()
    impact_font = common.find_impact_font()
    audio = AudioFileClip(audio_path)
    total_duration = audio.duration

    TOP_H    = round(H * 0.10)
    BOTTOM_H = round(H * 0.10)
    MID_H    = H - TOP_H - BOTTOM_H

    layers = common.build_banners(W, H, TOP_H, BOTTOM_H, total_duration, font, style=style)
    layers += build_body(
        W, MID_H, TOP_H, image_paths, captions, durations,
        total_duration, font, impact_font, style=style,
    )

    final = CompositeVideoClip(layers, size=(W, H)).with_audio(audio)
    final.write_videofile(
        out_path, fps=24, codec="libx264",
        audio_codec="aac", preset="ultrafast",
        threads=4, logger="bar",
    )
    return out_path


def default_style():
    """The style defaults, for the frontend to pre-fill its controls."""
    return dict(common.DEFAULT_STYLE)
