# Knitted texture in motion (`cloth-knit-texture`)

| family | status | last tested | best result |
|---|---|---|---|
| cloth | works-with-caveats | 2026-09-30 | smallest-gear 050, grade B+ |

**Also called:** knit texture, wool sweater detail, cable knit, fabric texture shifting, hyper-detailed knit
**Not the same as:**
- [`cloth-billow-slow`](billow-slow.md) - a whole garment moving; here the texture's stitches holding while it creases

## Recipe (v1, 2026-09-30)

A macro in which the knit is large, so the stitches are many pixels wide; the creasing in words.

1. Start frame: the knitted cuffs large in frame (smallest-gear 050's macro of four hands).
2. H3 seed 202 was in the cut.
3. Prompt: "The knitted cuffs of their sweaters shift and crease as they move."

## Checks before picking

- The stitch pattern holds (no swimming) through the move.

## Progression

### 2026-09-30 · smallest-gear 050 · cable-knit cuffs over the watch · grade B+
- **Did:** the recipe above.
- **Got:** clear cable knit that creases with the hands.
- **Learned:** texture holds when it is big in frame.

### 2026-09-30 · SHEETS · wool through the upscalers · grade A
- **Did:** SeedVR2 against ESRGAN on character sheets.
- **Got:** SeedVR2 adds real wool and skin detail; ESRGAN looks plastic.
- **Learned:** SeedVR2 for textures.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| (none recorded yet) | | | |

## Evidence

- `studio/samples/fight/smallest-gear/h3_050_s202.mp4`.

## Open questions

- Knit at medium distance (the sweaters in the two-shots) - not measured.
