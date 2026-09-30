# Spray off a wet surface (`fx-surface-spray`)

| family | status | last tested | best result |
|---|---|---|---|
| fx | partial | 2026-09-30 | storm-sonata 070, grade C+ |

**Also called:** mist off the keys, droplets flying off, water spraying off the surface, spray with every strike
**Not the same as:**
- [`fx-impact-splash`](impact-splash.md) - one heavy impact into liquid; spray is fine droplets thrown repeatedly
- [`fx-rain`](rain.md) - rain falls from above; spray is thrown up by what happens on the surface

## Recipe (v1, 2026-09-30)

H3 only, and keep the spray small in the words. LTX turns spray into an explosion.

1. Start frame: the wet surface with a few droplets already in the air.
2. H3; LTX accumulates the effect frame by frame until the object blows apart.
3. Prompt: name small droplets, not "spray flies off".

## Checks before picking

- The object is intact at the end.
- The droplets are visible at delivery size (in the cut they were faint).

## Progression

### 2026-09-30 · storm-sonata 070 · spray off the keys on one big chord · grade C+
- **Did:** "His hands crash down onto the keys in one huge chord and spray flies off the keyboard; at the same instant lightning strikes behind the church", LTX and H3.
- **Got:** LTX built the spray up until the piano exploded. H3 seed 202 gave some spray and a real lightning flash on the chord; it is in the cut, and the spray is faint.
- **Learned:** LTX accumulates an effect you ask for; H3 does not.

### 2026-09-30 · storm-sonata 040 · droplets off the keys during a fast run · grade C
- **Did:** "with every strike, water droplets fly off the keys in bright sprays", LTX and H3.
- **Got:** the take in the cut (H3 seed 11) shows the fingers moving with little visible spray.
- **Learned:** as above; spray has to be large in frame to read.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the object explodes | LTX accumulates the effect | H3; smaller words | storm-sonata 070 |
| the spray is too faint to read | small droplets at delivery size | a tighter framing on the surface | storm-sonata 070 |

## Evidence

- `studio/samples/fight/storm-sonata/h3_070_s202.mp4`; the challenge films README.

## Open questions

- A macro of the keys where spray can be large in frame.
