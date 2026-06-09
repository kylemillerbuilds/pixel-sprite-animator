#!/usr/bin/env python3
"""Draw a deterministic 32x32 demo creature that obeys POSE_TEMPLATE.md.

A small acorn-capped forest sprite: round body, two stubby legs on the foot
baseline (row 29), eyes in the head block. No AI, no randomness — this file
exists so the repo's example output is reproducible from scratch:

    python3 examples/make_demo_sprite.py          # writes examples/acorn_kid/source_idle.png
    python3 sprite_animator.py --source examples/acorn_kid/source_idle.png \
                               --out examples/acorn_kid --name acorn_kid
"""

from pathlib import Path

import numpy as np
from PIL import Image

W = H = 32
OUT = Path(__file__).parent / "acorn_kid"

# palette
OUTLINE = (43, 29, 20, 255)
CAP_D   = (122, 78, 44, 255)
CAP_L   = (158, 106, 61, 255)
FACE    = (236, 211, 175, 255)
FACE_SH = (214, 186, 148, 255)
EYE     = (32, 22, 18, 255)
BLUSH   = (226, 156, 130, 255)
LEG     = (107, 72, 45, 255)


def main():
    a = np.zeros((H, W, 4), dtype=np.uint8)

    def px(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            a[y, x] = c

    def hline(x0, x1, y, c):
        for x in range(x0, x1 + 1):
            px(x, y, c)

    # ── acorn cap (head block, rows 4-12) ──
    cap_rows = {4: (13, 18), 5: (11, 20), 6: (10, 21), 7: (9, 22),
                8: (8, 23), 9: (8, 23), 10: (7, 24), 11: (7, 24), 12: (7, 24)}
    for y, (x0, x1) in cap_rows.items():
        hline(x0, x1, y, CAP_D)
        if y >= 6:
            hline(x0 + 2, x1 - 4, y, CAP_L)  # highlight band
        px(x0, y, OUTLINE)
        px(x1, y, OUTLINE)
    hline(13, 18, 3, OUTLINE)        # cap top outline
    px(15, 2, OUTLINE); px(16, 2, OUTLINE)  # stem
    px(15, 1, CAP_D);  px(16, 1, CAP_D)

    # ── face/body (torso block, rows 13-22, round) ──
    body_rows = {13: (8, 23), 14: (8, 23), 15: (7, 24), 16: (7, 24),
                 17: (7, 24), 18: (8, 23), 19: (8, 23), 20: (9, 22),
                 21: (9, 22), 22: (10, 21)}
    for y, (x0, x1) in body_rows.items():
        hline(x0, x1, y, FACE)
        px(x0, y, OUTLINE)
        px(x1, y, OUTLINE)
        px(x1 - 1, y, FACE_SH)  # right shade
    # eyes (row 15-16, symmetric around center col ~15.5)
    px(12, 15, EYE); px(12, 16, EYE)
    px(19, 15, EYE); px(19, 16, EYE)
    # blush
    px(10, 18, BLUSH); px(21, 18, BLUSH)
    # mouth
    px(15, 19, OUTLINE); px(16, 19, OUTLINE)

    # ── legs (rows 23-29, feet ON baseline row 29) ──
    # body tapers into two stubby legs: back leg cols 11-13, front leg cols 18-20
    for y in (23, 24):
        hline(10, 21, y, FACE)
        px(10, y, OUTLINE); px(21, y, OUTLINE)
    for y in range(25, 30):
        for x0, x1 in ((11, 13), (18, 20)):
            hline(x0, x1, y, LEG)
            px(x0, y, OUTLINE)
            px(x1, y, OUTLINE)
    hline(11, 13, 29, OUTLINE)  # feet outline on baseline
    hline(18, 20, 29, OUTLINE)

    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(a, mode="RGBA").save(OUT / "source_idle.png")
    (OUT / "META.yaml").write_text(
        "signature_action: sparkle\nsignature_spot: [26, 6]\nhas_visible_legs: true\n"
    )
    print(f"wrote {OUT / 'source_idle.png'} + META.yaml")


if __name__ == "__main__":
    main()
