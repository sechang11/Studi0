# Previz: Blender under the video engine (`pipe-previz`)

| family | status | last tested | best result |
|---|---|---|---|
| pipeline | proven | 2026-09-30 | cyber-alchemist 103-110, 307, 310, grade A- |

**Also called:** previz, Blender previz, IC-LoRA control, depth control, choreographed shot, simulation under the painter
**Not the same as:**
- [`pipe-first-last`](first-last.md) - two frames and the engine's guess between them; previz dictates every frame's geometry
- [`pipe-motion-transfer`](motion-transfer.md) - motion from a real video, not a Blender scene
- [`pipe-3d-set`](3d-set.md) - a whole place every shot of a scene stands in; previz stages one move around one subject

## Recipe (v1, 2026-09-30)

Blender renders the geometry of the move (and any physics); LTX-2.3 with the IC-LoRA union control (`workflows/74_ltx23_ic_lora_control.json`) reads its depth and paints the film over it.

1. `studio/_tools/previz_blender.py --scene crates|fall|aisle|orbit|street|canyon`; `--figure-glb` for a character's real shape, `--figure-turn` to face her. `--scene set` puts the camera in a whole place built once ([`pipe-3d-set`](3d-set.md)).
2. `studio/_tools/previz_shot.py`: one shot (dress the first frame or use `"start"`; `"reverse": true` writes `pvr_`); `studio/_tools/previz_chain.py`: one long move over many shots (`--backward`, `--match`, `--draw`).
3. Run one IC-LoRA driver at a time, or rely on the per-take input names.
4. Output folders inside the repo: the flatpak Blender cannot see `/tmp`.

## Checks before picking

- Motion agreement against the previz (r); for constant motion it is noisy - look instead.

## Progression

### 2026-09-24 · §97.2 · a camera move by depth guide · grade A
- **Did:** the rig's arithmetic pull-back rendered first; its MoGe-2 depth into LTX-2.3 IC-LoRA.
- **Got:** 27% pull back on 3 of 3 seeds where words pushed in; the revealed border is generated.
- **Learned:** the depth guide moves the camera.

### 2026-09-27 · dead-stock 070 · a wall of crates pushed over · grade n/a
- **Did:** rigid-body previz under the IC-LoRA (per `previz_shot.py`'s record).
- **Got:** motion agreement r = 0.85-0.96 across five takes.
- **Learned:** Blender choreographs, the engine paints.

### 2026-09-30 · cyber-alchemist · camera moves by previz · grade A-
- **Did:** the orbit, the dolly zoom and the pan up to her face.
- **Got:** all three delivered (see their entries); two driver bugs fixed on the way (shared input names; a torch memory probe that failed on a full card).
- **Learned:** a camera move is choreography too.

### 2026-09-30 · plaza test · a camera in a whole set · grade B+
- **Did:** `--scene set`: eight cameras in one Blender square, rendered lit (Eevee) as both the control video and the start frames' source; `--masks` for the landmark and surface ID frames.
- **Got:** motion agreement 0.52-0.99 (the arc lowest, the static and slow shots 0.75-0.99); a lit render served as the control as well as the flat one; 13 s to render a shot with its masks.
- **Learned:** the same driver films a whole place; see [`pipe-3d-set`](3d-set.md).

### 2026-09-30 · the jester in the wood · puppets as actors, then as stand-ins · grade B+
- **Did:** characters as jointed puppets in a set ([`pipe-3d-set`](../pipeline/3d-set.md)), their depth drawn by LTX-2.3 IC-LoRA (`74`); then the same choreography as a pose skeleton (`previz_blender.py --joints`: 18 keypoints per puppet a frame, the face's points dropped where the camera cannot see them) on the same IC-LoRA; then only the frames, with H3 acting between them (§99.10).
- **Got:** on the depth, the motion was the puppets' (a shuffle, a plank of a leap) and so was the shape (a tube of a skirt); on the skeleton the costume came free and the motion stayed the puppets'; between the frames the engine acted, 2 of 2.
- **Learned:** previz drives what it can author well - the camera, the place, what falls where - and places the characters; it does not act for them.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the character moves like the puppet: a shuffle, a plank of a leap, a tube of a skirt | the take follows the puppets' depth, or a skeleton taken from them | puppets as stand-ins only: the set gives the frames, the engine acts (§99.10) | forest 302, 304 |
| a job reads another job's control video | fixed ComfyUI input names | per-take names (fixed) | orbit seed 505 |
| the shot never runs: CUDA out of memory in `make_room` | a torch probe on a full card | skip the probe (fixed) | cyber-alchemist 307 v1 |
| Blender cannot open the file | a relative or `/tmp` path under flatpak | absolute paths inside the repo | tests |

## Evidence

- `studio/_tools/previz_blender.py`, `studio/_tools/previz_shot.py`, `studio/_tools/previz_chain.py`.

## Open questions

- A moving subject in the previz (her path animated).
