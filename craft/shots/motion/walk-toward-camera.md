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

### 2026-09-30 · the jester in the wood 302 · a walk the camera tracks back from, pinned between a set's frames · grade B+
- **Did:** her walk toward a camera that tracks back at her pace, drawn between the set's first and last frames (her placed in both by the set, [`pipe-3d-set`](../pipeline/3d-set.md)) on H3 (`65`) and LTX-2.5 (`72`), against the old take on a puppet's depth and LTX-2.5 from the start frame alone; two seeds each.
- **Got:** pinned, real alternating steps, her glances left and right, the costume held - H3 2 of 2, LTX-2.5 2 of 2 (her hair flared on one). On the puppet's depth, a shuffle with one leg splayed. From the start frame alone LTX-2.5 pushed in to her waist on both seeds instead of tracking back.
- **Learned:** a walk the camera travels with holds on a pin: she is the same size in both frames (the 2026-09-04 failures pinned walks whose figure grew between the frames).

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the camera pushes in on her instead of tracking back | LTX-2.5 from a start frame alone, the move in words | pin the end frame too (`72`, or H3 `65`) | forest 302, 2 of 2 |
| a path and trees appear from nowhere | a walk pinned on H3, the figure growing between the frames | LTX; or move the camera with her - a walk the camera travels with holds on a pin (§99.10) | §29 |
| a different face by the end | the engine redraws the face on the way in | 4 s; three seeds; cut at the face | §53-§55 |
| people walk who were told to stand | LTX's prior | say what they do in place; keep it short | §46 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §29, §34, §46, §53-§56; `studio/shot_catalog.json` (`walk_to_camera`, `held_four`).

## Open questions

- Pinning only the END frame of a walk (suggested in §54, not tried).
