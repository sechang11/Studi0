# The same costume in every shot (`cont-wardrobe`)

| family | status | last tested | best result |
|---|---|---|---|
| continuity | works-with-caveats | 2026-09-30 | quantum-courier and cyber-alchemist (sheet views + Qwen compositor), grade A- |

**Also called:** wardrobe, costume consistency, same clothes, outfit continuity, costume identical shot to shot
**Not the same as:**
- [`cont-costume-back`](costume-back.md) - specifically the back of the costume
- [`cont-prop-state`](prop-state.md) - an object on the costume changing state
- [`cont-asymmetric-mark`](asymmetric-mark.md) - one detail on one side

## Recipe (v2, 2026-09-30)

In the shot-script pipeline: the costume lives in the character's reference and her sheet's views, handed to the Qwen-Image-2.1 compositor for every shot; the video engine carries it from the start frame. Never describe in the prompt what the reference already carries. In the /film builder (SDXL route): the costume in the weights (a costume LoRA trained on crops where the contact point is the subject) or composited, never asked for.

## Checks before picking

- The costume complete in every start frame (a dramatic Flux 2 light hid the corset in one master candidate).

## Progression

### 2026-08-03 · CINEMATOGRAPHY §2.3, §2.4 · costumes by description across CHRONO · grade C
- **Did:** characters described in words in every keyframe.
- **Got:** Crono lost his blue in 4 of 9 appearances, was barefoot in 5 of 9, and ranged from about 14 to 22 in age; "pale blonde" was read as a value, not a hue.
- **Learned:** the reference carries the costume, not the words.

### 2026-09-06 · §57 · a costume LoRA · grade B
- **Did:** trained on the character in costume; captions describing the pose and the room, never the costume.
- **Got:** the crown identical across 3 framings × 4 seeds with no costume word in the prompt; a costume LoRA trained on generated frames softened the face.
- **Learned:** "Anything that must be identical shot to shot is either in the weights or composited in - never asked for."

### 2026-09-07 · §68-§70 · describing the costume more · grade D
- **Did:** proportion prose, re-captioning, describing corrections.
- **Got:** describing the costume, or correcting the training set, made it worse (a lost strap, a skirt gained).
- **Learned:** "what is in the weights must not be asked for".

### 2026-09-30 · quantum-courier, cyber-alchemist · sheet views in every shot · grade A-
- **Did:** every shot from behind given her back view, every close-up her face view, every other shot her full reference.
- **Got:** the coat, the circuit sleeve, the corset, gauntlets and jetpack held across 38 shots each.
- **Learned:** in the shot-script pipeline the references carry the costume.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the costume re-invented | no costume in the reference | the costume in the reference | §61.2 |
| part of the costume hidden | a start frame's lighting | pick the start frame that shows it | cyber-alchemist 102 |
| the costume drifts with prose | describing what the weights carry | stop describing it | §68-§70 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §19, §56.6, §57, §61.2, §68-§70; `studio/_tools/sheet_refs.py`.

## Open questions

- None open.
