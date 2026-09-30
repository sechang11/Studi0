# Push into the head, into POV (`cam-push-into-pov`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | works-with-caveats | 2026-09-30 | quantum-courier 206-207, grade B+ |

**Also called:** push into the back of the head, seamless POV transition, into her eyes, head-to-POV
**Not the same as:**
- [`cam-push-in`](push-in.md) - a push toward a subject that stays outside the camera
- [`pov-walk-run`](../pov/walk-run.md) - the POV shot itself; this is the move that hands over to it

## Recipe (v1, 2026-09-30)

Two shots cut at the moment the back of her head fills the frame: a push toward the back of her head, then a POV shot starting on what she sees.

1. The push: a medium shot from directly behind her (Qwen-Image-2.1 with [her back view from her sheet, the place]), prompt "The camera rushes forward directly into the back of her head until her neon-blue hair fills the whole frame." LTX.
2. The POV: a composed start frame of what she sees, with her own gloved hands reaching forward at the bottom (see [`pov-hands-in-frame`](../pov/hands-in-frame.md)); prompt "the camera bobs with her running stride".
3. Cut on the frame where her hair fills the screen.

## Checks before picking

- The push actually reaches the hair (LTX tends to stop short).
- The POV's hands match her gloves.

## Progression

### 2026-09-30 · quantum-courier 206 → 207 · push into her head, cut to POV · grade B+
- **Did:** the recipe above (LTX s11 both).
- **Got:** it reads as one move into her point of view.
- **Learned:** the transition is made by the cut on a full-frame of hair, not by one generation.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| (none recorded yet) | | | |

## Evidence

- `studio/samples/fight/quantum-courier/shot_206_s11.mp4`, `shot_207_s11.mp4`.

## Open questions

- One generation doing both (a previz of the camera passing through the head) - not tried.
