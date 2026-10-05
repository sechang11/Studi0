# A glowing energy orb (`fx-energy-orb`)

| family | status | last tested | best result |
|---|---|---|---|
| fx | works-with-caveats | 2026-09-30 | orb_end.py and a hue-window recolour (§60-§62, §76, §88), grade B+ |

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

### 2026-09-30 · the jester in the wood 306 · a fireball as a glowing sphere in a 3D set · grade B
- **Did:** an emissive sphere keyed from her hands to the oak in the set ([`pipe-3d-set`](../pipeline/3d-set.md)), growing at the impact; LTX-2.3 IC-LoRA on its depth.
- **Got:** the fireball flew where it was keyed and read as an orange orb; the blast - the same sphere grown to 2.2 m - was painted as dark red blobs, not flame.
- **Learned:** a small glowing shape becomes a fireball; a big solid one does not become fire.

### 2026-10-01 · the duel in the clearing · the jester's orbs, juggled and thrown · grade B+
- **Did:** glowing purple orbs named in the beats on H3 between two set frames: juggled and hurled (D02), streaking at her and bursting against a tree (D03), and in the long version deflected, rained from a tornado, stretched into serpents, pulled from his cap as a string.
- **Got:** the orbs on every take that named them, magenta-white and bursting where they hit, 2 of 2 (D02, D03).
- **Learned:** an orb is a word on H3 now - no recolour in post (§60-§62) for a fight.

### 2026-10-05 · the ember thief 090-100 · orbs thrown at a fighter · grade A-
- **Did:** "three glowing purple orbs blink into being above his palm... he flicks them at her"; in the next shot "a glowing purple orb streaks in from the right and she bats it aside".
- **Got:** on six seeds the orbs came in the size of her body - a magenta ball filling half the frame; with "a small glowing purple orb, the size of a fist" two seeds of two drew fist-sized streaks she could swat and duck.
- **Learned:** an orb with no size is drawn as big as the frame allows: give it a size in the words.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the blast reads as dark red blobs | a solid glowing sphere under the depth | untested: many small glowing pieces, or a lit cloud | forest 306 |
| the orb welded to the staff | an edit asked to grow it | orb_end.py | §60.2 |
| flames turn green | a global hue rotation | a hue window | §76 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §60-§62, §76, §80, §85, §88.

## Open questions

- None open.
