# Electric arcs on a body (`fx-electric-arc`)

| family | status | last tested | best result |
|---|---|---|---|
| fx | proven | 2026-09-06 | `fx_zap` (§62.2), grade A- |

**Also called:** electrocution, zap, electric shock, arcs of energy, lightning strikes a person
**Not the same as:**
- [`fx-lightning`](lightning.md) - weather in the sky; here energy discharging into a body or from a source
- [`fx-energy-orb`](energy-orb.md) - a held glowing ball

## Recipe (v1, 2026-09-06)

Built in post, not generated: a knockback, a violet flash spiking at contact and decaying at exp(-2.2t), forked arcs drawn as random walks with a decaying step (redrawn every second frame), and a chromatic shear pulling R and B 14 px apart that settles. Draw the arcs FROM THE CENTRE OUTWARD.

## Checks before picking

- It reads as electricity, not as being hit by light.

## Progression

### 2026-09-06 · §62.2 · fx_boom, then fx_zap · grade A-
- **Did:** a knockback and a fade to black (`fx_boom`); then the arcs, flash and shear (`fx_zap`).
- **Got:** fx_boom read as being hit by LIGHT; fx_zap reads as electrified. Edge-start bolts read as weather; centre-start as the thing discharging into us.
- **Learned:** the direction of the arcs carries the meaning.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| reads as a flash of light | no arcs | fx_zap | §62.2 |
| reads as weather | arcs start at the edges | start them at the centre | §62.2 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §62.2.

## Open questions

- None open.
