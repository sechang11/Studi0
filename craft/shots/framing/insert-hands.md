# Insert of hands at work (`frame-insert-hands`)

| family | status | last tested | best result |
|---|---|---|---|
| framing | works-with-caveats | 2026-09-30 | system-error 050; cyber-alchemist 112e, grade A- |

**Also called:** hands close-up, hands at work, hand insert, tool in hand
**Not the same as:**
- [`frame-macro-object`](macro-object.md) - the object alone is the subject
- [`frame-hands-two-people`](hands-two-people.md) - two people's hands together
- [`pov-hands-in-frame`](../pov/hands-in-frame.md) - her own hands seen from her eyes
- [`cont-fingers`](../continuity/fingers.md) - what the fingers do, and how well

## Recipe (v1, 2026-09-30)

Flux 2 for the start frame when the hands must be close (Qwen widened to the torso); name the gloves.

1. Start frame: Flux 2 ref3 [her, her, place]; the gloves and what they hold named.
2. H3 when the hands lift or place something; LTX for a hold.

## Checks before picking

- Five fingers per hand; gloves keep their details.

## Progression

### 2026-08-03 · CINEMATOGRAPHY §5 #1, #3, #4 · hand beats packed into one shot · grade C
- **Did:** 100_dropped packed three beats and an exit from frame; 080_pendant's hand was already open in the keyframe.
- **Got:** the beats did not all happen; the pendant could not be opened.
- **Learned:** one beat per insert; the start frame shows the state BEFORE the action.

### 2026-09-30 · system-error 050 · chopsticks in a gloved hand over the bowl · grade A-
- **Did:** the ECU of the bowl with the gloved hand and chopsticks in it; H3 seed 202.
- **Got:** a clean lift.
- **Learned:** H3 for a hand lifting something.

### 2026-09-30 · cyber-alchemist 112e, 201 · gauntlets lifting and dropping the vial · grade B+
- **Did:** 112e: Flux 2 (both hands lifting the vial); 201: Qwen seed 202, which framed the hand closer than seed 11.
- **Got:** 201 LTX seed 11 dropped the vial out of frame.
- **Learned:** pick the closest framing; the drop reads.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the insert shows the torso | Qwen widened the framing | Flux 2 or another Qwen seed | cyber-alchemist 201 seed 11 |

## Evidence

- `studio/samples/fight/system-error/h3_050_s202.mp4`; `studio/samples/fight/cyber-alchemist/shot_201_s11.mp4`, `anchor_112e.png`.

## Open questions

- None open.
