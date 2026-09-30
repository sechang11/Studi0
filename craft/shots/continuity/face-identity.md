# The same face across the film (`cont-face-identity`)

| family | status | last tested | best result |
|---|---|---|---|
| continuity | works-with-caveats | 2026-09-30 | cyber-alchemist 310-311, grade A- |

**Also called:** identity, same face, face consistency, identity identical to shot 1, facial identity, likeness, held four, four seconds and the face holds
**Not the same as:**
- [`cont-asymmetric-mark`](asymmetric-mark.md) - a single feature's side and count; here the whole face
- [`pipe-start-frame`](../pipeline/start-frame.md) - where identity is decided; this entry says how to keep and check it
- [`cont-cast-count`](cast-count.md) - how many faces one frame can keep

## Recipe (v1, 2026-09-30)

Identity is decided in the start frame: compose faces with Qwen-Image-2.1 from her reference and her sheet's three-quarter face, and end a film's identity check on a composed frame.

1. Faces: Qwen-Image-2.1 compositor (`workflows/80_qwen21_edit_refs.json`) with [her face view from the sheet, her full reference, place]. Flux 2 faces drifted.
2. A move that must END on her face ends on a composed frame: draw it backwards from that frame and reverse (cyber-alchemist 310), or first-last onto it.
3. Pick takes by face score where the face is photoreal; by eye for drawn faces (anime, puppets), where the scorer is blind.

## Checks before picking

- The take's face against its own start frame: `take_rank.py` faults a take under 0.60 (`FACE_FAULT`); the same face reads 0.75-0.89.
- The last face of the film against the first.

## Progression

### 2026-08-03 · CINEMATOGRAPHY §2.2, §2.5 · identity by description · grade C
- **Did:** characters held by words across 109 keyframes.
- **Got:** word order lost one character's gender; a creature gained a cyclops eye in 3 of 5 shots.
- **Learned:** order the description; hold identity with pictures.

### 2026-08-30 · §24 · identity across an internal cut · grade A-
- **Did:** a two-beat shot on a composite start frame and on a plate-only one.
- **Got:** composite: the same face after the transition; plate-only: a different woman.
- **Learned:** the character must be in the start frame.

### 2026-09-05 · §50, §55 · the identity ruler and the face clock · grade n/a
- **Did:** a CLIP-ViT-H ruler across 14 packs; a nine-point clock over 119 takes.
- **Got:** 0.62+ same person, 0.50-0.62 uncertain, under 0.50 different (bands depend on framing: close 0.74-0.78, wide 0.56-0.72). The face holds about 4.3-4.8 s of a still, 4.0 s of a walk; kept in 89% of close-ups, 66% of wides, 17% of full-length shots.
- **Learned:** "the place and the face fail together": the remedy is the plate or the length, never another seed.

### 2026-09-06 · §58 · a face swap on every frame · grade B+
- **Did:** inswapper in aligned face space, with a FOLDER of photos as the source.
- **Got:** pose, expression and blink stay with the frame; detailing after the swap dropped it from 0.870 to 0.694.
- **Learned:** "The swap is the identity"; never detail after it; swap the mastered take before effects.

### 2026-09-07 · §67 · the swap's score was circular · grade n/a
- **Did:** leave-one-out on her own 45 photos.
- **Got:** 0.611 mean; the swap's 0.87 was above her own best (0.811).
- **Learned:** "where the number and the person who knows the subject disagree, the person wins".

### 2026-09-07 · §95.3 · sharpening the start frame · grade D
- **Did:** the start frame through the 2x master.
- **Got:** first-frame identity dropped 3 of 3 times (-0.038, -0.070, -0.029).
- **Learned:** "Detail is not what the video model wants".

### 2026-09-24 · §97.1, §97.3, §98.5b · ID-LoRA, ref2va, and what to score against · grade n/a
- **Did:** the LTX-2.3 ID-LoRA; H3 ref2va wired correctly; faces across the fight sequence.
- **Got:** the ID-LoRA carried the voice (0.816), not the face; ref2va carried face and wardrobe but doubled the person in 2 of 4; against the neutral cast reference faces read 0.22-0.33, against their own start frames 0.83-0.93.
- **Learned:** score against the shot's own start frame.

### 2026-09-29 · §0.3 · Qwen-Image-2.1 as the compositor · grade A-
- **Did:** Qwen-Image-2.1 against Flux 2 ref3.
- **Got:** 19 of 20 face-scored shots (+0.108).
- **Learned:** the default for faces.

### 2026-09-30 · quantum-courier · one face in 38 shots · grade B
- **Did:** every shot composed from her reference and sheet views.
- **Got:** held overall; the ranker flagged drift in 110 (0.57), 111 (0.41), 202 (0.50), 308 (0.53), all picked as "fewest faults".
- **Learned:** motion shots drift most (a run, a turn); keep close-ups still.

### 2026-09-30 · cyber-alchemist 310-311 · pan up to her face, identical to shot 1 · grade A-
- **Did:** the tilt drawn DOWN from 311's start frame and reversed, so it lands on a frame composed from her references.
- **Got:** her face at the end of the move is the composed face.
- **Learned:** end on a composed frame instead of trusting the engine to invent the face on the way.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a different woman at the end of a long move | drift over hops or over a long take | end on a composed frame | cyber-alchemist orbit seed 303 |
| Flux 2 faces drift from the reference | Flux 2 composes faces less faithfully | Qwen for faces | cyber-alchemist 311 Flux candidate |
| the scorer says nothing | drawn faces (anime, puppets) | pick by eye | system-error, smallest-gear |

## Evidence

- `studio/samples/fight/quantum-courier/ranked.json`; `studio/samples/fight/cyber-alchemist/anchors.json`.
- `studio/_tools/take_rank.py`.

## Open questions

- A face-drift fault for drawn faces.
