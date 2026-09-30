# Walk and talk (`dia-walk-and-talk`)

| family | status | last tested | best result |
|---|---|---|---|
| dialogue | partial | 2026-09-05 | builder `walk_and_talk`, same person 0.65 → 0.62 after re-scoring (§56), grade B- |

**Also called:** walk and talk, walking conversation, talking while walking
**Not the same as:**
- [`move-walk-toward-camera`](../motion/walk-toward-camera.md) - the walk without a line
- [`dia-line-on-camera`](line-on-camera.md) - the line standing

## Recipe (v1, 2026-09-05)

Two people walking toward the camera, 4 s, three seeds, cut where the face goes; the line voiced.

## Checks before picking

- Faces at the end; gaps of silence inside the voiced take.

## Progression

### 2026-09-05 · §53-§56 · the walk-and-talk entry · grade B-
- **Did:** built once, then five seeds.
- **Got:** 3 s of silence inside the voiced take; the place drifted 67-83% on some seeds; every seed seemed to redraw the face (0.57 → 0.34) until the ruler was fixed to find the head: 0.65 → 0.63, the same person.
- **Learned:** check the ruler before believing a face failure.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| silence inside the line | the voice pass | check the take's audio | §53 |
| the place drifts | a walk | short takes | §53 |

## Evidence

- `studio/shot_catalog.json` (`walk_and_talk`); `studio/LTX_PLAYBOOK.md` §53-§56.

## Open questions

- None open.
