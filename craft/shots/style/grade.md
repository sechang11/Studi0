# The film's grade (`style-grade`)

| family | status | last tested | best result |
|---|---|---|---|
| style | proven | 2026-10-05 | "filmic", one grade after the cuts (all five challenge films), grade A- |

**Also called:** grade, color grade, look, LUT, night look, filmic
**Not the same as:**
- [`style-photoreal`](photoreal.md) - what the references and start frames look like
- [`master-upscale`](master-upscale.md) - resolution, not colour

## Recipe (v1, 2026-09-07)

One grade after the cuts (`fight.py --finish`, "filmic": +11% saturation, +20% brightness). Never the `night` look: it crushes dark inserts to black; use moonlit, noir or cold.

## Checks before picking

- The darkest shots keep detail after the grade.

## Progression

### 2026-08-08 · VIDEO_RULES PICTURE-05 · the night look · grade F
- **Did:** the `night` grade.
- **Got:** luma 48 → 0 and 64 → 1: dark inserts came back pure black.
- **Learned:** banned (`roll.py` checks it).

### 2026-09-07 · §96.8 · one grade after the cuts · grade A-
- **Did:** the finish grades the assembled film once.
- **Got:** the filmic look: +11% saturation, +20% brightness.
- **Learned:** grade once, after the cut.

### 2026-10-05 · the fire esper · a grade per shot, by the place's state (an option) · grade n/a
- **Did:** `grade` 'by place' (shot_options.py): each shot graded in the cut by its place_state - dusk, ember (red), fire (burning), ash (volcanic) - all on the filmic base.
- **Got:** each act has its colour; dissolves carry one look into the next.
- **Learned:** a per-shot grade is an option; the film's one grade stays the default.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| dark shots go black | the night look | moonlit, noir or cold | PICTURE-05 |

## Evidence

- `craft/VIDEO_RULES.md` (PICTURE-05); `studio/LTX_PLAYBOOK.md` §96.8; `studio/_tools/post.py`.

## Open questions

- A grade per scene rather than per film.
