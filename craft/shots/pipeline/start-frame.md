# Start frames (`pipe-start-frame`)

| family | status | last tested | best result |
|---|---|---|---|
| pipeline | proven | 2026-09-30 | all five films, grade A- |

**Also called:** anchor, start frame, first frame, keyframe, composed frame, compositor
**Not the same as:**
- [`pipe-reference`](reference.md) - the pictures a start frame is composed from
- [`pipe-edit-fix`](edit-fix.md) - repairing a start frame after it is drawn
- [`cont-face-identity`](../continuity/face-identity.md) - keeping the face; decided here
- [`pipe-composite`](composite.md) - pasting a cut-out onto the untouched plate

## Recipe (v2, 2026-09-30)

Draw every shot on both compositors, then pick by eye per shot. Qwen-Image-2.1 keeps identity and costume; Flux 2 keeps framing (macros, ECUs, inserts, ground level, aerials, dives).

1. `fight.py --anchors --compositor best --qseeds 11 202`: Flux 2 ref3 (`workflows/75_flux2_ref3.json`, about 34 s) and two Qwen-Image-2.1 seeds (`workflows/80_qwen21_edit_refs.json`, about 11 s each). Flux 2 needs exactly three references: repeat one.
2. Board the candidates per shot; override with `--anchor-picks 111=flux2,...`. The automatic pick is "highest face score", which is 0.700 by default where there is no face and says nothing.
3. Qwen puts places first (the canvas follows image 1) and renumbers "reference one" to the new order.

## Checks before picking

- Framing as asked; the costume complete; props where they belong; one-sided features single and on the right side.

## Progression

### 2026-08-03 · CINEMATOGRAPHY §0, §1.1, §1.3 · keyframes at 4 steps; similes · grade C
- **Did:** 109 Qwen keyframes at 4 steps.
- **Got:** about 30 missed; a simile was drawn literally (a keyframe got beetles).
- **Learned:** 20 steps at cfg 2.5 for quality; no similes; review keyframes on contact sheets before animating.

### 2026-08-30 · §21 · the builder's compositor · grade A-
- **Did:** a cut-out pasted at a stated scale, relit, re-cut, shadowed, onto the pristine plate.
- **Got:** plate fidelity 0.000-0.007; a qwen full edit gave "a good picture of a DIFFERENT place".
- **Learned:** construct the frame; never let a model redraw the plate.

### 2026-09-24 · §98.1 · three references and an explicit canvas · grade A
- **Did:** Flux 2 with two characters and the place.
- **Got:** workflow 68 read its size off reference one, so a 16:9 frame was impossible from portrait references; 75 adds a third reference and an explicit canvas.
- **Learned:** the canvas must be stated.

### 2026-09-30 · cyber-alchemist · 29 composed start frames · grade A-
- **Did:** the recipe above; twelve overrides of the automatic pick by eye, then three eye edits picked as candidates.
- **Got:** Flux 2 won the eye macro, the hands lifting the vial, the shockwave, the dive, the horizontal fall, the jetpack, the descent aerial and the landing. Qwen won the master, the close-ups (after the eye fix), the POV frames, the slip and the shots in the shaft.
- **Learned:** judge the start frame by eye, per shot.

### 2026-09-30 · quantum-courier · the canvas shape · grade n/a
- **Did:** a shot listing [her, the corridor].
- **Got:** a portrait-shaped frame (the canvas follows image 1) cropped to 16:9.
- **Learned:** places first; `fight.py` was patched.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a macro/insert/ground shot comes back too wide | Qwen ignores framing words | Flux 2 | many |
| a face drifts from the reference | Flux 2 | Qwen | cyber-alchemist 311 |
| two props merged | Qwen | Flux 2 | cyber-alchemist 306 |
| a one-eye feature doubled | Qwen | edit | cyber-alchemist 114, 206, 311 |
| a previz dress ignores the framing | Qwen redraws the composition | use a given start frame (`"start"`) | cyber-alchemist 310 v1 |
| a dress returns the plate's view, not the render's | the plate handed in beside the render (the same place from another angle) | the render alone, words that name nothing ([`pipe-3d-set`](3d-set.md)) | plaza 102-108 |
| a steep look up comes back level | Qwen straightens perspective | draw from the depth alone, or stand the camera back | plaza 104 |

## Evidence

- `studio/samples/fight/cyber-alchemist/anchors.json`; the anchor boards.
- `studio/_tools/fight.py` (`_flux_anchor`, `_qwen_anchor`, `stage_anchors`).

## Open questions

- A framing check that could replace the by-eye pass.
