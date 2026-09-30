# The back of the costume (`cont-costume-back`)

| family | status | last tested | best result |
|---|---|---|---|
| continuity | works-with-caveats | 2026-09-30 | cyber-alchemist orbit and 211, grade A- |

**Also called:** back view, the back of the coat, costume from behind, rear view, back of the character
**Not the same as:**
- [`cont-prop-state`](prop-state.md) - an object on the costume changing state (helmet on, jetpack open); here the costume's own back
- [`frame-over-the-shoulder`](../framing/over-the-shoulder.md) - a framing that shows part of the back; this entry is about what the back looks like
- [`cont-wardrobe`](wardrobe.md) - the whole costume the same in every shot

## Recipe (v1, 2026-09-30)

Hand every shot from behind the back view from her own character sheet, as a reference.

1. `studio/_tools/sheet_refs.py` makes `ref_<who>_back.png` from the sheet's `turn_back` view (a cast entry `"sheet_view": [who, "turn_back"]`).
2. Every shot from behind lists it in its references.
3. For a moving back (an orbit), give the previz her real shape so the jetpack and the cape have depth.

## Checks before picking

- The back matches the sheet: jetpack, the side the cape hangs on, the braid.
- The compositor did not move a front object to the back (the helmet drawn on her back).

## Progression

### 2026-09-05 · §51 · relighting a back view · grade D
- **Did:** qwen asked to relight a back view "without changing the face".
- **Got:** it gave the back a face.
- **Learned:** never relight a back view; tint it.

### 2026-09-30 · quantum-courier · Maya from behind, 107 and 206 · grade A-
- **Did:** `maya_back` from her sheet in every shot from behind.
- **Got:** her hair and coat held from behind.
- **Learned:** as above.

### 2026-09-30 · cyber-alchemist 211, 212, orbit · the back with a jetpack and a one-sided cape · grade A-
- **Did:** `alch_back` in 211, 212, 301, 306; her mesh in the orbit.
- **Got:** jetpack and cape held; in the orbit her back is darker than her front.
- **Learned:** light the back (see [`cam-orbit-360`](../camera/orbit-360.md)).

### 2026-09-30 · SHEETS · backs made from a picture · grade A-
- **Did:** the figure cut out onto grey and turned by the angles LoRA; the old IPAdapter anime route.
- **Got:** the cut-out route held the coat and boots all round; the IPAdapter route turned one character's back to camera and changed another's species. Checks: colour 0.71-0.93 same character against 0.00-0.01 different (flag under 0.55).
- **Learned:** turn a cut-out; check the colours.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the helmet drawn on her back | the compositor merged two brass objects | Flux 2 start frame | cyber-alchemist 306 Qwen |

## Evidence

- `studio/samples/fight/quantum-courier/ref_maya_back.png`; `studio/samples/fight/cyber-alchemist/ref_alch_back.png`.
- `studio/_tools/sheet_refs.py`.

## Open questions

- None open.
