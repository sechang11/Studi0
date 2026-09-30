# Compositing a figure into a plate (`pipe-composite`)

| family | status | last tested | best result |
|---|---|---|---|
| pipeline | proven | 2026-09-07 | plate fidelity 0.000-0.007 (§21); a composited end pin 4.6 from the room (§61), grade A |

**Also called:** cut-out compositor, compose.py, paste the figure, figure paste, cut-out, layer, place the character
**Not the same as:**
- [`pipe-start-frame`](start-frame.md) - a model composes the whole frame; here the figure is pasted onto the untouched plate
- [`pipe-edit-fix`](edit-fix.md) - a model repaints part of a picture

## Recipe (v1, 2026-09-07)

The /film builder's route: cut the figure out (SAM 3.1 or BiRefNet), paste it at a stated height at a stated place (depth decides the ground line), relight or tint it part way, add a contact shadow, onto the PRISTINE plate.

1. `studio/_tools/compose.py`: paste at a stated scale; relight on its own canvas; re-cut; a proportion guard (refuse a shape change over a quarter); a geometric shadow wider than the figure and nearly opaque.
2. `figure_paste.py`: SAM 3.1 matte; exposure matched only PART way (a figure lit exactly like the wall disappears into it); foreground objects matted out of the room and put back on top.
3. Anchor a figure on the top-quarter alpha centroid and scale by alpha width; feather the last sixth of any edge the matte reaches; keep the largest component.

## Checks before picking

- The plate unchanged outside the figure; the feet on the ground; the figure's size against the room.

## Progression

### 2026-08-30 · §21, §22 · the compositor · grade A
- **Did:** qwen asked to put the character in the plate; then cut-out, paste, relight, re-cut, shadow, onto the pristine plate; a depth-based stand dial.
- **Got:** qwen gave "a good picture of a DIFFERENT place" (0.187 from the plate); the compositor 0.000-0.007. The first shadows were invisible; the first horizon detector took the sky.
- **Learned:** the plate is never touched by a model.

### 2026-09-06 · §61 · an end pin composited, against edits · grade A
- **Did:** the figure pasted into the room file for an end pin.
- **Got:** 4.6 from the room, against 43.5-62.9 for qwen edits; her face found in 77 of 145 frames against 3 of 145.
- **Learned:** "construct, don't request".

### 2026-09-07 · §78, §93 · placement and mattes · grade B+
- **Did:** placed figures by their bounding box; matted by a named region.
- **Got:** a skull half out of frame; straight matte edges showing as rectangles; a hole where a mask was.
- **Learned:** anchor on the top-quarter alpha centroid; feather edges; keep the largest component.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a different place | a model asked to insert the figure | paste onto the pristine plate | §21 |
| the figure disappears into the wall | exposure matched exactly | match part way | §61 |
| rectangular edges | straight matte edges | feather the last sixth | §78 |

## Evidence

- `studio/_tools/compose.py`; `studio/LTX_PLAYBOOK.md` §21, §22, §27, §61, §78, §93.

## Open questions

- The shot-script pipeline (fight.py) composes with Qwen/Flux 2 instead; a compositor route there is not wired.
