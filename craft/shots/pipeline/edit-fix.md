# Fixing a picture by edit (`pipe-edit-fix`)

| family | status | last tested | best result |
|---|---|---|---|
| pipeline | proven | 2026-09-30 | cyber-alchemist eye fixes, grade A- |

**Also called:** edit fix, image edit, Qwen edit, repaint a detail, fix the reference
**Not the same as:**
- [`pipe-start-frame`](start-frame.md) - composing a start frame from references
- [`pipe-reference`](reference.md) - drawing the references
- [`cont-asymmetric-mark`](../continuity/asymmetric-mark.md) - the most common thing an edit fixes
- [`pipe-composite`](composite.md) - construct instead of asking an edit

## Recipe (v1, 2026-09-30)

`studio/sheets.py` `edit(images, prompt, seed, angles=0, dest, tag)` (Qwen-Image-Edit-2511 without the angles LoRA; 6-14 s), three seeds, a board beside the original, pick by eye.

1. Name sides in picture terms ("on the right side of the picture (her left arm)").
2. Ask for the plain result, not hardware ("a normal open human eye ... only the iris is different").
3. End with what must not change ("Keep everything else exactly the same: ...").
4. Save a fixed start frame as a candidate `anchor_<id>_<name>.png` and choose it with `fight.py --anchor-picks <id>=<name>`, so the record keeps it.

## Checks before picking

- Only the named thing changed (compare side by side, zoomed).

## Progression

### 2026-09-04 · §26, §29 · an edit regenerates what it was told to keep · grade C
- **Did:** "same camera position, same framing, only the pose changes".
- **Got:** the car and the lamp post moved; she came back a quarter nearer.
- **Learned:** constrain and composite; never trust an edit to keep the background.

### 2026-09-06 · §61.2 · asking an edit for "closer" · grade D
- **Did:** "closer, costume from image 3".
- **Got:** the room re-framed (62.9 from the room; composited: 4.6).
- **Learned:** "asking for her CLOSER is an instruction about framing, and framing is the room".

### 2026-09-30 · quantum-courier · moving the circuit to the left sleeve · grade A-
- **Did:** three seeds; seed 21.
- **Got:** fixed; everything redrawn from the fixed reference.
- **Learned:** as above.

### 2026-09-30 · cyber-alchemist · the eye, twice; the close-ups' second silver eye · grade A-
- **Did:** round 1 "a glowing silver cybernetic iris made of fine concentric mechanical rings" (seeds 21-23): lens discs over the eye. Round 2 "a normal open human eye ... only the iris ... shining metallic silver" (seeds 31-34): seed 32. Then the close-ups (seeds 41, 42).
- **Got:** her own eye with a silver iris; the close-ups fixed and scoring higher.
- **Learned:** technical words make the model add hardware.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| hardware drawn over the feature | "cybernetic", "mechanical" in the ask | describe the plain result | cyber-alchemist round 1 |

## Evidence

- `studio/samples/fight/cyber-alchemist/_alch_eye_s21.png` ... `_alch_eye2_s34.png`, `anchor_*_eyefix_*.png`.

## Open questions

- None open.
