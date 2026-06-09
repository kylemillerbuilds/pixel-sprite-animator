#!/usr/bin/env python3
"""
sprite_animator.py — generate a full animation set from ONE idle pixel sprite.

Zero AI at runtime. Every frame is a deterministic pixel transform of the
source sprite, driven by a small rig contract (see POSE_TEMPLATE.md). One
32x32 idle sprite in, a complete animated character out:

  idle      breath rhythm + a per-creature signature action
  walk      articulated A-B-A-C leg cycle (contact-L, passing, contact-R)
  output    per-frame PNGs (real alpha), spritesheet, manifest.json, preview GIFs

Why no AI in the animation step: image models are straight-ahead animators
with zero memory. Ask one for N walk frames and you get N amnesiac drawings —
identity drifts, the motion reads as "character wobbling." Mechanical
derivation of one master sprite keeps identity perfect by construction.
An earlier version of this pipeline used a model for the two walk extremes
and spent most of its code defending against drift; the rig version replaced
it outright and reads better at 32x32.

Animation principles encoded here (the research that mattered):

  - IDLE MASTER IS SACRED. idle_0 is the source sprite, verbatim. Every
    other frame is a mechanical derivation of it.

  - STARDEW A-B-A-C WALK. 4 beats from 3 unique sprites:
    [contact_L, passing, contact_R, passing]. The passing frame is a
    whole-body 1px lift — the moment both feet leave the ground.

  - ARTICULATED LEGS, NOT BULK SHIFT. The leg region splits into back leg
    and front leg, animated asymmetrically (one plants forward, one lifts).
    Uniform shifting reads as a "hopping PNG," not a walk.

  - INTERNAL BREATH. Only the torso rows lift on the breath frame; head and
    feet stay planted. Shifting the whole sprite reads as bouncing, not
    breathing.

  - TIMING. 6fps walk (~170ms/frame), 4fps idle (250ms). Cozy-game cadence;
    Stardew farm animals run ~200ms/frame.

  - SIGNATURE ACTIONS. Each creature gets one personality frame in its idle
    loop (a bow, a hat tilt, a sparkle...) declared in an optional META.yaml
    next to the source sprite.

Usage:
  python3 sprite_animator.py --source creature/source_idle.png \
                             --out creature/ --name owl_monk

Optional META.yaml (next to the source sprite):
  signature_action: sparkle      # bow | hat_tilt | sparkle | twinkle | steam
  signature_spot: [24, 9]        # x, y — required for sparkle/twinkle/steam
  has_visible_legs: true         # false = robed/round creature, uses body sway
"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

# ─── Rig contract (POSE_TEMPLATE.md) — tuned for 32x32 sprites ─────────────

LEG_REGION_TOP = 23   # rows 23-29 = legs/feet
LEG_REGION_BOT = 30
LEG_SPLIT_COL = 16    # cols 0-15 = back leg, 16-31 = front leg
TORSO_TOP = 13        # rows 13-22 = torso/chest (the breathing zone)
TORSO_BOT = 23        # exclusive
HEAD_REGION_BOT = 13  # rows 0-12 = head/hat


@dataclass
class SpriteConfig:
    source: Path
    out_dir: Path
    name: str


# ─── Walk synthesis — articulated, not bulk-shift ───────────────────────────

def detect_hip_line(idle: Image.Image) -> int:
    """Auto-detect the FEET line — the row where the character narrows down
    to actual feet/legs (vs body). Returns hip row, clamped to [25, 28].

    Strategy: scan rows 22-28 looking for the LATEST significant narrowing.
    The earliest narrowing might be chest-to-waist, which would articulate
    too much body. The latest narrowing is where feet actually begin.
    A creature with no sharp transition falls back to the default 25.
    """
    arr = np.array(idle.convert("RGBA"))
    alpha = arr[:, :, 3]
    rgb = arr[:, :, :3]
    mag = (rgb[..., 0] > 240) & (rgb[..., 1] < 30) & (rgb[..., 2] > 240)
    char = (alpha > 200) & ~mag
    if not char.any():
        return 25
    counts = char.sum(axis=1)
    hip = 25  # default
    for y in range(28, 21, -1):  # reverse scan: latest narrowing wins
        if counts[y] < 2:
            continue
        prev = counts[y - 1] if y > 0 else 0
        # Significant narrowing: at least 40% drop, or absolute drop >= 5
        if prev > 4 and (counts[y] < prev * 0.60 or (prev - counts[y]) >= 5):
            hip = y
            break
    return max(25, min(28, hip))


def synthesize_contact_L(idle: Image.Image, has_visible_legs: bool = True) -> Image.Image:
    """Left foot forward, right foot lifted.

    has_visible_legs=True: auto-detects the hip line, then articulates legs
        only below it. Back leg plants forward, front leg lifts. Body above
        the hip is untouched.

    has_visible_legs=False: top-half SWAY — body tilts 1px left while the
        base stays planted. Reads as a robed/round creature shifting weight,
        not as a slime sliding.
    """
    arr = np.array(idle.convert("RGBA")).copy()

    if has_visible_legs:
        hip = detect_hip_line(idle)
        legs = arr[hip:LEG_REGION_BOT].copy()
        arr[hip:LEG_REGION_BOT] = 0
        back = legs[:, :LEG_SPLIT_COL]                       # planted forward
        arr[hip:LEG_REGION_BOT, 1:LEG_SPLIT_COL + 1] = back
        front = legs[:, LEG_SPLIT_COL:]                      # lifted
        arr[hip - 1:LEG_REGION_BOT - 1, LEG_SPLIT_COL:] = front
    else:
        BASE_BOTTOM = 26  # base rows stay planted
        top = arr[:BASE_BOTTOM].copy()
        arr[:BASE_BOTTOM] = 0
        arr[:BASE_BOTTOM, :-1] = top[:, 1:]  # top shifted left
    return Image.fromarray(arr, mode="RGBA")


def synthesize_contact_R(idle: Image.Image, has_visible_legs: bool = True) -> Image.Image:
    """Right foot forward, left foot lifted. Mirror of contact_L."""
    arr = np.array(idle.convert("RGBA")).copy()

    if has_visible_legs:
        hip = detect_hip_line(idle)
        legs = arr[hip:LEG_REGION_BOT].copy()
        arr[hip:LEG_REGION_BOT] = 0
        front = legs[:, LEG_SPLIT_COL:31]                    # planted forward
        arr[hip:LEG_REGION_BOT, LEG_SPLIT_COL + 1:32] = front
        back = legs[:, :LEG_SPLIT_COL]                       # lifted
        arr[hip - 1:LEG_REGION_BOT - 1, :LEG_SPLIT_COL] = back
    else:
        BASE_BOTTOM = 26
        top = arr[:BASE_BOTTOM].copy()
        arr[:BASE_BOTTOM] = 0
        arr[:BASE_BOTTOM, 1:] = top[:, :-1]  # top shifted right
    return Image.fromarray(arr, mode="RGBA")


def synthesize_passing(idle: Image.Image) -> Image.Image:
    """Walk passing pose — whole-body lift 1px. Correct for the walk's high
    beat (both feet leave the ground momentarily). NOT used for idle.
    """
    arr = np.array(idle.convert("RGBA"))
    bobbed = np.zeros_like(arr)
    bobbed[:-1] = arr[1:]
    return Image.fromarray(bobbed, mode="RGBA")


def synthesize_breath(idle: Image.Image) -> Image.Image:
    """INTERNAL breath — torso rows shift UP 1px while head and legs stay
    planted. Creates a chest-rising motion that reads as breathing, not as
    the whole sprite hopping.
    """
    arr = np.array(idle.convert("RGBA")).copy()
    torso = arr[TORSO_TOP:TORSO_BOT].copy()
    arr[TORSO_TOP:TORSO_BOT - 1] = 0          # clear torso rows (keep hip row)
    arr[TORSO_TOP - 1:TORSO_BOT - 1] = torso  # torso now 1px higher
    return Image.fromarray(arr, mode="RGBA")


# ─── Signature idle actions (per-creature personality) ──────────────────────

def synthesize_bow(idle: Image.Image) -> Image.Image:
    """Head region shifts down 1px — meditative bow / nod."""
    arr = np.array(idle.convert("RGBA")).copy()
    head = arr[:HEAD_REGION_BOT].copy()
    arr[:HEAD_REGION_BOT] = 0
    arr[1:HEAD_REGION_BOT + 1] = head
    return Image.fromarray(arr, mode="RGBA")


def synthesize_hat_tilt(idle: Image.Image, direction: int = -1) -> Image.Image:
    """Top rows shift sideways — character adjusting hat."""
    arr = np.array(idle.convert("RGBA")).copy()
    head = arr[:HEAD_REGION_BOT].copy()
    arr[:HEAD_REGION_BOT] = 0
    if direction < 0:
        arr[:HEAD_REGION_BOT, :-1] = head[:, 1:]
    else:
        arr[:HEAD_REGION_BOT, 1:] = head[:, :-1]
    return Image.fromarray(arr, mode="RGBA")


def synthesize_sparkle(idle: Image.Image, spot: tuple, color=(255, 240, 200)) -> Image.Image:
    """Bright 3-pixel cluster appears at (x, y) — wand spark, hammer strike."""
    arr = np.array(idle.convert("RGBA")).copy()
    x, y = spot
    h, w = arr.shape[:2]
    for dx, dy in ((0, 0), (0, -1), (1, 0)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h:
            arr[ny, nx] = [color[0], color[1], color[2], 255]
    return Image.fromarray(arr, mode="RGBA")


def synthesize_twinkle(idle: Image.Image, spot: tuple, color=(255, 255, 220)) -> Image.Image:
    """Single bright pixel toggles at (x, y) — subtle twinkle."""
    arr = np.array(idle.convert("RGBA")).copy()
    x, y = spot
    h, w = arr.shape[:2]
    if 0 <= x < w and 0 <= y < h:
        arr[y, x] = [color[0], color[1], color[2], 255]
    return Image.fromarray(arr, mode="RGBA")


def synthesize_steam(idle: Image.Image, spot: tuple, color=(240, 230, 220)) -> Image.Image:
    """Vertical 3-pixel column of light pixels rising from (x, y)."""
    arr = np.array(idle.convert("RGBA")).copy()
    x, y = spot
    h, w = arr.shape[:2]
    for dy in range(3):
        ny = y - dy
        if 0 <= ny < h and 0 <= x < w:
            arr[ny, x] = [color[0], color[1], color[2], 255]
    return Image.fromarray(arr, mode="RGBA")


def synthesize_signature_action(idle: Image.Image, action: str, spot=None) -> Image.Image:
    """Dispatch by META.yaml's signature_action. Unknown action or missing
    spot falls back to bow, which works on any creature."""
    if action == "hat_tilt":
        return synthesize_hat_tilt(idle)
    if action == "sparkle" and spot is not None:
        return synthesize_sparkle(idle, spot)
    if action == "twinkle" and spot is not None:
        return synthesize_twinkle(idle, spot)
    if action == "steam" and spot is not None:
        return synthesize_steam(idle, spot)
    return synthesize_bow(idle)


# ─── Spritesheet + GIF ───────────────────────────────────────────────────────

def build_spritesheet(frames, frame_w: int, frame_h: int) -> Image.Image:
    sheet = Image.new("RGBA", (frame_w * len(frames), frame_h), (0, 0, 0, 0))
    for i, (_, f) in enumerate(frames):
        sheet.paste(f, (i * frame_w, 0), f)
    return sheet


def build_gif_from_sequence(frames_by_name, sequence, fps, out_path: Path,
                            zoom: int = 8, bg_color=(250, 250, 250)) -> bool:
    """Build a preview GIF from a NAMED SEQUENCE.

    Composites each frame onto a solid neutral background before encoding —
    PIL's disposal+transparency GIF handling produces ghosting artifacts
    otherwise. The GIF is for eyeball preview only; the per-frame PNGs
    retain real alpha for game-engine use.
    """
    imgs = []
    for name in sequence:
        if name not in frames_by_name:
            return False
        f = frames_by_name[name]
        zoomed = f.resize((f.width * zoom, f.height * zoom), Image.Resampling.NEAREST)
        bg = Image.new("RGB", zoomed.size, bg_color)
        bg.paste(zoomed, (0, 0), zoomed if zoomed.mode == "RGBA" else None)
        imgs.append(bg)
    imgs[0].save(out_path, save_all=True, append_images=imgs[1:],
                 duration=int(1000 / max(fps, 1)), loop=0)
    return True


# ─── Main pipeline ───────────────────────────────────────────────────────────

def run(cfg: SpriteConfig) -> dict:
    source = Image.open(cfg.source).convert("RGBA")
    src_w, src_h = source.size
    print(f"[source] {cfg.source.name} {src_w}x{src_h}")

    # Chroma-key the source if it arrives on a magenta background
    src_arr = np.array(source)
    magenta = ((src_arr[..., 0] > 240) & (src_arr[..., 1] < 30) &
               (src_arr[..., 2] > 240) & (src_arr[..., 3] > 200))
    if magenta.any():
        src_arr[magenta] = [0, 0, 0, 0]
        source = Image.fromarray(src_arr, mode="RGBA")
        print(f"[source] chroma-keyed {int(magenta.sum())} magenta bg pixels")

    # Validate against the pose template (advisory)
    char = (np.array(source)[:, :, 3] > 200)
    if char.any():
        rows = np.where(char.any(axis=1))[0]
        foot_y = int(rows.max())
        if foot_y != 29:
            print(f"[template] WARN: foot baseline row {foot_y} != 29 "
                  f"(POSE_TEMPLATE.md). Walk articulation may misalign.")

    cfg.out_dir.mkdir(parents=True, exist_ok=True)

    # Optional META.yaml: per-creature personality
    sig_action, sig_spot, has_visible_legs = "bow", None, True
    meta_path = cfg.source.parent / "META.yaml"
    if meta_path.exists():
        try:
            import yaml
            meta = yaml.safe_load(meta_path.read_text())
            sig_action = meta.get("signature_action", "bow")
            sp = meta.get("signature_spot")
            if sp and isinstance(sp, list) and len(sp) == 2:
                sig_spot = (int(sp[0]), int(sp[1]))
            has_visible_legs = bool(meta.get("has_visible_legs", True))
            print(f"[meta] signature_action={sig_action} spot={sig_spot} legs={has_visible_legs}")
        except Exception as e:
            print(f"[meta] failed to parse META.yaml: {e} — using defaults")

    # Synthesize ALL frames algorithmically
    idle_0 = source
    frames_named = [
        ("idle_0", idle_0),
        ("breath", synthesize_breath(source)),
        ("walk_passing", synthesize_passing(source)),
        ("signature", synthesize_signature_action(source, sig_action, sig_spot)),
        ("contact_L", synthesize_contact_L(source, has_visible_legs)),
        ("contact_R", synthesize_contact_R(source, has_visible_legs)),
    ]
    print(f"[rig] {len(frames_named)} frames synthesized (signature: {sig_action})")

    # QA: walk frames must differ from idle in the leg region ONLY
    src_a = np.array(source)
    for nm in ("contact_L", "contact_R"):
        f_a = np.array(dict(frames_named)[nm])
        drift = ((src_a[:LEG_REGION_TOP] != f_a[:LEG_REGION_TOP]).any(axis=2)).sum()
        print(f"[rig] body-drift {nm} vs idle_0: {drift}px (target 0)")

    for name, img in frames_named:
        img.save(cfg.out_dir / f"{name}.png")

    sheet = build_spritesheet(frames_named, src_w, src_h)
    sheet.save(cfg.out_dir / f"{cfg.name}_spritesheet.png")

    # Zoomed preview, long edge capped at 1920
    zoom = max(1, min(8, 1920 // max(sheet.width, sheet.height)))
    sheet.resize((sheet.width * zoom, sheet.height * zoom),
                 Image.Resampling.NEAREST).save(
        cfg.out_dir / f"{cfg.name}_spritesheet_{zoom}x.png")

    # Manifest: animations are NAMED SEQUENCES (enables A-B-A-C reuse)
    animations = {
        "idle": {
            "sequence": ["idle_0", "breath", "idle_0", "breath", "idle_0", "breath",
                         "signature",
                         "idle_0", "breath", "idle_0", "breath", "idle_0"],
            "fps": 4,
            "loop": True,
        },
        "walk": {
            "sequence": ["contact_L", "contact_L", "walk_passing",
                         "contact_R", "contact_R", "walk_passing"],
            "fps": 6,
            "loop": True,
        },
    }
    manifest = {
        "name": cfg.name,
        "source": cfg.source.name,
        "frame_width": src_w,
        "frame_height": src_h,
        "frames": [n for n, _ in frames_named],
        "animations": animations,
    }
    (cfg.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    frames_by_name = dict(frames_named)
    for anim_name, spec in animations.items():
        gif_path = cfg.out_dir / f"{cfg.name}_{anim_name}.gif"
        if build_gif_from_sequence(frames_by_name, spec["sequence"], spec["fps"], gif_path):
            print(f"[gif] wrote {gif_path.name} ({len(spec['sequence'])}f @ {spec['fps']}fps)")

    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    p.add_argument("--source", type=Path, required=True, help="32x32 idle sprite PNG")
    p.add_argument("--out", type=Path, required=True, help="output directory")
    p.add_argument("--name", required=True, help="creature name (file prefix)")
    args = p.parse_args()
    manifest = run(SpriteConfig(source=args.source, out_dir=args.out, name=args.name))
    print("\n[done]", json.dumps({k: manifest[k] for k in ("name", "frames")}, indent=2))


if __name__ == "__main__":
    main()
