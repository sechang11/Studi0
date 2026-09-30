# Insert of a place's detail (`frame-insert-detail`)

| family | status | last tested | best result |
|---|---|---|---|
| framing | works-with-caveats | 2026-09-05 | builder rig push 1.117 for 1.12 (§41, catalog `insert_detail`), grade A- |

**Also called:** detail shot of the place, place detail, B-roll detail
**Not the same as:**
- [`frame-macro-object`](macro-object.md) - a hero object whose mechanism moves; here a small true detail of the place
- [`trans-cutaway`](../transitions/cutaway.md) - how an insert is used between shots

## Recipe (v2, 2026-09-04)

The place's own detail plate, on the camera rig (no generation) when the engine keeps adding things; describe only what is in the picture.

## Checks before picking

- Nothing grows (paper, cups), nobody walks through.

## Progression

### 2026-09-04 · §37, §38, §40-§42 · inserts on LTX · grade C
- **Did:** "wind moving a scrap of paper"; a courtyard insert marked empty; the ambient words "leaves, cloth".
- **Got:** a bench-sized sheet of paper grew; coffee cups grew on the counter; 3 renders of the courtyard, 3 visitors despite a negative naming them; the cloth ambient drew bunting in a park.
- **Learned:** "the fix is a different instrument, not a stronger prohibition": after one retry the shot becomes the plate itself on the camera rig.

### 2026-09-05 · §41, §53 · the rig's push · grade A-
- **Did:** `still_push` sized to the plate.
- **Got:** 1.117 for 1.12; the insert entry measured a 15% push.
- **Learned:** as above.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a small thing grows | words naming things the plate lacks | describe only what is in the picture | §37-§38 |
| people walk through | the engine's prior for the place | the camera rig | §40-§41 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §37-§42, §53; `studio/shot_catalog.json` (`insert_detail`).

## Open questions

- None open.
