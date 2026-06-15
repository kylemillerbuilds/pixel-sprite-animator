#!/usr/bin/env python3
"""Draw a deterministic 32x32 demo creature that obeys POSE_TEMPLATE.md.

A little robot: an antenna and a screen-face in the head block (rows 0-12), a
boxy torso with a glowing chest light and short arms (rows 13-22), and two
chunky feet on the foot baseline (row 29). No AI, no randomness, no input
assets. This file exists so the repo's example output is reproducible from
scratch:

    python3 examples/make_demo_sprite.py          # writes examples/robot/source_idle.png
    python3 sprite_animator.py --source examples/robot/source_idle.png \
                               --out examples/robot --name robot

The silhouette is drawn as flat color fills, then a single neighbour pass wraps
it in a 1px outline. That keeps the shape readable at 32x32 the same way a hand
inked sprite would, without hand-placing every edge pixel.
"""

from pathlib import Path

import numpy as np
from PIL import Image

W = H = 32
OUT = Path(__file__).parent / "robot"

# palette — cool brushed metal with a neon accent (matches the brand blue)
OUTLINE = (40, 44, 58, 255)
METAL   = (184, 199, 219, 255)   # body fill
METAL_SH = (134, 152, 178, 255)  # shadow
METAL_DK = (92, 108, 134, 255)   # legs, arms, joints
SCREEN  = (22, 28, 42, 255)      # dark face panel
NEON    = (92, 199, 255, 255)    # eyes, antenna, chest light
NEON_DK = (54, 140, 198, 255)    # neon shadow / mouth grille


def main():
    a = np.zeros((H, W, 4), dtype=np.uint8)

    def px(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            a[y, x] = c

    def span(x0, x1, y, c):
        for x in range(x0, x1 + 1):
            px(x, y, c)

    def block(rows, c):
        for y, (x0, x1) in rows.items():
            span(x0, x1, y, c)

    # ── antenna (rows 0-4) ──
    px(15, 0, NEON); px(16, 0, NEON)
    px(15, 1, NEON); px(16, 1, NEON)
    for y in (2, 3, 4):
        px(15, y, METAL_DK); px(16, y, METAL_DK)

    # ── head (rows 4-12): rounded metal box ──
    head = {4: (11, 20), 5: (9, 22), 6: (8, 23), 7: (8, 23), 8: (8, 23),
            9: (8, 23), 10: (8, 23), 11: (9, 22), 12: (10, 21)}
    block(head, METAL)
    for y in (5, 6, 7):                      # left highlight, right shade
        span(head[y][0], head[y][0] + 2, y, (206, 218, 234, 255))
        span(head[y][1] - 2, head[y][1], y, METAL_SH)
    # screen face panel
    screen = {6: (10, 21), 7: (10, 21), 8: (10, 21), 9: (10, 21), 10: (10, 21)}
    block(screen, SCREEN)
    # eyes (neon) with a brighter core
    for ex in (11, 12, 18, 19):
        px(ex, 7, NEON); px(ex, 8, NEON)
    px(12, 7, (190, 235, 255, 255)); px(18, 7, (190, 235, 255, 255))
    # mouth grille
    for mx in (13, 15, 17):
        px(mx, 10, NEON_DK)

    # ── torso (rows 13-22): boxy with chest light ──
    body = {13: (10, 21), 14: (9, 22), 15: (9, 22), 16: (9, 22), 17: (9, 22),
            18: (9, 22), 19: (10, 21), 20: (10, 21), 21: (10, 21), 22: (11, 20)}
    block(body, METAL)
    for y in body:                            # right-edge shade
        px(body[y][1], y, METAL_SH); px(body[y][1] - 1, y, METAL_SH)
    # chest light
    for (x, y) in ((15, 16), (16, 16), (15, 17), (16, 17)):
        px(x, y, NEON)
    px(15, 15, NEON_DK); px(16, 15, NEON_DK); px(15, 18, NEON_DK); px(16, 18, NEON_DK)
    # short arms at the sides
    for y in (15, 16, 17):
        span(6, 8, y, METAL_DK)               # left arm
        span(23, 25, y, METAL_DK)             # right arm
    px(7, 18, METAL_DK); px(24, 18, METAL_DK)  # hands

    # ── legs + feet (rows 23-29, feet ON baseline 29) ──
    span(11, 20, 23, METAL)                   # hips
    for y in range(24, 28):                   # legs
        col = METAL_SH if y == 24 else METAL_DK
        span(11, 14, y, col)                  # back leg
        span(17, 20, y, col)                  # front leg
    for y in (28, 29):                        # chunky feet, toe extends right
        span(10, 15, y, METAL_DK)             # back foot
        span(17, 22, y, METAL_DK)             # front foot

    # ── single neighbour pass: wrap the silhouette in a 1px outline ──
    opaque = a[:, :, 3] > 0
    out = a.copy()
    for y in range(H):
        for x in range(W):
            if opaque[y, x] or y > 29:
                continue
            if ((x > 0 and opaque[y, x - 1]) or (x < W - 1 and opaque[y, x + 1]) or
                    (y > 0 and opaque[y - 1, x]) or (y < H - 1 and opaque[y + 1, x])):
                out[y, x] = OUTLINE
    a = out

    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(a, mode="RGBA").save(OUT / "source_idle.png")
    (OUT / "META.yaml").write_text(
        "signature_action: sparkle\nsignature_spot: [15, 2]\nhas_visible_legs: true\n"
    )
    print(f"wrote {OUT / 'source_idle.png'} + META.yaml")


if __name__ == "__main__":
    main()
