#!/usr/bin/env python3
"""Draw a deterministic 32x32 demo creature that obeys POSE_TEMPLATE.md.

A little mushroom: a red spotted cap in the head block (rows 0-12), a rounded
cream face on the stem (rows 13-22), and two stubby boots on the foot baseline
(row 29). No AI, no randomness, no input assets. This file exists so the repo's
example output is reproducible from scratch:

    python3 examples/make_demo_sprite.py          # writes examples/mushroom/source_idle.png
    python3 sprite_animator.py --source examples/mushroom/source_idle.png \
                               --out examples/mushroom --name mushroom

The silhouette is drawn as flat color fills, then a single neighbour pass wraps
it in a 1px outline. That keeps the shape readable at 32x32 the same way a hand
inked sprite would, without hand-placing every edge pixel.
"""

from pathlib import Path

import numpy as np
from PIL import Image

W = H = 32
OUT = Path(__file__).parent / "mushroom"

# palette — warm, friendly, three tones per material
OUTLINE = (58, 38, 48, 255)     # soft dark plum, not pure black
CAP     = (214, 64, 64, 255)    # mushroom red
CAP_SH  = (176, 44, 52, 255)    # cap shadow
CAP_HI  = (232, 108, 98, 255)   # cap highlight
SPOT    = (247, 240, 222, 255)  # cream cap spots
BODY    = (244, 230, 206, 255)  # cream face / stem
BODY_SH = (224, 204, 172, 255)  # stem shadow (under the cap, right edge)
EYE     = (54, 38, 46, 255)
GLINT   = (255, 255, 255, 255)
CHEEK   = (236, 154, 134, 255)
MOUTH   = (150, 92, 84, 255)
BOOT    = (120, 78, 50, 255)
BOOT_HI = (150, 102, 66, 255)


def main():
    a = np.zeros((H, W, 4), dtype=np.uint8)

    def px(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            a[y, x] = c

    def span(x0, x1, y, c):
        for x in range(x0, x1 + 1):
            px(x, y, c)

    # ── cap: red dome that overhangs the stem (head block, rows 3-12) ──
    cap = {
        3: (13, 18), 4: (11, 20), 5: (10, 21), 6: (9, 22), 7: (9, 22),
        8: (8, 23), 9: (7, 24), 10: (7, 24), 11: (6, 25), 12: (6, 25),
    }
    for y, (x0, x1) in cap.items():
        span(x0, x1, y, CAP)
    # highlight band, upper-left; shadow along the brim and right edge
    for y in (4, 5, 6, 7):
        span(cap[y][0], cap[y][0] + 3, y, CAP_HI)
    for y in (11, 12):
        span(cap[y][0], cap[y][1], y, CAP_SH)
    for y in (8, 9, 10):
        span(cap[y][1] - 2, cap[y][1], y, CAP_SH)

    # cream spots on the cap (rounded blobs, not squares)
    for (cx, cy, r) in ((10, 8, 1), (20, 6, 1), (15, 10, 1), (22, 10, 1)):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r + 1:
                    px(cx + dx, cy + dy, SPOT)

    # ── stem / face (torso block, rows 13-22) ──
    stem = {
        13: (9, 22), 14: (8, 23), 15: (8, 23), 16: (8, 23), 17: (8, 23),
        18: (9, 22), 19: (9, 22), 20: (10, 21), 21: (10, 21), 22: (11, 20),
    }
    for y, (x0, x1) in stem.items():
        span(x0, x1, y, BODY)
        px(x1, y, BODY_SH)          # right-edge shade
        px(x1 - 1, y, BODY_SH)
    span(stem[13][0], stem[13][1], 13, BODY_SH)  # shadow cast by the cap

    # eyes (with a glint), cheeks, a small smile
    for ex in (11, 19):
        px(ex, 16, EYE); px(ex + 1, 16, EYE)
        px(ex, 17, EYE); px(ex + 1, 17, EYE)
        px(ex, 16, GLINT)
    px(10, 19, CHEEK); px(21, 19, CHEEK)
    px(14, 20, MOUTH); px(15, 21, MOUTH); px(16, 21, MOUTH); px(17, 20, MOUTH)

    # ── legs / feet (rows 23-29, feet ON baseline row 29) ──
    span(11, 20, 23, BODY)          # hips
    for y in range(24, 30):
        if y == 24:
            col = BODY
        elif y == 25:
            col = BOOT_HI
        else:
            col = BOOT
        span(9, 13, y, col)         # back leg
        span(18, 22, y, col)        # front leg
        if y >= 27:                 # toe extends right on each boot
            px(14, y, col); px(23, y, col)

    # ── single neighbour pass: wrap the silhouette in a 1px outline ──
    opaque = a[:, :, 3] > 0
    out = a.copy()
    for y in range(H):
        for x in range(W):
            if opaque[y, x] or y > 29:   # keep the foot baseline at row 29
                continue
            if ((x > 0 and opaque[y, x - 1]) or (x < W - 1 and opaque[y, x + 1]) or
                    (y > 0 and opaque[y - 1, x]) or (y < H - 1 and opaque[y + 1, x])):
                out[y, x] = OUTLINE
    a = out

    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(a, mode="RGBA").save(OUT / "source_idle.png")
    (OUT / "META.yaml").write_text(
        "signature_action: sparkle\nsignature_spot: [21, 5]\nhas_visible_legs: true\n"
    )
    print(f"wrote {OUT / 'source_idle.png'} + META.yaml")


if __name__ == "__main__":
    main()
