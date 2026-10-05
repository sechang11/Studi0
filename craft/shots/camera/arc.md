# Arc, a partial orbit (`cam-arc`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | works-with-caveats | 2026-10-01 | plaza 106, a 100° arc in a 3D set pinned at both ends, grade B+ |

**Also called:** arc shot, half orbit, quarter orbit, camera arcs around, semicircle move
**Not the same as:**
- [`cam-orbit-360`](orbit-360.md) - the full circle; it needs the two-halves chain, an arc is one piece
- [`cam-pan`](pan.md) - a pan turns the camera where it stands; an arc moves the camera round the subject, so the background slides with parallax

## Recipe (v1, 2026-09-30)

One previz piece: `previz_blender.py --scene orbit` with `--degrees` set to the arc, drawn once by LTX-2.3 IC-LoRA from the shot's start frame.

1. Her mesh as the figure (see [`cam-orbit-360`](orbit-360.md) step 1) if she must visibly turn with the arc; for arcs under about 30° the primitive stand-in may do.
2. Up to 45° in 97 frames (4 s) held identity in every test; one piece is one generation, so no hops, no drift.
3. Start from the shot's composed start frame; a room laid out like it.
4. Prompt: the arc's direction and pace in words, and what she does (usually: stands still).

## Checks before picking

- She turns relative to the lens by the arc's angle (compare the first and last frames).
- The background has parallax: near things slide faster than far ones. A pan without parallax is not an arc.

## Progression

### 2026-09-05 · §53 · the builder's orbit stand-in · grade D
- **Did:** a post move drifting sideways with a counter-zoom.
- **Got:** an 11% pan with no parallax.
- **Learned:** a 2D move is not an arc.

### 2026-09-07 · §96.5 · a previz arc under the IC-LoRA (a physics beat) · grade n/a
- **Did:** a Blender previz with a camera arc, drawn by LTX-2.3 IC-LoRA.
- **Got:** motion agreement r 0.84 / 0.71; "the geometry, timing and camera arc carried".
- **Learned:** the previz route carries an arc.

### 2026-09-30 · cyber-alchemist 103 (as its own test) · one 45° previz piece from the master · grade B
- **Did:** the first 45° of the orbit previz drawn from the master frame, LTX-2.3 IC-LoRA, 97 frames.
- **Got:** r = 0.94-0.96 against the previz; real parallax. With the primitive stand-in she did not turn with the camera. With her mesh (the orbit chain's first piece) she turned to three-quarter.
- **Learned:** one piece is a reliable arc; her turn needs her mesh.

### 2026-09-30 · quantum-courier 307-310 · the circling flight asked in words · grade D
- **Did:** the brief's "tight tracking shot circling Maya at 360 degrees", written as 307 "the camera circles around her as she flies, tight and fast" (LTX and H3) and 309 "as the camera swings around her".
- **Got:** the takes in the cut (307 H3 seed 202, 309 LTX seed 202) show her flying past and a glint; nothing circles her. The cut reads as four separate angles.
- **Learned:** an arc asked for in words is not delivered. Build it.

### 2026-09-30 · plaza 106 · a 100° arc in a 3D set, pinned at both ends · grade B+
- **Did:** the arc round the fountain as a camera in one set ([`pipe-3d-set`](../pipeline/3d-set.md)), LTX-2.3 IC-LoRA on its depth from a dressed start frame; then again with the move's last frame (the set's render, dressed) pinned at frame -1.
- **Got:** unpinned, the geometry followed (motion r 0.52-0.71) but the cafe the arc came round to was painted as a pink house with a white awning (the fit held 64-78%); pinned, it arrived as the cafe - striped awning, CAFFE sign - and the fit held 96-97%. Asked in words from a composed frame (LTX-2.5), the camera did not circle at all.
- **Learned:** depth carries the shapes, only a dressed frame carries the look: pin the end of an arc that reveals.

### 2026-10-01 · the duel orbit test O01 · a 120° arc round a close fight, H3 between the set's two frames · grade C+
- **Did:** a camera circling Terra and the jester through 120° in 85 frames (the set's `arc`) while they trade six numbered beats; H3 (`65`) between the set's first and last frames, seeds 11 and 202; then with the end frame edited into the beats' last pose (`studio/samples/settest/work/orbit_test.py`, `orbit_key.py`).
- **Got:** a whip, not an arc, 4 of 4: the side view held to frame ~46, a 4-6 frame smear or speed-line burst, the end view. The fight played through it.
- **Learned:** between two views far apart H3 whips; it does not travel the arc.

### 2026-10-01 · the duel orbit test O01 · + waypoint keys from the set at 31° and 91° · grade B-
- **Did:** the set's camera at take frames 30 and 60 rendered and cast, each frame edited into that moment's blow, anchored as keys ([`pipe-key-poses`](../pipeline/key-poses.md), `orbit_way.py`); seeds 11 and 202.
- **Got:** every view visited in order, 2 of 2 - in steps: the first waypoint held ~16 frames, then a slide to the next; each waypoint is its own painting of the forest.
- **Learned:** waypoints steer the path, not the glide; a constant glide is the depth's (`pipe-3d-set`, LTX-2.3 IC-LoRA).

### 2026-10-01 · the duel orbit test O01 · five waypoints, one every 15 frames · grade B-
- **Did:** three more of the set's views on the arc (9°, 60°, 112°) posed into the hook, the backfist and the lock forming, five waypoint keys in all plus the posed end (`orbit_way.py keys5`, `take5`); seeds 11 and 202.
- **Got:** all five views in order, 2 of 2, in smaller steps; the parking stayed - seed 11's longest still run 13 frames (15 with two waypoints), seed 202's 5 either way.
- **Learned:** denser waypoints shrink the steps, not the parking; for a glide, the depth.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a whip instead of an arc: one view, a smear, the other | H3 between two views 120° apart | waypoint keys from the set (in steps), or the set's depth for a glide | duel orbit O01, 4 of 4 |
| the camera parks on a waypoint, then slides on | each waypoint painted on its own | open: fewer differences between the waypoint paintings | duel orbit O01, 2 of 2 |
| what the arc comes round to is invented (a pink cafe) | only the start frame carries the look | pin the arc's last frame, a dressed render of the set | plaza 106 |
| no circling at all | asked in words | a previz piece | quantum-courier 307-310 |
| the room slides but she does not turn | a stand-in with no front | her mesh | cyber-alchemist 103 cone test |

## Evidence

- `studio/_tools/previz_blender.py` (`--scene orbit --degrees N`), `studio/_tools/previz_shot.py`, `workflows/74_ltx23_ic_lora_control.json`.
- [2026-09-30 review](../reviews/2026-09-30-challenge-films.md).

## Open questions

- Arcs past 90° in one piece; arcs around a moving subject.
