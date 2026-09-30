# Crash zoom (`cam-crash-zoom`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | proven | 2026-09-05 | builder mass ease 1.364 for 1.34 (§55), grade A- |

**Also called:** crash zoom, snap zoom, fast zoom, punch in
**Not the same as:**
- [`cam-push-in`](push-in.md) - slow, and the camera travels
- [`cam-dolly-zoom`](dolly-zoom.md) - lens and distance change together; the subject holds

## Recipe (v1, 2026-09-05)

**/film builder:** the crash-zoom mass ease in `postmove` (a critically damped second-order move with a settle). Not tried in the shot-script pipeline.

## Checks before picking

- The zoom's peak and settle against the ask.

## Progression

### 2026-09-05 · §55 · crash zoom as a mass ease · grade A-
- **Did:** asked 1.34.
- **Got:** the solver curve peaked at 1.393 and measured 1.364 before settling; one of four eases with worst step error 0.026.
- **Learned:** a move with mass reads as a camera, not a scale.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| (none recorded yet) | | | |

## Evidence

- `studio/LTX_PLAYBOOK.md` §55.

## Open questions

- The shot-script pipeline has no post-move stage.
