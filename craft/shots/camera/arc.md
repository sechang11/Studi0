# Arc, a partial orbit (`cam-arc`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | works-with-caveats | 2026-09-30 | cyber-alchemist 103 as a single 45° piece, grade B |

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

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| no circling at all | asked in words | a previz piece | quantum-courier 307-310 |
| the room slides but she does not turn | a stand-in with no front | her mesh | cyber-alchemist 103 cone test |

## Evidence

- `studio/_tools/previz_blender.py` (`--scene orbit --degrees N`), `studio/_tools/previz_shot.py`, `workflows/74_ltx23_ic_lora_control.json`.
- [2026-09-30 review](../reviews/2026-09-30-challenge-films.md).

## Open questions

- Arcs past 90° in one piece; arcs around a moving subject.
