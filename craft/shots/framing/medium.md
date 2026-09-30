# Medium shot (`frame-medium`)

| family | status | last tested | best result |
|---|---|---|---|
| framing | proven | 2026-09-30 | cyber-alchemist 102, grade A- |

**Also called:** medium shot, mid shot, waist-up shot, the master (at medium distance), knee-up shot, medium single
**Not the same as:**
- [`frame-wide-with-figure`](wide-with-figure.md) - the whole figure small in the place
- [`frame-close-up-face`](close-up-face.md) - the face fills the frame

## Recipe (v1, 2026-09-30)

Qwen-Image-2.1 from [character, character, place]; LTX. The compositor drew it a little wider than asked (knees up); that is the right master for an orbit.

1. Start frame: "a MEDIUM SHOT of the woman of reference one standing in the dark stone workshop of reference three", the lighting named.
2. Two Qwen seeds and one Flux 2 (`fight.py --anchors --compositor best`); Qwen kept the costume, Flux 2 the lighting.
3. LTX; "She stands completely still ... The camera is locked off".

## Checks before picking

- The costume is complete (corset, coat, gauntlets): Flux 2's version hid the corset.

## Progression

### 2026-08-30 · §24 · a medium then a close-up in one generation · grade A-
- **Did:** a two-beat shot on a composite start frame.
- **Got:** "it is her in both"; on a plate-only start frame the close-up was a different woman.
- **Learned:** the character must be in the start frame.

### 2026-09-05 · §55 · the same medium at 4 s and 7 s · grade B+
- **Did:** four seeds each.
- **Got:** 3 of 4 kept the face at 4 s; 1 of 4 at 7 s. The one 4 s failure started from a composed face of 0.45 against about 0.67 for its siblings.
- **Learned:** "a shot that begins badly does not recover"; ask for less than 5 s.

### 2026-09-30 · cyber-alchemist 102 · the master · grade A-
- **Did:** the recipe above.
- **Got:** Qwen seed 202 picked (face score 0.585 vs Flux 2 0.464); Flux 2 had the better Rembrandt light but hid the corset.
- **Learned:** for a master that must show a costume, choose the costume over the light.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the costume hidden by dramatic light | Flux 2's lighting | Qwen for costume masters | cyber-alchemist 102 Flux candidate |

## Evidence

- `studio/samples/fight/cyber-alchemist/anchor_102_qwen21_s202.png`, `shot_102_s11.mp4`.

## Open questions

- None open.
