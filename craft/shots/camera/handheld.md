# Handheld (`cam-handheld`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | works-with-caveats | 2026-09-30 | cyber-alchemist 208-210, grade B+ |

**Also called:** handheld, shaky cam, camera shake, documentary camera, chaotic camera
**Not the same as:**
- [`cam-locked-off`](locked-off.md) - no movement at all
- [`pov-walk-run`](../pov/walk-run.md) - the shake of her own stride, seen through her eyes
- [`pov-drift`](../pov/drift.md) - a slow subjective glide through a place, nobody in it

## Recipe (v1, 2026-09-30)

In a POV, "Handheld, chaotic" in the words carries on LTX; a post shake in the builder measured as static. An unwanted handheld drift in a pin means the background was regenerated.

## Checks before picking

- The shake reads as a person holding the camera, not as the room wobbling.

## Progression

### 2026-08-30 · §23, §26 · a "slight handheld drift" in pinned shots · grade C
- **Did:** H3 pins whose end frame was a qwen edit of the start.
- **Got:** the drift was H3 interpolating a background qwen had regenerated.
- **Learned:** build end frames on the pristine plate.

### 2026-09-05 · §53 · the handheld entry as a post shake · grade C
- **Did:** built once.
- **Got:** the camera measured "static".
- **Learned:** the post shake is too small to register.

### 2026-09-07 · §95.2, §96.9 · handheld micro-motion for photoreal · grade n/a
- **Did:** the method adopted the breakdown's "handheld for photoreal".
- **Got:** adopted as "a faint float for photoreal"; §98.9 (2026-09-24): "holds; the camera is measured against the ask on every take".
- **Learned:** a faint float, measured.

### 2026-09-30 · cyber-alchemist 208-210 · handheld in the helmet POV · grade B+
- **Did:** "Handheld, chaotic" in the prompts.
- **Got:** a live, shaky POV; the fast tilt blurred.
- **Learned:** in a POV the engines deliver handheld.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the room wobbles in a pinned shot | a regenerated background | end frame on the pristine plate | §26 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §23, §26, §53; `studio/samples/fight/cyber-alchemist/shot_209_s11.mp4`.

## Open questions

- None open.
