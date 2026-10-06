# An object held across the cut (`trans-held-object`)

| family | status | last tested | best result |
|---|---|---|---|
| transitions | works-with-caveats | 2026-10-05 | the fire esper: embers across 050-130 and 210-220, grade B+ |

**Also called:** object glue, held element, constant object, one object stays while everything else changes, overlay across cuts, continuous particles, embers through the cut
**Not the same as:**
- [`trans-match-cut`](match-cut.md) - a SHAPE that rhymes at the cut; the object here stays the same object
- [`trans-sound-bridge`](sound-bridge.md) - the sound crosses the cut, not the picture

## Recipe (v1, 2026-10-05)

Keep one element of the picture going while the shots change under it - an overlay composited over a range of shots in ONE continuous pass, so it never restarts at a cut (LTX_PLAYBOOK §102, a draft).

1. In the glue plan: `"overlays": [{"kind": "embers", "from": "050", "to": "130", "density": 0.8, "seed": 7}]` - glowing embers drifting up, a numpy particle layer the length of the whole film, black outside its span, faded in and out over half a second, blended with **screen in RGB** (`format=gbrp` on both inputs: in YUV the blend runs on the chroma planes too and tints the whole picture).
2. In the shot design: the same object in both shots of an echo (the circle of runes at her feet, 040, seen from above in 050).
3. Choose the object from the story: the spell's embers belong to the summoning and the return; a hunt has its own sound bed instead.

## Checks before picking

- Watch the cut: the overlay's particles must not jump or restart.
- The overlay must sit IN the world's light (embers in a red-lit forest), not on a clean daylight shot.

## Progression

### 2026-10-05 · the fire esper · embers across the summoning and the return · grade B+
- **Did:** the recipe above.
- **Got:** the embers drift on through the cuts of the summoning (050-130) without restarting and sit in the red light of the burning forest; in 050's dusk they read as fireflies more than embers. 040 → 050 holds the circle of runes in both shots (once 050's was painted where it is).
- **Learned:** an overlay belongs to the moment it is made of (the spell's embers from the spell's first light, not from dusk); the same object in two shots is shot design, an echo's detail painted in.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the whole picture tinted when the overlay is blended | `blend=screen` on YUV frames screens the chroma planes too | convert both to `gbrp` before the blend | glue_cut.py trial, 2026-10-05 |

## Evidence

- `studio/_tools/glue_cut.py` (`embers()`); `studio/shotscripts/fire-esper.cut.json`.

## Open questions

- A physical frame that stays while the picture inside changes (a window, a ring of fire) - the director's other example - is not built.
