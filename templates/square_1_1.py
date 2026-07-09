"""
templates/square_1_1.py
─────────────────────────
Square feed-post format (1:1) — Instagram/Facebook feed post size.

Same stacked arrangement as shorts_9_16 (BREAKING NEWS bar, image,
caption) so it reuses that layout function, just rendered onto a
square canvas instead of a tall one. Kept as its own file/template
entry so it shows up as its own selectable option with its own size.
"""
from .shorts_9_16 import build_body  # noqa: F401  (re-exported for the registry)

KEY   = "square_1_1"
LABEL = "Feed post (1:1)"
SIZE  = (1080, 1080)
