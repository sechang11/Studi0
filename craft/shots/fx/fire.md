# Fire and flame in the scene (`fx-fire`)

| family | status | last tested | best result |
|---|---|---|---|
| fx | works-with-caveats | 2026-10-01 | the duel D04, D05, D10: fireballs, a fire aura and a fire volley on H3, 2 of 2, grade B+ |

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

### 2026-10-01 · the duel in the clearing · fire as the subject: an aura, a volley, fireballs, a fire ring and whip and beam · grade B+
- **Did:** fire asked for by name on H3 between two set frames: flames igniting in her hands and an orange aura (D04), fireballs streaking across the clearing into a boulder (D05), a huge fireball against a purple orb (D10); in the long version a ring of fire, a fire whip, a fire beam, a dragon of fire.
- **Got:** fire on every take that asked for it, flaring and dying as H3's effects do (§96): the aura and the volley on 2 of 2, the boulder's blast a column of fire with rock flying.
- **Learned:** H3 draws fire as an action's effect; ask for it in the beat, never as a standing wall.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| fire everywhere on a quiet shot | the battle style line on an establishing shot | the style line only where something is fought | forest-duel D01 |
| flames change colour | a global recolour | a hue window | §76 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §76, §88.

## Open questions

- A fire as the subject of a shot.
