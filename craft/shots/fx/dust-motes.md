# Dust motes in a light beam (`fx-dust-motes`)

| family | status | last tested | best result |
|---|---|---|---|
| fx | partial | 2026-09-30 | smallest-gear 010-030, grade C |

**Also called:** dust in a sunbeam, floating dust, motes, god rays with dust, particles in light
**Not the same as:**
- [`fx-zero-g-droplets`](zero-g-droplets.md) - liquid rising without gravity; motes drift under normal gravity
- [`fx-smoke-steam-drift`](smoke-steam-drift.md) - a continuous haze; motes are separate specks

## Recipe (v1, 2026-09-30)

Not solved. What the one attempt says: the motes have to be large, few and backlit IN THE START FRAME, or they vanish at delivery size.

1. Start frame: a dark background behind a hard shaft of light, with visible specks inside it.
2. A tighter framing, so a speck is several pixels wide.

## Checks before picking

- Watch the take at delivery size (1280x704): can you see a speck?

## Progression

### 2026-07-30 · CINEMATOGRAPHY §5b · dust as an ambient mover · grade B
- **Did:** dust among the ambient movers of CHRONO.
- **Got:** three or four ambient movers are safe.
- **Learned:** motes work as MOTION; they are not a feature that reads at delivery size.

### 2026-09-30 · smallest-gear 010-030 · dust motes in a shaft of sunlight landing on gears · grade C
- **Did:** the motes in the prompts only: 010 "dust motes drift slowly through the shaft of golden sunlight" (LTX seed 202), 030 "Dust motes drift down through the shaft of sunlight and settle softly on the tiny still gears" (H3 seed 11). The start frames did not draw them.
- **Got:** warm sunlight and haze read; the motes do not, at delivery size.
- **Learned:** particles must be designed into the start frame, large and backlit.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| no visible motes | specks below a pixel at delivery size | fewer, larger, backlit; a tighter frame | smallest-gear |

## Evidence

- `challenge-films-2026-09-30/smallest-gear_final.mp4` (local deliverables).

## Open questions

- Everything; a second attempt following the recipe.
