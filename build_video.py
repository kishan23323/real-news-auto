"""
Professional news TV graphic — multiple aspect-ratio templates.

The actual per-format layouts now live under templates/ (one file per
template — see templates/__init__.py). This module just wires the
pipeline's inputs to the templates package and can build one or several
selected templates in a single call.

No emojis in TextClip strings — most fonts render them as boxes.
"""
import os
import templates as _templates


def build_video(image_paths, captions, durations, audio_path, title,
                 out_path="output.mp4", template="landscape_16_9",
                 templates=None, lang="hi", tmp_dir="/tmp"):
    """
    Build the news video for one or more templates.

    template:  single template key (back-compat, used when `templates` is None)
    templates: list of template keys to build, e.g. ["landscape_16_9", "shorts_9_16"]
               If given, `out_path` is treated as a base name and a
               template-suffixed file is written for each one.

    Returns:
        str        — the output path, if a single template was built
        dict       — {template_key: out_path}, if multiple templates were built
    """
    selected = templates if templates else [template]
    unknown = [t for t in selected if t not in _templates.TEMPLATES]
    if unknown:
        raise ValueError(
            f"Unknown template(s) {unknown}. Choose from: {list(_templates.TEMPLATES.keys())}"
        )

    if len(selected) == 1:
        _templates.render(selected[0], image_paths, captions, durations,
                           audio_path, out_path, lang=lang)
        return out_path

    base, ext = os.path.splitext(out_path)
    results = {}
    for key in selected:
        this_out = f"{base}_{key}{ext}"
        _templates.render(key, image_paths, captions, durations,
                           audio_path, this_out, lang=lang)
        results[key] = this_out
    return results


def list_templates():
    """Convenience re-export for callers that only import build_video."""
    return _templates.list_templates()
