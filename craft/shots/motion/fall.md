# Falling (`move-fall`)

| family | status | last tested | best result |
|---|---|---|---|
| motion | proven | 2026-09-30 | cyber-alchemist 212, 301, grade A- |

**Also called:** fall, drop, free fall, stepping off, plunging, dropping away
**Not the same as:**
- [`move-hover-flight`](hover-flight.md) - held up in the air, or flying under control
- [`move-run`](run.md) - on the ground

## Recipe (v1, 2026-09-30)

A start frame at the moment of release with the drop visible below; LTX for the release, H3 for the fall at speed.

1. 212: "a HIGH ANGLE SHOT looking down the colossal shaft past the woman ... as she lets go of the railing and falls forward" (LTX seed 11).
2. 301: Flux 2 start frame of the head-first dive; H3.
3. 303 (Courier): "She steps calmly off the edge into the air. The camera holds still as she drops out of the bottom of the frame."

## Checks before picking

- The direction of the fall stays down; the view does not flip.

## Progression

### 2026-07-29 · EDITING §6 · a fall, then its impact · grade B
- **Did:** two shots, the second continuing from the first's last frame (`from_prev`).
- **Got:** the impact follows the fall without a jump.
- **Learned:** chain the impact onto the fall.

### 2026-09-07 · §75 · a fall built from two photographs (fx_fall) · grade B
- **Did:** the fall composited inside a 1.8x oversize.
- **Got:** the settle cropped the middle 55% while the next shot opened on the whole plate: a jump. Fixed by widening the crop through the settle so the last frame IS the plate.
- **Learned:** a built fall must land on the next shot's first frame, pixel for pixel.

### 2026-09-30 · cyber-alchemist 212, 301; quantum-courier 303 · letting go; the dive; stepping off · grade A-
- **Did:** the recipe above.
- **Got:** 212: the camera tips down after her as she shrinks into the lights. 301 (H3 seed 11): the camera follows her down. LTX seed 11 of 301 flipped to a view from below.
- **Learned:** H3 holds a fall at speed.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the view flips mid-fall | LTX reinterprets the fall | H3 | cyber-alchemist 301 LTX |
| a jump at the landing cut | the built fall's crop did not end on the plate | widen the crop through the settle | §75 |

## Evidence

- `studio/samples/fight/cyber-alchemist/shot_212_s11.mp4`, `h3_301_s11.mp4`; `studio/LTX_PLAYBOOK.md` §75, §79, §91.

## Open questions

- None open.
