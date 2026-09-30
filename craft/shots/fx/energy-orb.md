# A glowing energy orb (`fx-energy-orb`)

| family | status | last tested | best result |
|---|---|---|---|
| fx | works-with-caveats | 2026-09-07 | orb_end.py and a hue-window recolour (§60-§62, §76, §88), grade B+ |

**Also called:** energy orb, magic orb, glowing sphere, spell, charged staff
**Not the same as:**
- [`fx-electric-arc`](electric-arc.md) - arcs discharging
- [`fx-fire`](fire.md) - real flame in the scene, which the orb's recolour must not touch

## Recipe (v1, 2026-09-07)

Construct the orb's end frame instead of asking an edit model to "grow" it; recolour with a hue window, not a global hue rotation.

1. `orb_end.py`: find the orb by brightness (above 200), lift it on a feathered radial mask onto the start frame, add its light.
2. Recolour with a hue window (244°-338°) weighted by saturation; mask on two properties (brightness × hue window: 21% → 6% of the frame).
3. "A discarded take is still an asset": the full-screen orb came from a drifting take.

## Checks before picking

- The torches (real fire) keep their colour.

## Progression

### 2026-09-06 · §60.2, §62.1 · "grow the orb" asked of qwen · grade D
- **Did:** an end frame by edit.
- **Got:** the orb welded to the staff; the shot charged but never fired.
- **Learned:** construct the end frame.

### 2026-09-07 · §76, §88 · recolour and mask · grade B+
- **Did:** a hue window instead of a global rotation; a two-property mask.
- **Got:** the orb recoloured; the torch flames kept their orange (a global rotation would have turned them green).
- **Learned:** recolour rather than re-render when only the colour is wrong.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the orb welded to the staff | an edit asked to grow it | orb_end.py | §60.2 |
| flames turn green | a global hue rotation | a hue window | §76 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §60-§62, §76, §80, §85, §88.

## Open questions

- None open.
