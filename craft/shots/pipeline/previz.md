# Previz: Blender under the video engine (`pipe-previz`)

| family | status | last tested | best result |
|---|---|---|---|
| pipeline | proven | 2026-09-30 | cyber-alchemist 103-110, 307, 310, grade A- |

**Also called:** previz, Blender previz, IC-LoRA control, depth control, choreographed shot, simulation under the painter
**Not the same as:**
- [`pipe-first-last`](first-last.md) - two frames and the engine's guess between them; previz dictates every frame's geometry
- [`pipe-motion-transfer`](motion-transfer.md) - motion from a real video, not a Blender scene

## Recipe (v1, 2026-09-30)

Blender renders the geometry of the move (and any physics); LTX-2.3 with the IC-LoRA union control (`workflows/74_ltx23_ic_lora_control.json`) reads its depth and paints the film over it.

1. `studio/_tools/previz_blender.py --scene crates|fall|aisle|orbit|street|canyon`; `--figure-glb` for a character's real shape, `--figure-turn` to face her.
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

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a job reads another job's control video | fixed ComfyUI input names | per-take names (fixed) | orbit seed 505 |
| the shot never runs: CUDA out of memory in `make_room` | a torch probe on a full card | skip the probe (fixed) | cyber-alchemist 307 v1 |
| Blender cannot open the file | a relative or `/tmp` path under flatpak | absolute paths inside the repo | tests |

## Evidence

- `studio/_tools/previz_blender.py`, `studio/_tools/previz_shot.py`, `studio/_tools/previz_chain.py`.

## Open questions

- A moving subject in the previz (her path animated).
