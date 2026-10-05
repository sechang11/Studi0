# A scene inside one 3D set (`pipe-3d-set`)

| family | status | last tested | best result |
|---|---|---|---|
| pipeline | works-with-caveats | 2026-10-01 | plaza test: eight shots in one set, grade B+; a fight with physics in a forest set, grade B; frames first (the set gives the frames, H3 acts), grade A- |

**Also called:** 3D set, 3D map, one world for every shot, shared set, set-based scene, world model, Astra set, scene geometry, plaza test
**Not the same as:**
- [`pipe-previz`](previz.md) - previz stages one move around one subject; a set is the whole place, and every shot of the scene is a camera in it
- [`cont-place`](../continuity/place.md) - holding the place with one picture of it; a set replaces the picture with geometry, so what the picture never showed exists too

## Recipe (v2, 2026-09-30)

Build the place once in Blender; make every shot a camera in it; dress each shot's own render into a photograph from the render ALONE; draw the take with LTX-2.3 reading the render's depth; pin the last frame of every move that reveals; measure against the set.

1. **The set.** A set module like `studio/_tools/set_plaza.py`: every building with its windows, shutters, doors and roof as geometry, each building its own colour, every object tagged with a `group` (landmark) and a `surface` (group/material). A set built elsewhere - GPT-6 Astra writes Blender scenes - comes in as a `.glb` (`--set file.glb`; objects grouped by the first word of their names).
2. **The shots.** `"engine": "previz"` with `"previz": {"scene": "set", "set": "plaza", "cam": [x, y, z], "look": [x, y, z], "lens": 28}` and, for a move, `cam_to` / `look_to` / `lens_to` or `arc` + `arc_center`; `"frames": 97` (8n+1), `"masks": 8`. Pattern: `studio/shotscripts/_make_plaza_test_0930.py`. Check every framing on the map before anything else is drawn (`studio/_tools/set_test.py render` writes `map.jpg` with every camera on it; 13 s a shot).
3. **The plate.** The establishing shot's render dressed as a photograph (`set_test.py plate`, four seeds, pick by eye). It is the look, and today's way's reference if both are made.
4. **Start frames.** `set_test.py dress`: each shot's 1280x720 still dressed by Qwen-Image-2.1 (workflow 80) from the render alone, with words that name nothing ("everything in it stays exactly where it is ... add nothing and remove nothing"), three or four seeds; the seed the set's surface map fits best becomes the start frame - then LOOK at it (a fit to the render rewards a surface left CG).
5. **Steep angles** (looking far up or down): the dress straightens them. Keep the angle gentle, or draw from the set's depth alone (`pvb`, geometry exact, look invented).
6. **A character** stands in the set as her own shape: `figure_glb` (the Hunyuan3D model from her character sheet's clean front view, `/sheets`), `figure_at`, `figure_turn` (90 faces east). Never dress her in: `set_test.py cast` dresses the place without her and puts in the view of her sheet facing the camera, scaled and placed where the set projects her feet and head.
7. **Takes.** `set_test.py draw` (through `studio/_tools/previz_shot.py`): LTX-2.3 with the IC-LoRA union control (`workflows/74_ltx23_ic_lora_control.json`) reading the render's depth, two seeds, about 50 s a take. A tilt up is drawn down from the frame it ends on and played backwards (`"reverse": true`).
8. **Characters who act** (walk, leap, fight) are drawn between the set's frames, not on its depth. Jointed puppets (`studio/_tools/set_actors.py`) keyed by the set module's choreography (`"action"`, e.g. `studio/_tools/set_forest.py`) are STAND-INS: `set_test.py cast --ends` puts each character into the shot's first and last frames where its puppet stands, and the take is H3 between the two frames (`workflows/65_minimax_h3_fl_turbo_v4.json`; `set_test.py take`, with any key poses the shot script gives - [`pipe-key-poses`](key-poses.md)), or LTX-2.5 (`72`) for a walk. A whole film of such shots: `studio/_tools/set_film.py` - check, frames, takes, boards, score sections, cut. Rigid bodies still decide whatever breaks. Never a take from the start frame alone: it leaves the set (§99.10).
9. **Moves that reveal** (an orbit, a crane, a long track): `set_test.py ends` dresses the move's LAST frame from the set too, and `set_test.py pin` draws the take pinned at both ends (`pve_`). Unpinned, what the move reveals is invented.
10. **Measure.** `studio/_tools/set_measure.py --truth <set sequence> --arms ...`: fit and chance per start frame and take, colour against the plate, boards. Optionally `set_test.py match` holds each building's colour from shot to shot with the surface masks (stills: dE 10.7 -> 4.6).

## Checks before picking

- The start frame's fit is clearly above its chance (`set_measure.py`), and on the board the set's red borders land on the picture's windows, doors and edges.
- The start frame shows the render's view, not the plate's.
- Nothing is in the start frame that is not in the render (a clock face on the fountain, a tower over the cafe), and nothing is still CG (a tree left as the set's green blob).
- A take's fit holds to its last frame (hold near 1); a move that reveals arrives on the set's own look.

## Progression

### 2026-09-30 · plaza test · the plate as a look reference for every dress · grade D
- **Did:** each shot's render as `<image1>` and the plate as `<image2>` ("the buildings, their colours and the light are those of <image2>").
- **Got:** 7 of 7 shots came back as the PLATE's view (fit below chance on 104-108). Told to take "only the colours", seed 202 still copied the plate and seed 11 grafted its tower onto the cafe.
- **Learned:** never hand the dress a picture of the same place from another angle; it overrides the canvas.

### 2026-09-30 · plaza test · the render alone, words that list the set · grade C+
- **Did:** the render alone, with words naming the tower, the clock faces, the fountain, the awning.
- **Got:** the shot's own view, but the named things were put where they are not: a clock face on the fountain (108), a clock tower over the cafe (105).
- **Learned:** the dress words must name nothing.

### 2026-09-30 · plaza test · the render alone, words that name nothing · grade B+
- **Did:** "everything in it stays exactly where it is ... add nothing and remove nothing", three and then four seeds, pick by fit.
- **Got:** fit 0.26-0.59, above its chance (0.10-0.23) on six of seven shots; the set's borders land on the windows and the awning. The steep look up at the tower (104) was straightened to eye level on 8 of 8 seeds from its foot and 4 of 4 from its clock, and dressed from its base the plain shaft became a house front with a roof (4 of 4). The pink and the white houses came out beige in every shot.
- **Learned:** the edit keeps any ordinary view of the set; it will not keep a steep angle, and it weathers every wall toward the same ochre.

### 2026-09-30 · plaza test · a ControlNet start frame for the steep angle · grade D
- **Did:** Qwen-Image 2512 + InstantX ControlNet Union (canny of the render, strength 0.8, `workflows/05_qwen_controlnet.json`), words for the look, three seeds on 104 and 105.
- **Got:** fine photographs of a redesigned place (a new belfry, the cafe re-composed); fit below chance on all six.
- **Learned:** at these settings canny control suggests a layout, it does not hold one.

### 2026-09-30 · plaza test · the takes, against one plate and words · grade B+
- **Did:** each shot drawn by LTX-2.3 + IC-LoRA on the set's depth from its dressed start frame, two seeds; the orbit (106) and the crane (107) again pinned at both ends. Today's way: the same shots on LTX-2.5 from start frames composed from the plate by words (the plate turned by the angles LoRA for the reverse and the west side; the best of three candidates by fit), two seeds.
- **Got:** the picked takes fit the set at 0.43 against 0.32; over all takes, 91% of a take's fit held to its last frame against 77%; motion agreement with the set 0.52-0.99. The set's film holds one square in all eight shots (the same tower, arch, cafe and fountain); today's way grew a dome on the tower inside its own establishing take, and put a different square in most of the others (a domed tower, another arch, the cafe on a white house). Unpinned, the orbit's cafe came back as a pink house with a white awning and the crane's red awning came out white; pinned, both arrived on the set's own look (hold 96-97% and 90%, against 64-78% and 61-78%).
- **Learned:** the set holds the shapes; only a dressed frame holds the look; pin the end of every move that reveals.

### 2026-09-30 · Terra in the plaza · a character's shape in the set · grade C
- **Did:** Terra (Foundry, anime) stood east of the fountain as her Foundry `mesh.glb`; then as the Hunyuan3D model from a /sheets character sheet made from her front picture (78 s).
- **Got:** the Foundry mesh came in as a two-metre box (built from a picture with its decorative card behind her); the sheet's model is her shape. Turned 90° to face the cafe, she still faced south: the glTF importer leaves objects in quaternion mode, where an euler is ignored - every `--figure-turn` until then had done nothing (fixed in `previz_blender._import_figure`).
- **Learned:** a character's set shape comes from her sheet's clean front view; check her facing on two stills before anything else.

### 2026-09-30 · Terra in the plaza · a character dressed in from her reference · grade D
- **Did:** the set's render with her grey figure, plus her sheet's front (or back) view as `<image2>`, anime dress words.
- **Got:** the square and every added thing kept; Terra redrawn full length and centred in every shot - where the set had her cut at the knees, over her shoulder, or 57 px tall across the square (the plate drew her two to three times that).
- **Learned:** the dress takes a character's size and framing from her reference, as it took the view from the plate. Do not dress her in.

### 2026-09-30 · Terra in the plaza · a character put in by the set · grade A-
- **Did:** `set_test.py cast`: the place dressed without her; her feet and head projected through the camera; the nearest of her sheet's eight views to the camera's side of her, cut out (BiRefNet), scaled to her height there, on her feet with a soft shadow.
- **Got:** start frames fit the set at 0.55 against chance 0.14 (over her shoulder 0.80); the set's border traces her outline; the right side of her in every shot (back-right from 155° round, front-right and front-left at the arc's two ends).
- **Learned:** the set places the character; her sheet supplies the picture.

### 2026-09-30 · Terra in the plaza · four takes, 2D anime, things added · grade B+
- **Did:** four shots (the square from above, her face, over her shoulder, the camera circling her pinned at both ends) on LTX-2.3 IC-LoRA, two seeds; a fruit stall, a bicycle, pots and strings of lights added to the set (`set_plaza_market.py`).
- **Got:** the takes kept 91% of their fit; her hair, dress and sash held in every shot; the added things stayed where the set put them; the anime look held through every take; the arc turned her as the set does (its motion r came out negative, -0.29/-0.36, a measure to look into). Mid-arc the white house drifted to a minty grey.
- **Learned:** a character and added things hold like the buildings once the set places them.

### 2026-09-30 · plaza test · colour held by the surface masks (stills only) · grade n/a
- **Did:** each key surface of each start frame pulled toward its colour in a look book (the plate, then the first shot that shows it), a and b fully, L by half, feathered 6 px (`set_test.py match`).
- **Got:** dE against the plate 10.7 -> 4.6; the largest dE between two shots per surface 14.6 -> 6.9 on average (the yellow house 43.3 -> 21.9); no visible seams.
- **Learned:** the set's masks can hold a building's colour from shot to shot; not yet drawn through a take.

### 2026-09-30 · the jester in the wood · characters who move, and physics, in a set · grade B
- **Did:** a forest set (~700 trees, a path, a huge oak pre-fractured at fireball height) and seven shots of a fight: Terra and a new harlequin jester as jointed puppets (`studio/_tools/set_actors.py`) keyed by each shot's choreography (`studio/_tools/set_forest.py`), rigid bodies for leaves, twigs, pebbles, bark and the falling oak; start frames composed by `cast`; LTX-2.3 IC-LoRA takes, two seeds.
- **Got:** start frames fit the set at 0.44 against chance 0.14; the moves followed the choreography (blows r 0.97-0.99, the leap 0.91-0.94, the fire and the fall 0.86-0.95); the oak fell across the path and the next shot was set in its wreckage. Unpinned, the characters drifted in 4 of 6 shots (her hair narrowed to the puppet's and turned magenta, his costume became a bare torso); pinned at both ends, all seven held. The blast, a solid glowing sphere, came out as dark red blobs.
- **Learned:** the puppet's depth carries the motion and never the look: pin both ends of every shot with a character in it, and give each character colours the other's words never use.

### 2026-09-30 · the jester in the wood, again · frames first: the set gives the frames, the engine acts · grade A-
- **Did:** three of the scene's shots (her walk, his drop, the blows) redrawn with the set giving only the first and last frames (`cast --ends`) and an engine acting between them - H3 (`65`), LTX-2.5 (`72`), each engine from the start frame alone, and LTX-2.3 on the puppets' pose skeleton (`previz_blender.py --joints`) - against the old takes on the puppets' depth; two seeds, 22 takes.
- **Got:** between the frames H3 walked her with real steps, leapt him down to a crouch facing her, and played the blows as a lunge, a kick and a skid back through the dust - 2 of 2 seeds each. The place held to the pinned ends (by eye the same forest; mid-take fit 0.28-0.39 against the old way's 0.34-0.37). From the start frame alone the engines left the set (LTX-2.5 pushed in on the walk, H3 ignored the camera move). The skeleton freed the costume and kept the puppets' crude motion.
- **Learned:** the set gives the frames and the engine acts; both ends always; the set's depth only for the camera's own shots.

### 2026-10-01 · the duel in the clearing · a set at scale: 58 shots, frames first · grade B+
- **Did:** a clearing cut into the forest set (`studio/_tools/set_duel.py`) with breakable trees, a pre-cracked boulder and the first film's oak; every shot's choreography in the film's acts file (marks at both ends, the events it sets off); only frames 1 and N rendered (`previz_blender.py --endpoints`); wreckage cached; an in-frame check of every character before any render (`set_film.py check`); one painting for both frames of a still shot (`cast --same-bg`); H3 between the frames.
- **Got:** the 30-second fight in about an hour of card; the long version - see §100.
- **Learned:** a camera behind the clearing's ring of stones, a close-up shot from behind her head, a character behind the lens - the map does not show them, the in-frame check and the frames do.

### 2026-10-05 · the ember thief · 20 shots, one line of action, the cast's views fixed · grade A-
- **Did:** the clearing again, a story-first minute ([`cont-shot-chain`](../continuity/shot-chain.md)); every camera east of the line between the two of them ([`cont-screen-direction`](../continuity/screen-direction.md)), checked by the maker before anything rendered.
- **Got:** the frames came out facing the right way for the first time: `set_test.py cast` had pasted every side and three-quarter view MIRRORED (the sheets name views by the camera's orbit, the cast read them by the character's side) - fixed, plus a mirrored twin where a sheet drew both three-quarters facing one way. Twenty shots' frames in 6 minutes.
- **Learned:** look at what the frames draw, not what the marks say; a set shot with nobody in it is legal (it crashed the cast - fixed); `set_test.py render` keeps an existing shot unless `--force` (a moved mark rendered nothing new until forced).

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a standing stone fills half the frame | the camera stood behind the ring of stones | look at the two frames of every shot before a take; `set_film.py check` | forest-duel D05, D10 |
| the close-up shows the back of her head | the camera placed behind the way she faces | put the close-up camera along her line of sight | forest-duel F07c |
| a character pasted at random | her mark behind the camera | `set_film.py check` flags it before anything renders | forest-duel F11b |
| the wood changes during a still shot | its two frames dressed one at a time | `cast --ends --same-bg` | forest-duel E01 |
| characters cut off at the knees by a log that is not in the picture | `cast --occlude`: the set's depth hides them behind geometry the dress did not paint | occlusion off (the default); where the set truly hides them, move the camera | forest-duel E07; F15 (hidden whole, truly) |
| a character acts like a puppet: a shuffle for a walk, a plank of a leap, a tube for a skirt | the take follows the puppets' depth | draw the shot between the set's frames (§99.10) | forest 302, 304 |
| the take leaves the set: the camera pushes in, or stands still where the set moves | a take from the start frame alone | pin the end frame too | forest 302 (LTX-2.5), 304 (H3) |
| a skeleton take still moves like the puppet | the skeleton was taken from hand-keyed puppets | real motion on the set's marks (open) | forest 302, 304 |
| a character's hair or costume drifts during a take | the puppet's depth is all the take reads between the frames | pin both ends (`cast --ends`, `pin`) | forest 302, 304, 305, 307 |
| one character comes back in another's colour | a colour in one character's words ("magenta hair") | describe each by colours the other does not have | forest 304, 307 |
| the fallen tree lands on its crown and flips | the whole tree's convex hull as its physics shape | the trunk alone as the body, the tree parented to it | forest 307 v1 |
| the whole set renders black | a world fog volume in Eevee (density 0.012) | no world volume; the dress paints mist | forest, first renders |
| the dressed frame shows the plate's view | the plate given as a second picture | the render alone | plaza 102-108 |
| things appear that are not in view | the dress words list the set's objects | words that name nothing | plaza 105, 108 |
| a steep angle comes back level | the edit model straightens perspective | a gentler angle, or the depth alone (`pvb`) | plaza 104 |
| a tower's shaft becomes a house with a roof | the frame cuts a plain shaft | start on its distinctive part and reverse | plaza 104 |
| what a move reveals is invented (a pink cafe) | only the start frame carries the look | pin the move's last frame (`ends` + `pin`) | plaza 106, 107 |
| the best-fitting start frame has a CG tree | a fit to the render rewards what was left unpainted | look at the pick; take the next seed | plaza 108 |
| every wall weathers to the same ochre | "weathered plaster" and the warm grade | untested: say each wall keeps its own paint colour | plaza, the pink and white houses |
| the same building changes colour between shots | each dress weathers on its own | a colour match by the surface masks (`match`, stills tested) | plaza, the yellow house |
| a character's set shape is a box | her mesh was built from a picture with a background | a model from her sheet's clean front view | Terra (Foundry `mesh.glb`) |
| `--figure-turn` does nothing | glTF objects come in quaternion mode | set `rotation_mode = "XYZ"` first (fixed) | Terra; the cyber-alchemist orbit's turn 35 never took |
| the character is full length and centred whatever the shot | the dress takes her size and framing from her reference | `set_test.py cast`: place dressed without her, her sheet's view put in by the set | Terra 201-204 |
| a character in profile faces away from the one she fights | the cast read the sheets' turnaround names mirrored | VIEWS8 fixed 2026-10-05 (`set_test.py`) | forest-duel D07; every set film before 2026-10-05 |
| a three-quarter view faces the wrong way on one side only | the sheet drew both three-quarters facing one way | `_same_facing`: the twin mirrored | Terra's turn_front_l, the jester's turn_back_l |
| a shot with nobody in it stops the cast (KeyError 'figure_sheet') | no figures fell back to the single-statue path | fixed: an empty place, dressed at both ends | ember-thief 120 |
| a moved mark changes nothing | `render` keeps an existing shot | `render --force` | ember-thief 110-180 |
| a character drawn from behind in their own shot | the camera ended up behind them after a mark moved | the maker's check names back views | ember-thief 160 |

## Evidence

- `studio/_tools/set_plaza.py`, `studio/_tools/set_plaza_market.py`, `studio/_tools/set_test.py`, `studio/_tools/set_measure.py`, `studio/_tools/previz_blender.py`, `studio/_tools/previz_shot.py`, `studio/shotscripts/_make_plaza_test_0930.py` (writes `plaza-set.json` and `plaza-words.json`), `studio/shotscripts/_make_plaza_terra_0930.py` (`plaza-terra.json`). The playbook's §99.
- `studio/_tools/set_actors.py`, `studio/_tools/set_forest.py`, `studio/shotscripts/_make_forest_fight_0930.py` (`forest-fight.json`); the jester's sheet `studio/sheets/forest-fight-the-jester/`; the playbook's §99.9.
- Box-local: `studio/samples/fight/forest-fight/frames_test/` (the 22 takes of §99.10, compare_302/304/305.mp4, the recut, measure.json), `studio/samples/settest/work/forest_frames.py`; the joints: `studio/_tools/previz_blender.py --joints`.
- Box-local: `studio/samples/fight/forest-fight/` (forest-fight_filmic.mp4), `studio/samples/fight/plaza-terra/` (plaza-terra_filmic.mp4, measure/), Terra's sheet `studio/sheets/terra-in-the-plaza-terra/`.
- Box-local: `studio/samples/fight/plaza-set/` (map.jpg, plate_board.jpg, measure/starts.jpg, measure/landmarks.jpg, measure/takes.jpg, plaza_compare.mp4, plaza-set_filmic.mp4, measure.json), `studio/samples/fight/plaza-words/` (plaza-words_filmic.mp4).

## Open questions

- A set built by GPT-6 Astra (more detail) against a hand-written one.
- The colour match drawn through a take; dress words that keep each wall's paint.
- A character who moves in the set: a walk needs a rigged figure under the depth, not a statue.
- A steep angle kept by a stronger control (ControlNet strength 1.0, more steps).
