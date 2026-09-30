# Fire and flame in the scene (`fx-fire`)

| family | status | last tested | best result |
|---|---|---|---|
| fx | untested | 2026-09-07 | none generated on purpose |

**Also called:** fire, flames, torches, candle flame, burning
**Not the same as:**
- [`fx-thruster-flames`](thruster-flames.md) - jets from a machine
- [`fx-energy-orb`](energy-orb.md) - magic light, recoloured in post

## Recipe (v0, 2026-09-07)

No fire effect has been generated on purpose. What is known: torch flames in a scene are the one warm thing a recolour must not move (use a hue window, §76, §88).

## Checks before picking

- Flames keep their colour through any grade or recolour.

## Progression

### 2026-09-07 · §76, §88 · protecting torch flames during a recolour · grade n/a
- **Did:** recoloured an orb in a torch-lit hall.
- **Got:** a global hue rotation would have turned the flames green; a brightness-only mask caught the chains and the flames.
- **Learned:** hue window plus brightness.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| flames change colour | a global recolour | a hue window | §76 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §76, §88.

## Open questions

- A fire as the subject of a shot.
