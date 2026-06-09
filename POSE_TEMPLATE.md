# Pose template — the rig contract

The animator is a rig, and rigs need anatomy in known places. Source sprites that follow this contract animate correctly; sprites that don't will still run, but the walk articulation lands on the wrong rows.

## The 32x32 contract

```
row 0  ┌────────────────────────────┐
       │  HEAD / HAT     rows 0-12  │  ← signature actions move this block
row 13 ├────────────────────────────┤
       │  TORSO / CHEST  rows 13-22 │  ← breath frame lifts this block 1px
row 23 ├────────────────────────────┤
       │  LEGS / FEET    rows 23-29 │  ← walk cycle articulates here
row 29 ├──── FOOT BASELINE ─────────┤  ← bottom-most opaque pixel sits HERE
row 30 │  (empty)        rows 30-31 │
row 31 └────────────────────────────┘
         cols 0-15 = back leg side · cols 16-31 = front leg side
```

Rules:

1. **Foot baseline at row 29.** The character's lowest opaque pixel sits on row 29, not 30 or 31. The animator warns if it doesn't.
2. **Character faces right.** Walk poses assume rightward travel.
3. **Background: transparent or solid magenta (#FF00FF).** Magenta is keyed out automatically (it survives art tools that won't export alpha).
4. **Eyes and identity detail live in the head block (rows 0-12).** Everything there is never touched by walk or breath frames.
5. **One creature per file, roughly centered.**

## Legless creatures

Robed, round, or floating creatures set `has_visible_legs: false` in META.yaml. The walk cycle switches from leg articulation to a body sway (top of the sprite tilts while the base stays planted) — which reads as weight-shifting, not sliding.

## META.yaml (optional, next to the source sprite)

```yaml
signature_action: sparkle   # bow | hat_tilt | sparkle | twinkle | steam
signature_spot: [24, 9]     # x, y of the effect (sparkle/twinkle/steam only)
has_visible_legs: true
```

The signature action is the creature's personality beat: once per idle loop, the wizard's wand sparks, the scholar tilts their hat, the baker's loaf steams. Tiny, but it's the difference between a creature that's alive and a PNG that breathes.

## Other sizes

The row constants at the top of `sprite_animator.py` assume 32x32. For 64x64, double them. The proportions (40% head, 30% torso, 20% legs, feet on the last meaningful row) are the actual contract.
