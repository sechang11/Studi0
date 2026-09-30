# Glass shatter on impact (`fx-glass-shatter`)

| family | status | last tested | best result |
|---|---|---|---|
| fx | proven | 2026-09-30 | cyber-alchemist 202, grade A- |

**Also called:** shatter, glass breaking, vial shatters, 1000 fps shatter, slow-motion shatter, smashing glass
**Not the same as:**
- [`fx-impact-splash`](impact-splash.md) - a body hitting liquid; here a brittle object breaks on a hard surface
- [`fx-zero-g-droplets`](zero-g-droplets.md) - drops hanging and rising with no impact; a shatter is one violent moment
- [`fx-liquid-in-vessel`](liquid-in-vessel.md) - the liquid still inside the glass; a shatter releases it
- [`fx-impact-burst`](impact-burst.md) - debris at a strike, no brittle object
- [`fx-broken-state`](broken-state.md) - the object already broken; here the moment it breaks

## Recipe (v1, 2026-09-30)

A floor-level start frame with the object just touching the ground, rendered on H3. LTX barely breaks it.

1. Start frame: floor-level, the object at the moment of contact, the room behind (Qwen-Image-2.1 with the place repeated as its references did fine here: [place, place, place]).
2. `"engine": "both"`, two seeds; expect to pick H3.
3. Prompt: "In extreme slow motion, a thousand frames a second, the vial hits the stone floor and the glass bursts into glittering shards; the mercury flies out in heavy silver beads."

## Checks before picking

- The object breaks within the take, not only a splash beside an intact bottle.
- The liquid reads as what it is (mercury as beads, not water).

## Progression

### 2026-09-30 · cyber-alchemist 202 · floor-level vial, LTX and H3 · grade A-
- **Did:** the recipe above, both engines, seeds 11 and 202.
- **Got:** LTX (both seeds) kept the vial nearly whole with a small splash. H3 seed 11 burst it into shards and silver droplets; H3 seed 202 burst it and spread a carpet of silver beads across the floor. H3 seed 202 is in the cut.
- **Learned:** a shatter is an H3 shot.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the vial stays whole | LTX under-plays a destructive event | H3 | 202 LTX |

## Evidence

- `studio/samples/fight/cyber-alchemist/h3_202_s202.mp4`; strip `h3_a.jpg`.

## Open questions

- A shatter of something big (a window) with a figure beside it.
