# Barrel roll (`cam-roll`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | works-with-caveats | 2026-09-30 | quantum-courier 312, grade B+ |

**Also called:** barrel roll, camera spin, roll with the subject, spinning camera
**Not the same as:**
- [`cam-orbit-360`](orbit-360.md) - an orbit travels round the subject; a roll spins about the lens's own axis
- [`cam-dutch-tilt`](dutch-tilt.md) - a fixed canted frame; a roll keeps turning

## Recipe (v1, 2026-09-30)

H3 image-to-video from a composed flight frame, with the roll and the motion blur in words.

1. Start frame: her in flight, framed tight.
2. H3 (`workflows/67_minimax_h3_i2v_sparse.json` via `fight.py --h3`); the prompt says the camera spins with her and the blur is violent.
3. Cut out of the blur into the next shot (a match cut on the spin: [`trans-match-cut`](../transitions/match-cut.md)).

## Checks before picking

- The spin is visible (the horizon turns), not only blur.
- She is the same person when the spin stabilises.

## Progression

### 2026-09-30 · quantum-courier 312 · barrel roll on H3 · grade B+
- **Did:** the recipe above, H3 seed 11.
- **Got:** a violent spin with motion blur; cut out of it into the pull-back.
- **Learned:** H3 carries a roll asked for in words; LTX was not in the cut for this shot.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| (none recorded yet) | | | |

## Evidence

- `studio/samples/fight/quantum-courier/h3_312_s11.mp4`.

## Open questions

- Whether LTX can do it; whether a previz roll is steadier.
