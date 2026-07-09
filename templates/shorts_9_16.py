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
    container_radius = style["container_radius"]
    headline_size = style["headline_size"]
    caption_size  = style["caption_size"]

    MARGIN_X   = 16
    PAD        = round(MID_H * 0.028)
    CONTENT_H  = MID_H - 2 * PAD
    CONTAINER_W = W - 2 * MARGIN_X

    layers = []

    container = ColorClip(size=(CONTAINER_W, MID_H), color=frame_rgb).with_duration(total_duration)
    mask = common.rounded_mask_clip(CONTAINER_W, MID_H, container_radius, total_duration)
    if mask is not None:
        container = container.with_mask(mask)
    layers.append(container.with_position((MARGIN_X, frame_y)))

    content_y = frame_y + PAD
    x0 = MARGIN_X + PAD
    content_w = CONTAINER_W - 2 * PAD

    # BREAKING NEWS pill, centered
    pill = common.pill_clip("BREAKING NEWS", impact_font, min(headline_size, 56),
                             style["frame_color"], "#FFFFFF", 30, 12, total_duration, min_size=20)
    layers.append(pill.with_position((x0 + (content_w - pill.size[0]) // 2, content_y)))

    gap = 14
    image_y = content_y + pill.size[1] + gap
    image_h = int(CONTENT_H * 0.50)
    border = 5

    image_layers = []
    t = 0.0
    for i, (img, dur) in enumerate(zip(image_paths, durations)):
        clip_dur = dur + 0.4
        image_layers.append(common.ken_burns_clip(
            img, content_w - border * 2, image_h - border * 2, clip_dur, i % 2 == 0, t,
            max(0, corner_radius - border),
        ))
        t += dur
    img_inner = CompositeVideoClip(image_layers, size=(content_w - border * 2, image_h - border * 2)).with_duration(total_duration)
    white_bg = ColorClip(size=(content_w, image_h), color=(255, 255, 255)).with_duration(total_duration)
    white_mask = common.rounded_mask_clip(content_w, image_h, corner_radius, total_duration)
    if white_mask is not None:
        white_bg = white_bg.with_mask(white_mask)
    gradient = common.gradient_overlay_clip(content_w - border * 2, image_h - border * 2, total_duration)
    img_panel = CompositeVideoClip(
        [white_bg, img_inner.with_position((border, border)), gradient.with_position((border, border))],
        size=(content_w, image_h),
    ).with_duration(total_duration)
    layers.append(img_panel.with_position((x0, image_y)))

    yellow_y = image_y + image_h + gap
    yellow_h = CONTENT_H - pill.size[1] - image_h - 2 * gap
    yellow_bg = ColorClip(size=(content_w, yellow_h), color=common._hex_to_rgb(style["banner_color"], common.YELLOW)).with_duration(total_duration)
    yellow_mask = common.rounded_mask_clip(content_w, yellow_h, min(20, corner_radius), total_duration)
    if yellow_mask is not None:
        yellow_bg = yellow_bg.with_mask(yellow_mask)
    layers.append(yellow_bg.with_position((x0, yellow_y)))

    t = 0.0
    for caption, dur in zip(captions, durations):
        clip_dur = dur + 0.3
        cap_clip = common.autofit_wrapped(
            common.wrap_caption(caption), content_w - 40, yellow_h - 20, font, min(caption_size, 34), "black",
            min_size=16, align="center",
        )
        cap_clip = cap_clip.with_duration(clip_dur).with_effects([vfx.CrossFadeIn(0.3)]).with_start(t)
        cap_clip = cap_clip.with_position(
            (x0 + (content_w - cap_clip.size[0]) // 2, yellow_y + max(10, (yellow_h - cap_clip.size[1]) // 2))
        )
        layers.append(cap_clip)
        t += dur

    return layers
