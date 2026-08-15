# Attic - retired generation paths (ARCHITECTURE Phase 3)

One generator now: `studio/_tools/generate.py` (roll - scene - grow - isolate - beats).
These tools did their one-shot jobs and their living behaviour moved:

- `gallery_gen.py` - vary-one-knob corpus builder. The knob-isolation idea lives in
  `generate.py isolate` (per-card clean plates); the 17h22m --loop runaway it caused is
  why roll refuses to start without a time budget. A stale duplicate at
  `studio/gallery_gen.py` was deleted outright.
- `gallery_fill.py` - rendered prompt_recipes.json (task 38, done). The recipes and
  their shape are untouched; rendering any of them again is `generate.py scene` with the
  recipe constraints.
- `flux2_gallery.py` - the FLUX.2 body of work (task 44, done). Its measured lessons
  (quoted-text rule, physical-media verdicts) live in PROMPTING.md and the style cards.
- `make-samples.sh` - pre-library sample seeding; the library grows through
  `generate.py` now.

Kept for the record, not on any path. Nothing imports them.
