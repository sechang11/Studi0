# Shot / reverse shot (`frame-shot-reverse`)

| family | status | last tested | best result |
|---|---|---|---|
| framing | partial | 2026-09-05 | builder `matched_angles`: angles within 0.08 of each other, the camera ran away 39% (§55), grade C+ |

**Also called:** shot reverse shot, reverse angle, matched angles, conversation coverage, eyeline match
**Not the same as:**
- [`frame-over-the-shoulder`](over-the-shoulder.md) - one of the pair, with the listener's shoulder in frame
- [`frame-two-shot`](two-shot.md) - both people in one frame

## Recipe (v1, 2026-09-05)

The builder performs matching angles on the two plates (keystone, measured); the eyeline cannot be promised.

## Checks before picking

- Both sides at the same angle; the eyelines meet (by eye).

## Progression

### 2026-09-05 · §55 · matched angles · grade C+
- **Did:** two mediums from matched low angles.
- **Got:** the angles delivered to 0.04 and within 0.08 of each other; the camera ran away (39% push) and the place drifted.
- **Learned:** angles match; eyelines are not promised.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a runaway push on one side | the engine | stabilise; the runaway fault | §55 |

## Evidence

- `studio/shot_catalog.json` (`matched_angles`); `studio/LTX_PLAYBOOK.md` §55.

## Open questions

- An eyeline check.
