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
               total_duration, font, impact_font, style=None):
    style = common.resolve_style(style)
    frame_rgb = common._hex_to_rgb(style["frame_color"], common.RED)
    corner_radius = style["corner_radius"]
    container_radius = style["container_radius"]
    headline_size = style["headline_size"]
    caption_size  = style["caption_size"]

    MARGIN_X   = 22
    PAD        = round(MID_H * 0.045)
    CONTENT_H  = MID_H - 2 * PAD
    CONTAINER_W = W - 2 * MARGIN_X
    GAP        = 12
    HALF_W     = (CONTAINER_W - 3 * PAD - GAP) // 2

    layers = []

    # big rounded red container behind everything
    container = ColorClip(size=(CONTAINER_W, MID_H), color=frame_rgb).with_duration(total_duration)
    mask = common.rounded_mask_clip(CONTAINER_W, MID_H, container_radius, total_duration)
    if mask is not None:
        container = container.with_mask(mask)
    layers.append(container.with_position((MARGIN_X, frame_y)))

    content_y = frame_y + PAD
    left_x  = MARGIN_X + PAD
    right_x = left_x + HALF_W + GAP

    # left: white-bordered rounded image panel with a subtle gradient overlay
    border = 6
    image_layers = []
    t = 0.0
    for i, (img, dur) in enumerate(zip(image_paths, durations)):
        clip_dur = dur + 0.4
        image_layers.append(common.ken_burns_clip(
            img, HALF_W - border * 2, CONTENT_H - border * 2, clip_dur, i % 2 == 0, t,
            max(0, corner_radius - border),
        ))
        t += dur
    img_inner = CompositeVideoClip(image_layers, size=(HALF_W - border * 2, CONTENT_H - border * 2)).with_duration(total_duration)
    white_bg = ColorClip(size=(HALF_W, CONTENT_H), color=(255, 255, 255)).with_duration(total_duration)
    white_mask = common.rounded_mask_clip(HALF_W, CONTENT_H, corner_radius, total_duration)
    if white_mask is not None:
        white_bg = white_bg.with_mask(white_mask)
    gradient = common.gradient_overlay_clip(HALF_W - border * 2, CONTENT_H - border * 2, total_duration)
    left_panel = CompositeVideoClip(
        [white_bg, img_inner.with_position((border, border)), gradient.with_position((border, border))],
        size=(HALF_W, CONTENT_H),
    ).with_duration(total_duration)
    layers.append(left_panel.with_position((left_x, content_y)))

    # right: BREAKING NEWS pill (red background, white text, per reference) + rounded yellow caption box
    pill = common.pill_clip("BREAKING NEWS", impact_font, headline_size, style["frame_color"], "#FFFFFF",
                             36, 16, total_duration, min_size=24)
    pill_w = min(pill.size[0], HALF_W)
    layers.append(pill.with_position((right_x, content_y)))

    yellow_gap = 18
    yellow_y = content_y + pill.size[1] + yellow_gap
    yellow_h = CONTENT_H - pill.size[1] - yellow_gap
    yellow_bg = ColorClip(size=(HALF_W, yellow_h), color=common._hex_to_rgb(style["banner_color"], common.YELLOW)).with_duration(total_duration)
    yellow_mask = common.rounded_mask_clip(HALF_W, yellow_h, min(20, corner_radius), total_duration)
    if yellow_mask is not None:
        yellow_bg = yellow_bg.with_mask(yellow_mask)
    layers.append(yellow_bg.with_position((right_x, yellow_y)))

    t = 0.0
    for caption, dur in zip(captions, durations):
        clip_dur = dur + 0.3
        cap_clip = common.autofit_wrapped(
            common.wrap_caption(caption), HALF_W - 40, yellow_h - 20, font, caption_size, "black",
            min_size=16, align="center",
        )
        cap_clip = cap_clip.with_duration(clip_dur).with_effects([vfx.CrossFadeIn(0.3)]).with_start(t)
        cap_clip = cap_clip.with_position(
            (right_x + 20, yellow_y + max(10, (yellow_h - cap_clip.size[1]) // 2))
        )
        layers.append(cap_clip)
        t += dur

    return layers
