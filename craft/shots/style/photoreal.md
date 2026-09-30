# Photoreal (`style-photoreal`)

| family | status | last tested | best result |
|---|---|---|---|
| style | proven | 2026-09-30 | storm-sonata; cyber-alchemist, grade A- |

**Also called:** photoreal, live action, cinematic realism, realistic, hyper-realistic
**Not the same as:**
- [`style-stop-motion`](stop-motion.md) - puppets
- [`master-upscale`](master-upscale.md) - the 2x master that follows
- [`style-grade`](grade.md) - the colour of the whole film

## Recipe (v1, 2026-09-30)

References on Flux 2 (`--cast-engine flux2`) with a realism suffix ("Unretouched photograph, available light, visible skin texture and pores, fine film grain, shallow depth of field, no retouching, no gloss"); start frames "A still frame from a live-action film, ..."; a film grade line appended to each.

## Checks before picking

- Faces by score (`take_rank.py`), then by eye.

## Progression

### 2026-08-05 · CURRENT_PRACTICE · steering Qwen away from photography · grade n/a
- **Did:** prompt and CFG changes.
- **Got:** Qwen cannot be steered off photography by prompt at any CFG; a LoRA can.
- **Learned:** photoreal is Qwen's home.

### 2026-09-04 · §30, §43 · the photographic prior · grade C
- **Did:** full-length photographic renders.
- **Got:** Mara's prior is "a three-quarter portrait, whatever the sentence"; four seeds stayed cropped.
- **Learned:** "a seed does not move a composition prior; words do".

### 2026-09-07 · §72, §81 · a brief that fights realism · grade B
- **Did:** "a wiry woman in her late twenties".
- **Got:** she came back fifty; restated as bone structure and muscle, twenty-eight.
- **Learned:** spell the brief as anatomy.

### 2026-09-24 · ACTION_SEQUENCE · the realism clause · grade B
- **Did:** references with and without a realism clause.
- **Got:** without it: an "airbrushed poster".
- **Learned:** a realism suffix on every reference.

### 2026-09-30 · storm-sonata, quantum-courier, cyber-alchemist · three photoreal films · grade A-
- **Did:** the recipe above.
- **Got:** photoreal throughout.
- **Learned:** the realism suffix on the references carries into every shot.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| (none recorded in these films) | | | |

## Evidence

- `studio/shotscripts/_make_cyber_alchemist_0930.py` (`REAL`, the grade lines).

## Open questions

- None open.
