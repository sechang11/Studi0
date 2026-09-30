# Fingers in motion (`cont-fingers`)

| family | status | last tested | best result |
|---|---|---|---|
| continuity | partial | 2026-09-30 | storm-sonata 040, grade C; smallest-gear 050, grade A- |

**Also called:** fast fingers, fingers on piano keys, finger count, hands playing, precise hand movement
**Not the same as:**
- [`frame-insert-hands`](../framing/insert-hands.md) - the framing; this entry is about what the fingers do
- [`frame-hands-two-people`](../framing/hands-two-people.md) - two people's hands interacting

## Recipe (v1, 2026-09-30)

Slow, deliberate finger work holds; fast playing does not follow any real music. Keep hands large and moves slow; do not promise a real passage.

1. Start frame: the hands large, fingers separated and on the keys or the tool.
2. H3 for hands that interact with something.
3. Prompt: one slow action per shot.

## Checks before picking

- Five fingers per hand in every frame.
- For music: accept that the fingers will not match the notes.

## Progression

### 2026-08-05 · CURRENT_PRACTICE §4.1 · hand negatives · grade n/a
- **Did:** a public claim that hand negatives raise quality from 60% to 85%.
- **Got:** a sweep found zero effect at CFG 1-7.
- **Learned:** do not rely on negatives for hands.

### 2026-09-30 · storm-sonata 040 · fingers racing across the keys · grade C
- **Did:** "His fingers race across the keys in a fast, precise run up the keyboard ... The camera tracks fast alongside the hands", LTX and H3.
- **Got:** the fingers move and stay five to a hand at this size, but play no real passage; the take in the cut (H3 seed 11) does not track.
- **Learned:** no engine here follows a score; fast playing is texture, not performance.

### 2026-09-30 · smallest-gear 050 · his fingers guide her hand with tweezers · grade A-
- **Did:** a slow guided move, H3.
- **Got:** a readable hand-over-hand guide.
- **Learned:** slow hand work holds.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| fingers move but play nothing | no engine follows music | do not promise a passage; cut on the hands' rhythm | storm-sonata 040 |

## Evidence

- `studio/samples/fight/storm-sonata/h3_040_s11.mp4`; `studio/samples/fight/smallest-gear/h3_050_s202.mp4`.

## Open questions

- Hands driven by a pose control (H3 pose, workflow 84) from a real performance.
