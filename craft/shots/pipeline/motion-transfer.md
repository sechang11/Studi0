# Motion transfer from a driver video (`pipe-motion-transfer`)

| family | status | last tested | best result |
|---|---|---|---|
| pipeline | untested | 2026-09-27 | Wan Animate 2: motion r 0.59-0.63 (§96.5), grade n/a |

**Also called:** motion transfer, animate from video, pose driving, Wan Animate, puppeteering
**Not the same as:**
- [`pipe-previz`](previz.md) - geometry from a Blender scene; here motion from a real video

## Recipe (v0, 2026-09-27)

Wan Animate 2 (`workflows/81_wan_animate2.json`) is wired and has run once; it is not a route yet.

## Checks before picking

- Identity (unmeasured so far) and motion agreement with the driver.

## Progression

### 2026-09-27 · §96.5 · Wan Animate 2, first run · grade n/a
- **Did:** a character driven by a clip.
- **Got:** 65 s for 81 frames at 848x464; motion transferred at r 0.59-0.63; the first wiring cropped the reference's head, so identity is unmeasured.
- **Learned:** it needs a driver whose motion is not mostly camera.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the reference's head cropped | the first wiring | rewire | §96.5 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §96.5; `workflows/81_wan_animate2.json`.

## Open questions

- Everything past the first run.
