# Crouching (`move-crouch`)

| family | status | last tested | best result |
|---|---|---|---|
| motion | proven | 2026-09-04 | builder pinned crouch, "lowers across all 192 frames" (§23, §29), grade A- |

**Also called:** crouch, kneel, squat, bend down, lower herself, pick something up from the ground
**Not the same as:**
- [`move-turn-in-place`](turn-in-place.md) - the body turns; here it lowers
- [`move-look-up`](look-up.md) - only the eyes and chin move

## Recipe (v2, 2026-09-04)

A pin on H3 between the standing start frame and a crouched end frame built on the pristine plate, the end figure constrained to the start figure's ground line, x and head width. By words alone she never crouches.

## Checks before picking

- Feet and size fixed; the face score at the end is information, not a fault (the head moves out of the scoring box).

## Progression

### 2026-08-30 · §23 · a crouch by words; then pinned · grade A-
- **Did:** prose on LTX; then a pin.
- **Got:** by prose she never crouched. Pinned: she lowers across all 192 frames and the framing holds (0.0129/s).
- **Learned:** the end state is an edit of the start frame.

### 2026-09-04 · §26, §29 · the end frame regenerated the street; the end figure unconstrained · grade C
- **Did:** a qwen edit for the end frame, "same camera position, same framing, only the pose changes".
- **Got:** qwen moved the car and the lamp post (over half the measured change); she came back a quarter nearer and grew for 3 s before bending.
- **Learned:** end frames on the pristine plate; the end figure pinned to the start figure's ground line, x and head width.

### 2026-09-24 · §95 S5 (corrected) · "crouch unheld" was a lookup, not a measurement · grade n/a
- **Did:** re-examined the face clock's verdict.
- **Got:** the two sampled crouches were unpinned LTX takes; pinned on H3 a crouch is among the best-behaved shots.
- **Learned:** the crouch is pinned on H3 automatically (`film_routes.IN_PLACE`).

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| no crouch | asked in words | pin it | §23 |
| the street shifts during the crouch | a regenerated end frame | end frame on the pristine plate | §26 |
| she grows before bending | the end figure unconstrained | ground line, x, head width | §29 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §23, §26, §29, §43, §56, §95; `studio/shot_catalog.json` (`crouch`).

## Open questions

- A crouch in the shot-script pipeline.
