"""
templates/landscape_16_9.py
────────────────────────────
YouTube / TV format (16:9). Left image panel (Ken Burns), right
BREAKING NEWS + caption panel.

┌───────────────────────────┐
│ YELLOW BANNER    [logo]   │
├───────────────────────────┤
│┆  ┌──────────┐┌─────────┐ │
│┆  │  image   ││BREAKING │ │
│┆  │  (Ken    ││ NEWS    │ │
│┆  │  Burns)  │├─────────┤ │
│┆  │          ││ yellow  │ │
│┆  └──────────┘│ caption │ │
│┆              └─────────┘ │
├───────────────────────────┤
│ [badge]   share text       │
└───────────────────────────┘
"""
from moviepy import ColorClip, CompositeVideoClip, vfx
from . import common

KEY   = "landscape_16_9"
LABEL = "YouTube / TV (16:9)"
SIZE  = (1280, 720)


def build_body(W, MID_H, frame_y, image_paths, captions, durations,
               total_duration, font, impact_font):
    RED_BORDER  = 8
    PAD_TB      = round(MID_H * 0.10)
    CONTENT_H   = MID_H - 2 * PAD_TB
    SIDE_MARGIN = 16
    GAP         = 10
    HALF_W      = (W - 2 * SIDE_MARGIN - GAP) // 2

    layers = [
        ColorClip(size=(W, RED_BORDER), color=common.RED).with_duration(total_duration).with_position((0, frame_y)),
        ColorClip(size=(W, RED_BORDER), color=common.RED).with_duration(total_duration).with_position((0, frame_y + MID_H - RED_BORDER)),
        ColorClip(size=(RED_BORDER, MID_H), color=common.RED).with_duration(total_duration).with_position((0, frame_y)),
        ColorClip(size=(RED_BORDER, MID_H), color=common.RED).with_duration(total_duration).with_position((W - RED_BORDER, frame_y)),
    ]

    content_y = frame_y + PAD_TB
    left_x  = SIDE_MARGIN
    right_x = SIDE_MARGIN + HALF_W + GAP

    image_layers = []
    t = 0.0
    for i, (img, dur) in enumerate(zip(image_paths, durations)):
        clip_dur = dur + 0.4
        image_layers.append(common.ken_burns_clip(img, HALF_W, CONTENT_H, clip_dur, i % 2 == 0, t))
        t += dur
    left_panel = CompositeVideoClip(image_layers, size=(HALF_W, CONTENT_H)).with_duration(total_duration)
    layers.append(left_panel.with_position((left_x, content_y)))

    breaking_h = int(CONTENT_H * 0.18)
    layers.append(
        ColorClip(size=(HALF_W, breaking_h), color=common.RED).with_duration(total_duration)
        .with_position((right_x, content_y))
    )
    bn_txt, _ = common.autofit_textclip(
        "BREAKING NEWS", HALF_W - 30, impact_font, start_size=64, color="white",
        min_size=22, max_height=breaking_h - 14,
    )
    bn_txt = bn_txt.with_duration(total_duration)
    layers.append(bn_txt.with_position(
        (right_x + (HALF_W - bn_txt.size[0]) // 2, content_y + (breaking_h - bn_txt.size[1]) // 2)
    ))

    yellow_gap = 8
    yellow_y = content_y + breaking_h + yellow_gap
    yellow_h = CONTENT_H - breaking_h - yellow_gap
    layers.append(
        ColorClip(size=(HALF_W, yellow_h), color=common.YELLOW).with_duration(total_duration)
        .with_position((right_x, yellow_y))
    )

    t = 0.0
    for caption, dur in zip(captions, durations):
        clip_dur = dur + 0.3
        cap_clip = common.wrapped_text_clip(
            common.wrap_caption(caption), HALF_W - 40, font, 30, "black", clip_dur, align="center",
        )
        cap_clip = cap_clip.with_effects([vfx.CrossFadeIn(0.3)]).with_start(t)
        cap_clip = cap_clip.with_position(
            (right_x + 20, yellow_y + max(10, (yellow_h - cap_clip.size[1]) // 2))
        )
        layers.append(cap_clip)
        t += dur

    return layers
