# Contributing

This is the animation layer extracted from a game project. Contributions are welcome if they follow the design:

1. **Zero AI at runtime.** Every frame is a deterministic pixel transform. If a contribution requires a model call, it belongs in a different tool.
2. **The rig contract is the API.** Sprites follow POSE_TEMPLATE.md. Changes to the rig must be backward-compatible with existing sprites.
3. **Identity preservation.** idle_0 is sacred — it IS the source sprite, untouched. Every other frame derives from it mechanically.

## Adding a new signature action

1. Add the synthesis function to `sprite_animator.py`.
2. Register it in `synthesize_signature_action`.
3. Test it with the demo sprite: `python examples/make_demo_sprite.py && python sprite_animator.py --source examples/acorn_kid/source_idle.png --out /tmp/test --name test`
4. Open a PR with before/after GIFs.
