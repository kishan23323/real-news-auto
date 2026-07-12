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
    body_bg_rgb = common._hex_to_rgb(style.get("body_bg", "#000000"), (0, 0, 0))
    img_bg_rgb = common._hex_to_rgb(style.get("image_bg", "#FFFFFF"), (255, 255, 255))
    caption_bg_rgb = common._hex_to_rgb(style.get("banner_color", "#FFD100"), common.YELLOW)
    
    corner_radius = style.get("corner_radius", 28)
    container_radius = style.get("container_radius", 36)
    headline_size = style.get("headline_size", 64)
    caption_size  = style.get("caption_size", 30)
    image_border = style.get("image_border", 6)
    image_grad_alpha = style.get("image_gradient_alpha", 0.45)
    breaking_text = style.get("breaking_text", "BREAKING NEWS")
    breaking_text_color = style.get("breaking_text_color", "#FFFFFF")
    breaking_outline = style.get("breaking_outline", "#FFFFFF")
    breaking_box_width = style.get("breaking_box_width", 0)
    breaking_box_height = style.get("breaking_box_height", 0)
    breaking_font_choice = style.get("breaking_font", "impact")
    breaking_align = style.get("breaking_text_align", "center")
    caption_radius = style.get("caption_radius", 12)
    caption_padding = style.get("caption_padding", 20)
    caption_margin = style.get("caption_margin", 18)

    MARGIN_X   = style.get("mid_container_margin", 22)
    # Keep interior padding at least as large as the container's corner
    # radius so content never sits inside the rounded-corner cutout
    # (previously the BREAKING NEWS pill could appear to float outside
    # the red background there). 0 = auto.
    _pad_setting = style.get("mid_container_padding", 0)
    PAD        = int(_pad_setting) if _pad_setting else max(round(MID_H * 0.045), round(container_radius * 0.7))
    CONTENT_H  = MID_H - 2 * PAD
    CONTAINER_W = W - 2 * MARGIN_X
    GAP        = 12
    HALF_W     = (CONTAINER_W - 3 * PAD - GAP) // 2

    layers = []

    # full-bleed body background behind everything (fills any gaps around
    # the rounded container so there's never an unstyled black gap)
    layers.append(
        ColorClip(size=(W, MID_H), color=body_bg_rgb).with_duration(total_duration).with_position((0, frame_y))
    )

    # big rounded red container behind everything
    container = ColorClip(size=(CONTAINER_W, MID_H), color=frame_rgb).with_duration(total_duration)
    mask = common.rounded_mask_clip(CONTAINER_W, MID_H, container_radius, total_duration)
    if mask is not None:
        container = container.with_mask(mask)
    layers.append(container.with_position((MARGIN_X, frame_y)))

    content_y = frame_y + PAD
    left_x  = MARGIN_X + PAD
    right_x = left_x + HALF_W + GAP

    # left: white-bordered rounded image panel with edge-vignette overlay
    image_layers = []
    t = 0.0
    for i, (img, dur) in enumerate(zip(image_paths, durations)):
        clip_dur = dur + 0.4
        image_layers.append(common.ken_burns_clip(
            img, HALF_W - image_border * 2, CONTENT_H - image_border * 2, clip_dur, i % 2 == 0, t,
            max(0, corner_radius - image_border),
        ))
        t += dur
    img_inner = CompositeVideoClip(image_layers, size=(HALF_W - image_border * 2, CONTENT_H - image_border * 2)).with_duration(total_duration)
    white_bg = ColorClip(size=(HALF_W, CONTENT_H), color=img_bg_rgb).with_duration(total_duration)
    white_mask = common.rounded_mask_clip(HALF_W, CONTENT_H, corner_radius, total_duration)
    if white_mask is not None:
        white_bg = white_bg.with_mask(white_mask)
    gradient = common.gradient_overlay_clip(HALF_W - image_border * 2, CONTENT_H - image_border * 2, total_duration, image_grad_alpha)
    left_panel = CompositeVideoClip(
        [white_bg, img_inner.with_position((image_border, image_border)), gradient.with_position((image_border, image_border))],
        size=(HALF_W, CONTENT_H),
    ).with_duration(total_duration)
    layers.append(left_panel.with_position((left_x, content_y)))

    # right: BREAKING NEWS pill (with visible outline so it's never
    # invisible against a same-colored background) + rounded yellow caption box
    breaking_font = common.resolve_font_choice(breaking_font_choice, impact_font)
    pill_max_w = HALF_W if breaking_box_width == 0 else min(breaking_box_width, HALF_W)
    pill = common.pill_clip(breaking_text, breaking_font, headline_size, style.get("breaking_bg", "#8E0E0E"),
                             breaking_text_color, 36, 16, total_duration, min_size=24,
                             outline_hex=breaking_outline, outline_width=3,
                             fixed_width=pill_max_w if breaking_box_width else None,
                             fixed_height=breaking_box_height if breaking_box_height else None,
                             align=breaking_align)
    layers.append(pill.with_position((right_x, content_y)))

    yellow_gap = caption_margin
    yellow_y = content_y + pill.size[1] + yellow_gap
    yellow_h = max(60, CONTENT_H - pill.size[1] - yellow_gap)
    yellow_bg = ColorClip(size=(HALF_W, yellow_h), color=caption_bg_rgb).with_duration(total_duration)
    yellow_mask = common.rounded_mask_clip(HALF_W, yellow_h, min(caption_radius, yellow_h // 2), total_duration)
    if yellow_mask is not None:
        yellow_bg = yellow_bg.with_mask(yellow_mask)
    layers.append(yellow_bg.with_position((right_x, yellow_y)))

    t = 0.0
    for caption, dur in zip(captions, durations):
        clip_dur = dur + 0.3
        # fit_caption_block guarantees the text fits inside (width, height):
        # shrinks font, trims words if still too tall, and hard-clips as a
        # last resort — captions can no longer bleed outside the yellow box.
        cap_clip = common.fit_caption_block(
            common.wrap_caption(caption, max_words=40), HALF_W - caption_padding * 2, yellow_h - caption_padding,
            font, caption_size, "black",
            min_size=15, align=style.get("caption_align", "center"),
        )
        cap_clip = cap_clip.with_duration(clip_dur)
        cap_clip = cap_clip.with_effects([vfx.CrossFadeIn(0.3)]).with_start(t)
        cap_clip = cap_clip.with_position(
            (right_x + caption_padding, yellow_y + max(10, (yellow_h - cap_clip.size[1]) // 2))
        )
        layers.append(cap_clip)
        t += dur

    return layers
