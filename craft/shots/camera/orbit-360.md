# Orbit, 360° (`cam-orbit-360`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | works-with-caveats | 2026-09-30 | cyber-alchemist 103-110, grade A- |

**Also called:** 360, 360 orbit, 360-degree orbit, full orbit, circle shot, circling shot, orbit around the character, turntable move
**Not the same as:**
- [`cam-arc`](arc.md) - part of a circle, up to about 90°, which one generation can carry; a full circle cannot be one generation
- [`cam-roll`](roll.md) - the camera spins about its own lens axis; an orbit travels round the subject
- [`move-turn-in-place`](../motion/turn-in-place.md) - the subject turns and the room behind her stays; in an orbit the room behind her changes

## Recipe (v5, 2026-09-30)

Build it, never ask for it: a Blender previz of the whole circle around her real shape, painted by LTX-2.3 with the IC-LoRA union control in 45° pieces, drawn in two halves from the master frame.

1. **Her shape.** The /sheets "3D model" button (Hunyuan3D 2.1, `workflows/24_hunyuan3d_mesh.json`) on her character sheet writes `studio/sheets/<sheet>/model.glb` in about 34 s. A primitive stand-in (a cone and a ball) has no front, and the painter keeps her facing the lens.
2. **The shots.** One shot per 45°: eight shots of 97 frames (4 s at 24 fps; 8n+1 frames) is 32 s for the circle. `"engine": "previz"`. The first shot carries the move: `"previz": {"scene": "orbit", "degrees": 360, "radius": 3.3, "lens": 42, "cam_z": 1.45, "look_z": 1.25, "figure_glb": "studio/sheets/<sheet>/model.glb"}`.
3. **The room.** `studio/_tools/previz_blender.py --scene orbit` lays out a vaulted room: bench on her right, railing behind her. Match it to the master frame's layout. Keep tall props (lamps, tall flasks) off the part of the circle the camera passes over; one stood between the lens and her for a quarter of the turn. Render the previz alone first (`studio/_tools/previz_chain.py ... --only-previz`, 52-69 s for 769 frames) and look at the eight angles.
4. **First half, forward from the master:** `previz_chain.py --sequence F --shots 103,...,110 --frames-per 97 --draw 103,104,105,106 --seeds S --match 0.6 --start anchor_102.png`.
5. **Second half, backward from the master:** the same with `--draw 107,108,109,110 --backward --seeds S2`. Each piece is drawn in reverse from the frame the circle must END on, then reversed back, so 360° lands exactly on the master.
6. **The seam where the halves meet**, pinned at both ends: `previz_shot.draw(..., end=<first frame of the next piece>)` adds a keyframe guide at the last frame. It starts on one half's last frame and ends on the other half's first.
7. **The prompt.** Describe her from behind as well as the front (jetpack, the cape's side, the braid). Light from all sides ("neon tubes on the piers rim-light her from every side, so from behind the velvet and the brass stay visible"). Name each object the previz room has (shelves of books, barrels, a lantern table); otherwise the painter invents neon wireframes.
8. **Trims.** Drop the first frame of every piece after the first (`"trim": {"in": 0.0417}`): it repeats the join.

## Checks before picking

- Board the frame each piece ends on (45°, 90°, ... 360°). She must TURN: front, profile, back, profile, front. If she keeps facing the lens while the room slides, the stand-in had no front.
- Measure every join (last frame vs next first frame, Lab mean and mean pixel difference): 2-5 pixel levels inside a half after trimming, about 2.5 at the pinned seam. The unpinned meeting of two halves measured 23.7.
- 360° must BE the master frame (6.9 pixel levels in the final: the master at another size).
- The back of the costume: the jetpack, the side the cape hangs on, the braid.

## Progression

### 2026-08-08 · VIDEO_RULES PICTURE-04 · the `orbit` preset in roll.py · grade F
- **Did:** the preset.
- **Got:** a render byte-identical to a static one (mean absolute difference 0.00).
- **Learned:** it needs a depth pass.

### 2026-09-05 · §50, §53 · the /film builder's orbit, a 2D stand-in · grade D
- **Did:** a lateral drift with a counter-zoom and a hair of roll, as a post move.
- **Got:** it reads as an 11% pan; no parallax (the plate is flat); same person 0.64 → 0.60.
- **Learned:** a flat plate cannot orbit.

### 2026-09-30 · cyber-alchemist 104 · angles-LoRA keys + first-last between them · grade D
- **Did:** turned the master to seven azimuths with the multiple-angles LoRA (`studio/_tools/flf_shots.py keys`, 6-12 s each; the keys were a consistent turn), then rendered the 45° segment k1→k2 on LTX-2.5 first-last (`workflows/72_ltx25_flf2v.json`) and H3 first-last (`workflows/65_minimax_h3_fl_turbo_v4.json`).
- **Got:** both engines turned her figure and cross-faded the room. Mid-segment (1.5-2.1 s) two sets of benches are visible at once.
- **Learned:** every key invents the room behind her again, so there is no single space for a first-last engine to move through.

### 2026-09-30 · cyber-alchemist 103 · previz with a primitive stand-in · grade C
- **Did:** a Blender previz around a cone-and-ball figure in a room laid out like the master; LTX-2.3 IC-LoRA (`workflows/74_ltx23_ic_lora_control.json`) from the master, 97 frames. Also tested a start frame dressed from the previz by Qwen-Image: same result.
- **Got:** motion agreement r = 0.94. The room orbited with real parallax, but after 45° she still faced the lens.
- **Learned:** the depth guide has to carry her orientation. A cone has no front.

### 2026-09-30 · cyber-alchemist 103-110 seed 11 · her mesh, eight hops forward · grade C+
- **Did:** her Hunyuan3D mesh as the figure; eight pieces chained forward from the master, each from the previous piece's last frame.
- **Got:** she turns properly: profile with the jetpack, back, round again. But the picture darkened with every hop. Unnamed grey blocks became glowing neon wireframes. At 360° she came back looking like someone else.
- **Learned:** drift compounds per hop, in exposure and in identity. The first mesh previz also put a lamp pole in front of her for a quarter of the turn, so the scene was changed to keep tall props off the camera's path.

### 2026-09-30 · seeds 303 and 404 · named props, all-round light, colour pull · grade B-
- **Did:** the prompt named the room's objects and asked for rim light from every side. Seed 404 also pulled each start frame 60% toward the master's Lab mean and spread (`--match 0.6`).
- **Got:** bookshelves and barrels instead of wireframes. Seed 404 kept the crimson coat and brass jetpack readable from behind. At 360° it was still a slightly different woman.
- **Learned:** words fix what the painter invents; the colour pull holds exposure; neither fixes identity after eight hops.

### 2026-09-30 · cyber-alchemist final · two halves from the master, pinned seam · grade A-
- **Did:** forward 103-106 (seed 404, match 0.6), backward 107-110 (seed 606, match 0.6), and piece 107 redrawn pinned at both ends (seed 11).
- **Got:** a circle that closes on the master. The seam where the halves meet went from 23.7 to 2.4 and 2.5 pixel levels. In the pinned piece the lamp dims over about a second as the camera passes behind her, and the back half stays darker than the front.
- **Learned:** draw a long move from the frame you trust in both directions, and pin the piece where they meet.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the room cross-fades mid-move | first-last between keys that each re-invented the room | previz + IC-LoRA | cyber-alchemist 104 A/B |
| the room turns, she keeps facing the lens | the depth stand-in has no front | her real mesh (Hunyuan3D from her sheet) | 103 cone test |
| darker at every hop | each hop starts on a darker end frame | `--match 0.6`; two halves | seeds 11, 303 |
| unnamed blocks painted as neon wireframes | the painter guesses what a grey block is | name the props in the prompt | seed 11 |
| a lamp in front of her for a quarter of the turn | a tall prop on the camera's path | keep tall props off that side of the circle | first mesh previz |
| a different woman at 360° | eight hops of drift | two halves from the master | seed 303 |
| a jump where the halves meet | two separate paintings of her back | redraw the meeting piece pinned at both ends | 106/107: 23.7 → 2.4 |
| a piece fails ("conditioning frames exceed the length") or draws the wrong start | two drivers wrote the same ComfyUI input file names | per-take input names in `previz_shot.draw` (fixed) | 108 seed 505 |

## Evidence

- Takes (box-local): `studio/samples/fight/cyber-alchemist/pv_103..106_s404.mp4`, `pvj_107_s11.mp4`, `pv_108..110_s606.mp4`; the previz and its pieces in `previz_103-110/`; `previz_103-110_chains.jpg`.
- The orbit board, one frame every 45°: `challenge-films-2026-09-30/cyber-alchemist_orbit_board.jpg` (local deliverables folder).
- Tools: `studio/_tools/previz_blender.py`, `studio/_tools/previz_chain.py`, `studio/_tools/previz_shot.py`, `studio/_tools/flf_shots.py` (the rejected keys route).
- The review: [2026-09-30 challenge films](../reviews/2026-09-30-challenge-films.md).
- `craft/VIDEO_RULES.md` (PICTURE-04); `studio/shot_catalog.json` (`orbit`).

## Open questions

- A circle round a MOVING subject (the Courier's "circle her as she flies"): the previz would have to animate her path too. Not tried.
- Four longer pieces (193 frames) against eight (fewer hops): not measured.
- Whether matching exposure on every frame, not only each start frame, removes the darker back half.
