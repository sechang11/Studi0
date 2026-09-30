# Establishing shot, empty (`frame-establishing-empty`)

| family | status | last tested | best result |
|---|---|---|---|
| framing | proven | 2026-09-30 | cyber-alchemist 101, grade A |

**Also called:** establishing shot, establishing wide, the place alone, empty set, opening wide, location shot, empty night, the place at night
**Not the same as:**
- [`frame-wide-with-figure`](wide-with-figure.md) - the same distance with a person in it
- [`cont-place`](../continuity/place.md) - keeping the place the same in every shot; this is the shot that shows it first

## Recipe (v1, 2026-09-30)

The place's own plate is the start frame (a shot with no cast gets it automatically), with nobody in the negative.

1. `"anchor": null` and the place as the only reference: `fight.py --anchors` copies the plate as the start frame.
2. `"avoid_extra": "people, a person, a figure, a crowd, a face, hands"` - the engine adds people otherwise.
3. A slow move in words, and the place's sounds.

## Checks before picking

- Nobody appears.
- The place stays the plate (no drift into a different room).

## Progression

### 2026-08-03 · CINEMATOGRAPHY §3 · five wide openings in a row · grade C
- **Did:** the CHRONO opening: five wide and extra-wide shots.
- **Got:** they read as a slideshow.
- **Learned:** break a run of wides with an extreme close-up or a macro.

### 2026-09-04 · §40-§42 · empty shots grow people; silence · grade C
- **Did:** an empty courtyard (anime), re-rendered with "empty" and a negative naming students and pedestrians; an establishing shot with wind and birds in the words.
- **Got:** 3 renders, 3 visitors; the establishing shot came back silent (rms 0.0013).
- **Learned:** "the fix is a different instrument, not a stronger prohibition": after one retry, the plate itself on the camera rig; name the sounds.

### 2026-09-05 · §50-§51 · a static empty wide, stabilised · grade A-
- **Did:** the builder's stabilise pass.
- **Got:** a drift of 1.09-1.16 held to 1.016, pan 0.000, tilt 0.001.
- **Learned:** arithmetic holds an empty frame still.

### 2026-09-30 · all five challenge films · the opening wide of each place · grade A
- **Did:** the recipe above: system-error 010 and 100, smallest-gear 010, storm-sonata 010, quantum-courier 101, cyber-alchemist 101 (LTX).
- **Got:** every one held its place. Cyber-alchemist 101 pushed slowly into the workshop with smoke and flickering neon.
- **Learned:** the plate IS the establishing shot.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| people walk through an empty shot | the engine's prior for the place | the camera rig after one retry (builder); `"avoid_extra"` (shot-script pipeline) | §40-§41 |
| silent | nothing named to sound | name the sources; build the bed | §42 |

## Evidence

- `studio/samples/fight/cyber-alchemist/shot_101_s11.mp4`; `studio/_tools/fight.py` (`stage_anchors`: an anchor of None copies the plate).

## Open questions

- None open.
