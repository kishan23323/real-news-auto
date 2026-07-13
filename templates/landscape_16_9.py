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

    # ── Mid container: per-side margin (gap from container to the top/
    # bottom banners and the screen's left/right edges) and per-side
    # padding (gap from the container's own edge to its content). 0 for
    # padding means "auto" — stays clear of the rounded corners.
    m_top    = style.get("mid_container_margin_top", 0)
    m_right  = style.get("mid_container_margin_right", 22)
    m_bottom = style.get("mid_container_margin_bottom", 0)
    m_left   = style.get("mid_container_margin_left", 22)

    auto_pad = max(round(MID_H * 0.045), round(container_radius * 0.7))
    p_top    = style.get("mid_container_padding_top", 0) or auto_pad
    p_right  = style.get("mid_container_padding_right", 0) or auto_pad
    p_bottom = style.get("mid_container_padding_bottom", 0) or auto_pad
    p_left   = style.get("mid_container_padding_left", 0) or auto_pad

    CONTAINER_X = m_left
    CONTAINER_Y = frame_y + m_top
    CONTAINER_W = W - m_left - m_right
    CONTAINER_H = max(80, MID_H - m_top - m_bottom)
    CONTENT_H   = max(60, CONTAINER_H - p_top - p_bottom)
    GAP        = 12
    HALF_W     = max(80, (CONTAINER_W - p_left - p_right - GAP) // 2)

    layers = []

    # full-bleed body background behind everything (fills any gaps around
    # the rounded container so there's never an unstyled black gap)
    layers.append(
        ColorClip(size=(W, MID_H), color=body_bg_rgb).with_duration(total_duration).with_position((0, frame_y))
    )

    # big rounded red container behind everything
    container = ColorClip(size=(CONTAINER_W, CONTAINER_H), color=frame_rgb).with_duration(total_duration)
    mask = common.rounded_mask_clip(CONTAINER_W, CONTAINER_H, container_radius, total_duration)
    if mask is not None:
        container = container.with_mask(mask)
    layers.append(container.with_position((CONTAINER_X, CONTAINER_Y)))

    content_y = CONTAINER_Y + p_top
    left_x  = CONTAINER_X + p_left
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

    # ── Caption box: per-side margin (positions/sizes the box itself
    # relative to its column) and per-side padding (inset of the text
    # within the box).
    cap_m_top    = style.get("caption_margin_top", 18)
    cap_m_right  = style.get("caption_margin_right", 0)
    cap_m_bottom = style.get("caption_margin_bottom", 0)
    cap_m_left   = style.get("caption_margin_left", 0)
    cap_p_top    = style.get("caption_padding_top", 20)
    cap_p_right  = style.get("caption_padding_right", 20)
    cap_p_bottom = style.get("caption_padding_bottom", 20)
    cap_p_left   = style.get("caption_padding_left", 20)

    yellow_x = right_x + cap_m_left
    yellow_y = content_y + pill.size[1] + cap_m_top
    yellow_w = max(60, HALF_W - cap_m_left - cap_m_right)
    yellow_h = max(60, CONTENT_H - pill.size[1] - cap_m_top - cap_m_bottom)
    yellow_bg = ColorClip(size=(yellow_w, yellow_h), color=caption_bg_rgb).with_duration(total_duration)
    yellow_mask = common.rounded_mask_clip(yellow_w, yellow_h, min(caption_radius, yellow_h // 2), total_duration)
    if yellow_mask is not None:
        yellow_bg = yellow_bg.with_mask(yellow_mask)
    layers.append(yellow_bg.with_position((yellow_x, yellow_y)))

    text_w = max(30, yellow_w - cap_p_left - cap_p_right)
    text_h = max(20, yellow_h - cap_p_top - cap_p_bottom)

    t = 0.0
    for caption, dur in zip(captions, durations):
        clip_dur = dur + 0.3
        # fit_caption_block guarantees the text fits inside (width, height):
        # shrinks font, trims words if still too tall (never mid-word),
        # and hard-clips as a last resort — captions can no longer bleed
        # outside the yellow box.
        cap_clip = common.fit_caption_block(
            common.wrap_caption(caption, max_words=40), text_w, text_h,
            font, caption_size, "black",
            min_size=15, align=style.get("caption_align", "center"),
        )
        cap_clip = cap_clip.with_duration(clip_dur)
        cap_clip = cap_clip.with_effects([vfx.CrossFadeIn(0.3)]).with_start(t)
        cap_clip = cap_clip.with_position((
            yellow_x + cap_p_left,
            yellow_y + cap_p_top + max(0, (text_h - cap_clip.size[1]) // 2),
        ))
        layers.append(cap_clip)
        t += dur

    return layers
