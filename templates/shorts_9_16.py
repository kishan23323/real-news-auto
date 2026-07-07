"""
templates/shorts_9_16.py
──────────────────────────
Shorts / Reels / WhatsApp Status format (9:16). Everything stacked full
width: BREAKING NEWS bar, then image (Ken Burns), then caption.

┌───────────────────┐
│ YELLOW BANNER [lg] │
├───────────────────┤
│┆ BREAKING NEWS bar │
│┆ ┌───────────────┐ │
│┆ │ image (Ken     │ │
│┆ │ Burns zoom)    │ │
│┆ └───────────────┘ │
│┆ ┌───────────────┐ │
│┆ │ yellow caption│ │
│┆ └───────────────┘ │
├───────────────────┤
│ [badge] share text │
└───────────────────┘
"""
from moviepy import ColorClip, CompositeVideoClip, vfx
from . import common

KEY   = "shorts_9_16"
LABEL = "Shorts / Reels / Status (9:16)"
SIZE  = (720, 1280)


def build_body(W, MID_H, frame_y, image_paths, captions, durations,
               total_duration, font, impact_font, style=None):
    style = common.resolve_style(style)
    frame_rgb = common._hex_to_rgb(style["frame_color"], common.RED)
    corner_radius = style["corner_radius"]
    headline_size = style["headline_size"]
    caption_size  = style["caption_size"]

    RED_BORDER  = 8
    PAD_TB      = round(MID_H * 0.06)
    CONTENT_H   = MID_H - 2 * PAD_TB
    SIDE_MARGIN = 14
    CONTENT_W   = W - 2 * SIDE_MARGIN

    layers = [
        ColorClip(size=(W, RED_BORDER), color=frame_rgb).with_duration(total_duration).with_position((0, frame_y)),
        ColorClip(size=(W, RED_BORDER), color=frame_rgb).with_duration(total_duration).with_position((0, frame_y + MID_H - RED_BORDER)),
        ColorClip(size=(RED_BORDER, MID_H), color=frame_rgb).with_duration(total_duration).with_position((0, frame_y)),
        ColorClip(size=(RED_BORDER, MID_H), color=frame_rgb).with_duration(total_duration).with_position((W - RED_BORDER, frame_y)),
    ]

    content_y = frame_y + PAD_TB
    x0 = SIDE_MARGIN

    breaking_h = int(CONTENT_H * 0.09)
    layers.append(
        ColorClip(size=(CONTENT_W, breaking_h), color=frame_rgb).with_duration(total_duration)
        .with_position((x0, content_y))
    )
    bn_txt, _ = common.autofit_textclip(
        "BREAKING NEWS", CONTENT_W - 30, impact_font, start_size=min(headline_size, 56), color="white",
        min_size=20, max_height=breaking_h - 10,
    )
    bn_txt = bn_txt.with_duration(total_duration)
    layers.append(bn_txt.with_position(
        (x0 + (CONTENT_W - bn_txt.size[0]) // 2, content_y + (breaking_h - bn_txt.size[1]) // 2)
    ))

    gap = 10
    image_y = content_y + breaking_h + gap
    image_h = int(CONTENT_H * 0.52)
    image_layers = []
    t = 0.0
    for i, (img, dur) in enumerate(zip(image_paths, durations)):
        clip_dur = dur + 0.4
        image_layers.append(common.ken_burns_clip(img, CONTENT_W, image_h, clip_dur, i % 2 == 0, t, corner_radius))
        t += dur
    img_panel = CompositeVideoClip(image_layers, size=(CONTENT_W, image_h)).with_duration(total_duration)
    layers.append(img_panel.with_position((x0, image_y)))

    yellow_y = image_y + image_h + gap
    yellow_h = CONTENT_H - breaking_h - image_h - 2 * gap
    layers.append(
        ColorClip(size=(CONTENT_W, yellow_h), color=common._hex_to_rgb(style["banner_color"], common.YELLOW))
        .with_duration(total_duration).with_position((x0, yellow_y))
    )

    t = 0.0
    for caption, dur in zip(captions, durations):
        clip_dur = dur + 0.3
        cap_clip = common.autofit_wrapped(
            common.wrap_caption(caption), CONTENT_W - 40, yellow_h - 20, font, min(caption_size, 34), "black",
            min_size=18, align="center",
        )
        cap_clip = cap_clip.with_effects([vfx.CrossFadeIn(0.3)]).with_start(t)
        cap_clip = cap_clip.with_position(
            (x0 + (CONTENT_W - cap_clip.size[0]) // 2, yellow_y + max(10, (yellow_h - cap_clip.size[1]) // 2))
        )
        layers.append(cap_clip)
        t += dur

    return layers
