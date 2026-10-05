# Shot / reverse shot (`frame-shot-reverse`)

| family | status | last tested | best result |
|---|---|---|---|
| framing | partial | 2026-09-30 | plaza 103, the reverse of a place from a 3D set, grade A- (two people: builder `matched_angles`, grade C+) |

**Also called:** shot reverse shot, reverse angle, matched angles, conversation coverage, eyeline match
**Not the same as:**
- [`frame-over-the-shoulder`](over-the-shoulder.md) - one of the pair, with the listener's shoulder in frame
- [`frame-two-shot`](two-shot.md) - both people in one frame
- [`cont-screen-direction`](../continuity/screen-direction.md) - which side of the screen each of two characters keeps across a whole scene

## Recipe (v1, 2026-09-05)

The builder performs matching angles on the two plates (keystone, measured); the eyeline cannot be promised.

## Checks before picking

- Both sides at the same angle; the eyelines meet (by eye).

## Progression

### 2026-09-05 · §55 · matched angles · grade C+
- **Did:** two mediums from matched low angles.
- **Got:** the angles delivered to 0.04 and within 0.08 of each other; the camera ran away (39% push) and the place drifted.
- **Learned:** angles match; eyelines are not promised.

### 2026-09-30 · plaza 103 · the reverse of a place, from a 3D set · grade A-
- **Did:** the square's south side (looking back past the fountain at the archway) as a camera in one set ([`pipe-3d-set`](../pipeline/3d-set.md)), against the plate turned round by the angles LoRA plus words.
- **Got:** from the set, the arch, the cypresses and the houses either side where the set has them: fit 0.58 (chance 0.16), held 99% over the take. The turned plate invented a whole south side (arcaded houses, no arch), and the words then drew a different arch between different houses (fit 0.30). No people in either; the conversation case is untested.
- **Learned:** a reverse sees what the plate never saw; only a set knows what is there.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the reverse shows a different place | the plate never saw that side | a set of the place | plaza 103 (today's way) |
| a runaway push on one side | the engine | stabilise; the runaway fault | §55 |

## Evidence

- `studio/shot_catalog.json` (`matched_angles`); `studio/LTX_PLAYBOOK.md` §55.

## Open questions

- An eyeline check.
