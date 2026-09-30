# Close-up of a face (`frame-close-up-face`)

| family | status | last tested | best result |
|---|---|---|---|
| framing | works-with-caveats | 2026-09-30 | cyber-alchemist 311, grade A- |

**Also called:** close-up, CU, face shot, head and shoulders, portrait shot
**Not the same as:**
- [`frame-medium`](medium.md) - from the waist up; the face is small
- [`frame-ecu-eye`](ecu-eye.md) - one eye fills the frame

## Recipe (v1, 2026-09-30)

Qwen-Image-2.1 from [her face view from the sheet, her reference, place]; then check both eyes; LTX; one small action.

1. Start frame: Qwen with the three-quarter face from her sheet (`"sheet_view": [who, "face_front_r"]`).
2. Check the eyes and any one-sided feature; fix with an edit (see [`cont-asymmetric-mark`](../continuity/asymmetric-mark.md)).
3. LTX; one small action ("she looks up", "a slow smile"); static camera.

## Checks before picking

- The face against its start frame (`take_rank.py` fault under 0.60).
- One-sided features on the right side and single.
- The face does not swell toward the lens as the take goes on.

## Progression

### 2026-08-03 · CINEMATOGRAPHY §5 · small face actions · grade C
- **Did:** micro-actions on faces across a film.
- **Got:** each one asks the model to "invent identity" again.
- **Learned:** keep faces still; move hair, cloth and light.

### 2026-09-04 · §46 · compose the close-up; do not zoom to it · grade A-
- **Did:** a close-up built as a whole figure at a near stand, then as a composed close-up from the portrait view.
- **Got:** the zoomed version lost 71% of its picture; the composed one had the face large and sharp from frame one, the same face at the end, in 18 s.
- **Learned:** a close-up is composed, not zoomed.

### 2026-09-04 · §47 · "turns toward the sound" in a close-up · grade D
- **Did:** a head turn in words.
- **Got:** at 1 s he turned; 4 s of the back of his head.
- **Learned:** "glances", "looks up", "listens" - never "turns".

### 2026-09-05 · §55 · which framings keep the face · grade A
- **Did:** the face clock over 119 takes.
- **Got:** close-ups kept the face 17 of 19 (89%).
- **Learned:** the bigger the head, the longer it lasts.

### 2026-09-20 · §96.5 · H3 against LTX on a held close-up · grade n/a
- **Did:** the same start frame on both.
- **Got:** H3 keeps frame 0 (SSIM 0.962 against 0.289) and returns -27 dB where LTX returns -56 dB.
- **Learned:** a held close-up that must sound goes to H3.

### 2026-09-30 · cyber-alchemist 114, 206, 311 · her close-ups · grade A-
- **Did:** Qwen start frames; the compositor gave her two silver eyes; edits restored the brown right eye (114 seed 41, 206 seed 42, 311 seed 42).
- **Got:** the fixed frames scored higher on identity (114 0.525 → 0.566). 206 LTX seed 11 pushed in on a growing flare from the silver eye; seed 202 had both eyes glowing and was not used.
- **Learned:** check both eyes in every close-up start frame.

### 2026-09-30 · storm-sonata 050; quantum-courier 110 · faces in rain · grade B+
- **Did:** close-ups from the sheet's face view.
- **Got:** the pianist's soaked face held; the Courier's 110 was flagged for drift (0.57) as she glances back.
- **Learned:** a head turn in a close-up drifts; keep close-ups still.

### 2026-09-30 · SHEETS · a face close-up asked of an edit model · grade D
- **Did:** framing words ("close-up") in edit prompts.
- **Got:** full length came back 23 of 24 times.
- **Learned:** crop the face from the full figure and restore it (SeedVR2 x4 took a 271 px crop to 1084 px and kept the scar).

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| two silver eyes | the compositor spreads a one-eye feature | edit, pick as a candidate | cyber-alchemist 114, 206, 311 |
| drift on a head turn | the face redrawn as it turns | keep close-ups still; separate the turn | quantum-courier 110 |
| a different woman | a Flux 2 face | Qwen for faces | cyber-alchemist 311 Flux candidate |
| the back of the head for most of the take | "turns toward" | "glances" | §47 |
| near silence | an LTX close-up | H3, or the scene's bed | §46, §96.5 |

## Evidence

- `studio/samples/fight/cyber-alchemist/anchor_311_eyefix_s42.png`, `shot_311_s11.mp4`.

## Open questions

- None open.
