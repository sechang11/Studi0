# Walking toward the camera (`move-walk-toward-camera`)

| family | status | last tested | best result |
|---|---|---|---|
| motion | works-with-caveats | 2026-09-30 | builder 4 s walk, 2 of 3 seeds kept the face (§55); quantum-courier 104, grade B+ |

**Also called:** walk to camera, walks toward us, approaching, walks in, arriving
**Not the same as:**
- [`move-run`](run.md) - a sprint; the body is blurred and the face matters less
- [`cam-lead-dolly`](../camera/lead-dolly.md) - the camera backing away in front of the walk
- [`dia-walk-and-talk`](../dialogue/walk-and-talk.md) - the same walk with a line spoken

## Recipe (v3, 2026-09-05)

LTX from a composed start frame with her already in place, 4 s, three seeds, cut where the face goes. Never pinned: H3 regenerates the scene for a walk.

1. The start frame places her where the walk BEGINS (a figure the anchor already stands at the steps cannot "walk in", §95).
2. LTX (`workflows/70_ltx25_i2v.json`); three seeds; 4 s, because the face holds about 4 s of a walk.
3. Cut the take where the face is redrawn (`cam.trim_face` in the builder, never below 2 s); prefer the take whose face lasts longest.

## Checks before picking

- The face at the end against the start (walks redraw faces).
- The place behind her (walks drift the scene).

## Progression

### 2026-08-03 · CINEMATOGRAPHY §5 #4, EDITING §5 · entering and leaving frame · grade D
- **Did:** characters asked to enter or leave the frame.
- **Got:** it fails; a walk into frame should run 3.0-3.5 s.
- **Learned:** start with her in frame.

### 2026-09-04 · §29, §34 · walks pinned on H3; walks on LTX · grade D
- **Did:** a qwen end frame "walked closer", pinned on H3 twice (once clamped to 0.6-1.6x of head width on the pristine plate); then the walk on LTX from the composed anchor.
- **Got:** both H3 pins invented willow trees and a grass path from frame 0: H3's own prior, "a tracking shot down a path", took over. On LTX she stayed put while the fog moved; the scene held.
- **Learned:** pin in-place motions; never walks.

### 2026-09-04 · §46 · two people asked to "stand and talk" · grade C
- **Did:** a two-person medium on LTX.
- **Got:** they walked toward the camera unasked: "the LTX law, not the picture".
- **Learned:** LTX walks people toward the lens.

### 2026-09-05 · §53-§55 · the face clock on walks · grade B
- **Did:** the walk-to-camera entry; a seed dance; a nine-point face clock; 6 s against 4 s.
- **Got:** every seed redrew the face on the way in (0.57 → 0.34); by eye, 3 of 3 "different face" verdicts were right. The face crossed at 3.7, 4.5 and 4.5 s of 6 s takes. At 6 s, 0 of 3 kept the face; at 4 s, 2 of 3 did. Over 17 walk takes three quarters held 4.0 s; stills hold 4.8 s.
- **Learned:** "The shot was made shorter than the failure." LTX loses faces at about 5 s in general.

### 2026-09-30 · quantum-courier 104; cyber-alchemist 312 · walking toward and away from the camera · grade B+
- **Did:** 104: a low-angle start frame of her mid-stride, 4 s (LTX seed 202). 312: she walks away into the haze, 5 s (LTX seed 11).
- **Got:** both read; the walk away hides the face problem by construction.
- **Learned:** short walks toward; walks away are safe.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a path and trees appear from nowhere | a walk pinned on H3 | LTX, never pin a walk | §29 |
| a different face by the end | the engine redraws the face on the way in | 4 s; three seeds; cut at the face | §53-§55 |
| people walk who were told to stand | LTX's prior | say what they do in place; keep it short | §46 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §29, §34, §46, §53-§56; `studio/shot_catalog.json` (`walk_to_camera`, `held_four`).

## Open questions

- Pinning only the END frame of a walk (suggested in §54, not tried).
