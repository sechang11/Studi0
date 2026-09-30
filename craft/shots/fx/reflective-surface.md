# Reflections on a glossy surface (`fx-reflective-surface`)

| family | status | last tested | best result |
|---|---|---|---|
| fx | proven | 2026-09-30 | storm-sonata 030, 060, grade A |

**Also called:** reflections, lacquer reflection, wet ground reflections, puddle reflections, mirror-like surface, reflection consistency
**Not the same as:**
- [`fx-lightning`](lightning.md) - the light event; here the surface that mirrors it
- [`fx-rain`](rain.md) - the falling water; here the wet surface it leaves
- [`pov-reflection`](../pov/reflection.md) - a CHARACTER seeing her own reflection; that one failed, this one works

## Recipe (v1, 2026-09-30)

A glossy surface in the start frame, and the things it should reflect placed in the scene. Both engines hold reflections of the environment.

1. The start frame already shows the reflection (the lid, the wet cobbles, the puddle).
2. Either engine; storm-sonata's reflections were on H3.

## Checks before picking

- The reflection moves with what it reflects (a lightning flash appears in the lid at the same moment).

## Progression

### 2026-09-30 · storm-sonata 030, 060 · lightning and windows in the lacquer; the plaza in wet stone · grade A
- **Did:** H3 seed 11.
- **Got:** lightning and lit windows in the lid; the plaza mirrored in the wet ground.
- **Learned:** reflections of the ENVIRONMENT hold. Reflections of a character are a different problem: [`pov-reflection`](../pov/reflection.md).

### 2026-09-30 · cyber-alchemist 308-312 · neon in puddles and wet asphalt · grade A-
- **Did:** the street place drawn wet with neon.
- **Got:** the reflections hold through the descent, the landing and the walk away.
- **Learned:** as above.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| (none recorded yet) | | | |

## Evidence

- `studio/samples/fight/storm-sonata/h3_030_s11.mp4`, `h3_060_s11.mp4`.

## Open questions

- A reflection that must show a specific moving object in sync.
