# Dolly zoom (`cam-dolly-zoom`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | works-with-caveats | 2026-09-30 | cyber-alchemist 307, grade B+ |

**Also called:** vertigo, vertigo effect, reverse dolly zoom, zolly, contra-zoom, trombone shot
**Not the same as:**
- [`cam-push-in`](push-in.md) - a push grows the subject; a dolly zoom holds her size while the background stretches or squeezes
- [`cam-crash-zoom`](crash-zoom.md) - a fast zoom with the camera still; nothing holds its size

## Recipe (v1, 2026-09-30)

A Blender previz of the move with her mesh (lens and distance changing together, lens/distance constant), painted by LTX-2.3 IC-LoRA from a start frame dressed from the previz's first frame.

1. `previz_blender.py --scene canyon` (or a scene whose lines run away behind her) with `--radius 14 --radius-to 3.5 --lens 100 --lens-to 25 --cam-z 1.1 --look-z 1.1 --figure-glb <her model.glb>`. Distance and lens are keyed with the same easing, so her size holds on every frame. Reverse the pairs for the other direction.
2. Shot script: `"engine": "previz"` with those keys in `"previz"`, plus `"dress"` words (what each grey shape becomes) and `"grade"` words for THIS place. The film's default grade described a stone workshop and would have been appended to a canyon.
3. `studio/_tools/previz_shot.py --sequence F --shot 307 --seeds 11 202 --bypass-seeds --force`. It dresses the previz's first frame (Qwen-Image-2.1, `workflows/80_qwen21_edit_refs.json`) into the start frame and draws with `workflows/74_ltx23_ic_lora_control.json`.
4. Prompt: what she does and the effect in words ("she stays the same size while the canyon seems to stretch away").

## Checks before picking

- Her height in the first and last frames: equal within a few percent.
- The background's lines change angle (the canyon deepens or flattens). A push-in in disguise keeps them parallel.
- Seed 202 painted the neon canyon as streaky grey walls: check the place survived.

## Progression

### 2026-08-08 · VIDEO_RULES PICTURE-04 · the `dolly_zoom` preset in roll.py · grade F
- **Did:** the preset.
- **Got:** byte-identical to a static render.
- **Learned:** it needs depth.

### 2026-09-30 · cyber-alchemist 307 · asked in words on LTX-2.5 and H3 · grade D
- **Did:** "Reverse dolly zoom: she stays the same size in the centre of the frame while the canyon around her seems to stretch and tunnel away" on a composed start frame; LTX and H3, seeds 11 and 202.
- **Got:** no dolly zoom. LTX (both seeds) kept her size while the background RE-FORMED: neon signs vanish and reappear in new places rather than stretching. H3 seed 11 held still; H3 seed 202 pulled back and rose. `craft/VIDEO_RULES.md` PICTURE-04 had already recorded that `roll.py`'s `dolly_zoom` preset came back byte-identical to a static render.
- **Learned:** no engine here knows the move by name. A background that morphs while the subject holds is not a lens change.

### 2026-09-30 · cyber-alchemist 307 · previz canyon, 100 mm at 14 m → 25 mm at 3.5 m · grade B+
- **Did:** the recipe above, seeds 11 and 202.
- **Got:** seed 11 is a true dolly zoom: the jets fire, her size holds, and the neon walls swing from compressed to deep. Seed 202 turned the neon canyon into grey streaks. The brief's deceleration does not read: she hovers.
- **Learned:** the move comes from the previz. Anything she does during it (decelerating) has to be in the previz too.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the background morphs, or the camera pulls back, instead | asked in words | previz | 307 LTX/H3 |
| the place loses its look mid-move | a seed that ignores the dressed start frame's texture | draw two seeds; check the place | 307 seed 202 |
| the canyon described as a workshop | the film-wide grade appended to the dress | a per-shot `"grade"` in `"previz"` | 307 (caught before drawing) |

## Evidence

- `studio/samples/fight/cyber-alchemist/pv_307_s11.mp4`, `previz_307/`.
- `studio/_tools/previz_blender.py` (`build_canyon`, `_move_camera`), `studio/_tools/previz_shot.py`.

## Open questions

- Her deceleration and the jets igniting as part of the previz (animate her position).
- The forward version (dolly out, zoom in) - not tried.
