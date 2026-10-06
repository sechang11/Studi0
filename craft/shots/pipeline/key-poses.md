# Key poses: the blow drawn, the engine in-betweening (`pipe-key-poses`)

| family | status | last tested | best result |
|---|---|---|---|
| pipeline | works-with-caveats | 2026-10-05 | forest 305: four keys on their frames, 2 of 2, the whole exchange on a chosen timeline, grade A; the duel's F10 meteor, keyed, 2 of 2 where words failed 4 of 4, grade A- |

**Also called:** key pose, key poses, posed keyframe, mid-take anchor, guide frame, AddGuide, drawn choreography
**Not the same as:**
- [`pipe-first-last`](first-last.md) - first-last pins a shot's two ends; a key pins a frame between them, in a pose that no reference shows
- [`move-fight`](../motion/fight.md) - the choreography itself; keys are one way of fixing it to frames
- [`pipe-edit-fix`](edit-fix.md) - an edit that repairs a picture; a key is a shot's frame edited into a pose that never existed

## Recipe (v2, 2026-10-01)

Write each blow as a key in the shot script, paint it with `set_test.py key`, look at the board, pick a seed, and draw the shot with `set_test.py take` - H3 first-last (`65`) with a `MiniMaxH3AddGuide` at every key; keep the numbered beat list as the words.

0. **The tool.** In the shot: `"keys": [{"at": 10, "from": "end", "erase": "...", "pose": "...", "fx": "...", "seed": 202}]` (`"fx"` optional: a last edit for the impact flash at the contact, for a dense flurry) (`"at"` is the take's frame, or `"end"` for a posed last frame; `"from"` is `"start"`, `"end"` or an earlier key's frame). `python3 studio/_tools/set_test.py --sequence <film> key --only <id> --seeds 11 202 3003` paints, grades and boards (`keys_<id>/keys.jpg`, a key over x3.5 its source's detail flagged RESTYLED?); then `take --only <id>` (`h3k_<id>_s<seed>.mp4`). Pattern: F10 in `studio/shotscripts/_make_forest_duel_1001.py`. Steps 1-5 are what the stages do.

1. **The frames.** The shot's first and last frames from the set (`set_test.py cast --ends`, [`pipe-3d-set`](3d-set.md)).
2. **Paint each key** with Qwen-Image-2.1 edit (`workflows/80_qwen21_edit_refs.json`, `set_test.dress_one`), two seeds. The words: the pose, then "Everything else - the forest, the path, the light, both of their costumes, faces and colours - stays exactly as it is; same camera, same framing." Paint from the frame where the character already stands nearest the pose:
   - a lunge a short way across: from the start frame;
   - a pose in place (a wind-up, a crouch at the mark): from the frame where they stand there, start or end;
   - a pose far across the frame: paint it, then erase the copy left at the mark in a second edit ("remove the jester standing upright at the far right ... fill in the forest, the path and the light behind him");
   - someone who arrives later in the shot: erase them first, then pose the other.
3. **Grade each key to the start frame** (LAB mean and spread; a second edit pass adds contrast): `matched()` in `studio/samples/settest/work/keypose.py`.
4. **The take.** Workflow `65`, plus one `MiniMaxH3AddGuide` per key: `positive` from node 20 (or the previous guide), `latent` node 20's, `vae` node 3, `frame_idx` the frame the blow lands on; the last guide into the guider (node 30). The numbered beat list stays the words ([`move-fight`](../motion/fight.md), §100.1): the keys do not replace it. Two seeds. Patterns: `take()` in `keypose.py` (several keys), `studio/samples/settest/work/keypose_shot.py` (one key in a duel shot, saved as `h3f_<shot>_s70NN.mp4` beside its other takes).
5. **Not workflow `83`.** It is reference-to-video: its first image is a subject reference ("motifs, not layout"), not the first frame.

## Checks before picking

- Every key before it goes in: one of each character (count them); the part of the frame the words did not touch still its source (compare them side by side; the board's detail ratio flags a whole-frame restyle over x3.5); faces and costumes on model.
- Every take: step through the key's frame - the blow is there, with a run-up drawn into it and a follow-through out of it, not a still pasted in; the end frame still reached.

## Progression

### 2026-10-01 · the jester in the wood 305 · two keys against words alone · grade A-
- **Did:** the exchange between its two set frames (H3 `65`, 90 frames), with two keys painted into its start frame - his punch landing on her (frame 20) and her kick in his chest (frame 44) - against the takes of §100.1 between the same frames; words {L1 "they fight", L4 six numbered beats} x {no keys, keys}, seeds 11 and 202 (`studio/samples/fight/forest-fight/keypose/board.jpg`).
- **Got:** both keys on their frames in 4 of 4 keyed takes; L4 alone put the kick at frame 36 on both seeds. H3 drew a flying lunge into the punch, an impact burst out of it, a pivot into the kick and the launch out of it, on twos like the rest of the take. With "they fight" the keys still came with hits (an impact ring, him knocked into the air), then he walked back to his mark: no skid, no crouch. With the six beats: all six, on the keys' frames.
- **Learned:** a key fixes the pose and the frame; the words still say what the blow does. Keys plus the beat list is the most a shot can be told.

### 2026-10-01 · the jester in the wood 305 · four keys in one shot · grade A
- **Did:** the six beats with four keys - his wind-up at frame 8 and his skid-stop crouch at 64 (poses in place, painted from the start and end frames), the punch at 20, the kick at 44; seeds 11 and 202 (`studio/samples/fight/forest-fight/keypose/board4.jpg`).
- **Got:** all four on their frames, 2 of 2. Between them: the spring out of the wind-up, the punch, the pivot, the kick, the launch, the skid into the crouch, the straighten into the end frame - no step in the frame-to-frame change at a pose-in-place key. With two keys the skid and the crouch came on the engine's own timing.
- **Learned:** a key every 12-24 frames holds; the whole exchange can run on a timeline chosen beforehand.

### 2026-10-01 · a shot that starts mid-air · a posed FIRST frame · grade B+
- **Did:** D07's end frame edited so the jester is high in the air, upside down mid-somersault; H3 from it to the set's end frame (him standing at his mark), words for the rest of the flip, the landing and the spring up (`studio/samples/settest/work/firstkey_test.py`); seeds 11 and 202.
- **Got:** 2 of 2 carried the airborne motion on - the flip completed, the drop, crouched in a puff of dust, springing up into the end frame. The landing: a white impact flash on 202, a pillar of light on 11 (the [`move-crash-landing`](../motion/crash-landing.md) habit).
- **Learned:** a posed first frame starts a shot mid-action; key the landing too if it must not become a beam of light.

### 2026-10-01 · a flurry in place · six keys a quarter second apart · grade B+
- **Did:** both fighters at D07's end marks (its end frame first and last), six blows in numbered beats, against the same words with a key on every blow every 6 frames, frames 12-42; seeds 11 and 202 (`studio/samples/settest/work/flurry_test.py`).
- **Got:** every key on its frame, 2 of 2, with real in-betweens on twos; but calm - frame-to-frame 5-14 against the words-only frenzy of impact flashes and smears (6-70), whose blows read only roughly.
- **Learned:** keys hold a quarter second apart; dense keys trade the battle energy for precision.

### 2026-10-01 · a flurry in place · the same six keys with the impact flash painted in · grade A-
- **Did:** a second Qwen edit on each flurry key: a huge white impact flash where the blow lands, radiating speed lines across the frame, a shockwave ring (`flurry_test.py fxkeys`); seeds 11 and 202.
- **Got:** every blow on its frame, 2 of 2, and the frenzy back: frame-to-frame 0-57 (plain keys 5-14, words alone 6-70), impact bursts on the keys, rings and smears between. The speed lines carry through the in-betweens - a near-constant speed-line backdrop.
- **Learned:** the dialect a dense key lacks can be painted into it; precision and frenzy together.

### 2026-10-01 · a flurry in place · the flash painted at the contact only · grade A
- **Did:** the six flurry keys with a LOCAL impact flash instead ("a small shockwave ring and a few short speed lines right around the contact only"; `flurry_test.py flkeys`); seeds 11 and 202.
- **Got:** every blow on its frame, 2 of 2; bursts, rings and whoosh arcs at the hits and a clean forest between them - frame-to-frame mean 8.5 / 11.1 (plain keys 5.5 / 7.4, full-frame flash 12.2 / 17.8, words 12.7 / 21.2).
- **Learned:** paint the flash where the blow lands, not across the frame: the energy stays on the hits.

### 2026-10-01 · the duel in the clearing D07 · three keys and a posed end, through the stages · grade A-
- **Did:** the flurry re-staged (see [`move-fight`](../motion/fight.md)): keys at frames 20 and 42 and an end key, each a pose in place at the end marks, painted on seeds 11, 202, 3003 (`set_test.py key`), seed 11 picked, then `take`.
- **Got:** seed 202 restyled all three (flagged x4.4-4.5). The first end key turned her toward the camera and swapped her red boots for sandals; the take swung her round to face the camera on its way into the lock, 2 of 2. Re-worded ("side-on to the camera, in profile ... knee-high red boots"), the boots held; the turn became a pirouette into the lock.
- **Learned:** an edited end frame is a redrawing: name the facing and the costume the editor must keep.

### 2026-10-01 · the duel orbit test O01 · a posed END frame · grade A-
- **Did:** a shot whose six beats end in an arm-lock, the set's end frame showing them standing apart; the end frame edited into the lock (Qwen edit, two seeds, one kept the look) and the take pinned to it instead (`studio/samples/settest/work/orbit_key.py`); H3 seeds 11 and 202.
- **Got:** with the set's end frame, 2 of 2 locked at frame 50 and then pulled apart to match it; with the posed end frame, 2 of 2 ended IN the lock, straining, held to the last frame.
- **Learned:** the end frame wins over the last beat - paint the last beat into it.

### 2026-10-01 · the duel orbit test O01 · keys as camera waypoints · grade B-
- **Did:** the set's camera at take frames 30 and 60 of a 120° orbit rendered and cast, each edited into that moment's blow, anchored there ([`cam-arc`](../camera/arc.md), `orbit_way.py`).
- **Got:** every view in order, 2 of 2, in steps - the first key held ~16 frames, then a slide on.
- **Learned:** a key carries the camera too; keys at different camera positions are different paintings, and the engine parks on each.

### 2026-10-01 · keys as stages of `set_test.py` · F10 again, through the tool · grade n/a
- **Did:** `set_test.py key` and `take` (the spec in the shot script); F10's key repainted on seeds 11 and 202, once with the dress's negative prompt and once with one fit for anime.
- **Got:** the two negatives gave pixel-identical keys - workflow `80` samples at CFG 1, the negative never reaches it. The restyled seed flagged at x5.83 its source's detail, the kept one x2.25 (calibrated on six keys judged by eye: restyled x4.4-5.9, kept x0.9-2.6). The take through the stages drew the meteor crash again.
- **Learned:** the restyle belongs to a seed on a frame; catch it by detail, pick another seed.

### 2026-10-01 · painting the keys for 305 and F10 · Qwen-Image-2.1 edit, two seeds each · grade n/a
- **Did:** keys painted from the shots' own frames.
- **Got:** the lunge from the start frame, 2 of 2. The kick, which needed him across the frame: 2 of 2 added a SECOND jester, the first left standing at his mark. Painted from the punch key instead, it kept his punch and its flash, 2 of 2. The duplicate erased by a second edit: 2 of 2 clean, a little more contrast. Poses in place (his wind-up at his start mark, his skid-stop crouch at his end mark): 4 of 4 clean. On F10 one seed restyled the whole frame - another palette, another hand - on both of its edits.
- **Learned:** the editor moves a character a short way; across the frame it adds one. It keeps whatever the words do not change. Erasing is what it does best. Look at every key.

### 2026-10-01 · the duel in the clearing F10 · the meteor that words could not draw · grade A-
- **Did:** [`move-crash-landing`](../motion/crash-landing.md): one key - the jester crashed down on one knee, his fist in the ground, dirt erupting under a white flash - painted from the shot's end frame with her erased first (she lands later), anchored at frame 10 of 73, the shot's own words (`keypose_shot.py`, `studio/samples/fight/forest-duel/keys_F10/board.jpg`).
- **Got:** words alone, 4 of 4 a pillar of light with him appearing afterwards in the dust; keyed, 2 of 2 HIM crashing in - s7011 a red-gold meteor streak, an impact frame, him crouched in a ring of flying dirt, springing up as she lands beyond him. It replaced the old take in the film.
- **Learned:** what no wording makes the engine draw, one painted frame of it can.

### 2026-10-05 · the ember thief 050, 060, 110, 140 · every contact keyed, one copy erased · grade A-
- **Did:** keys for the three contacts - her hook at f30 (050), his palm at f14 (060), her uppercut as 110's last frame - and the catch as 140's last frame; two seeds each, the restyled seed (flagged x4.0-5.3) thrown away every time.
- **Got:** all four land on their frames on both seeds; 110 ends ON the uppercut (an impact burst) so the cut to the pendant flying is a cut on the action. 060's kept seed drew the jester twice - lunging, and still standing where he had been: a key's `"fx"` may now be a list, and a second edit removed the copy. For the uppercut his mark was moved to 0.9 m in front of her so the key could be painted from the end frame without moving anyone across it.
- **Learned:** pose a key from a frame in which the two are already within reach; erase a pose's leftover copy with a second edit, not a new seed.

### 2026-10-05 · the fire esper · the poses a relay needs, the first frame keyed too · grade A-
- **Did:** 16 keys in 10 shots of THE FIRE ESPER - the set's cast draws everyone standing, arms down, eyes open, so the prayer (020, 060, 090, 210, 220), a circle of runes round her feet (050), a flock in the sky (070), his fear (080), the column of fire in the esper's place (100) and her kneel (230) were painted. Two new mechanics in `set_test.py`: `"at": "start"` replaces the FIRST frame; `"from": "key:start"` paints a key from a key made before it, so both frames share one pose (060, 090, 220). 100 ran it backwards: the last frame (the esper beside her) painted first, then the first frame from it - "replace the demon with a column of fire as tall, in the same place" - and H3 grew the esper out of the column.
- **Got:** every keyed shot holds its pose or its change; one seed of the editor repainted the whole frame on 9 of the 10 shots (flagged by the detail ratio, 3.6-6.9) - the other seed was clean each time. 050's circle came out paler than the shot it echoes; 220's "the glow has faded" barely dimmed it.
- **Learned:** paint the END state of a beat into the last frame (080's grin came back when the last frame was the grin); key from a key when two frames must share a pose; a removal ("the light is gone") is weak on this editor.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a second copy of a character in the key | the pose needs them across the frame; the editor adds one rather than moving them | paint, then erase the copy left at the mark | 305 key B, 2 of 2 |
| the key keeps the previous blow (his fist out, its flash) | painted from the previous key: the editor keeps what the words do not change | paint from the frame where the character stands; erase what must go | 305 key C, 2 of 2 |
| the key in another palette and hand | the editor restyled the whole frame on one seed - which seed depends on the frame; not the words, not the negative (CFG 1) | the board flags it (detail over x3.5 its source's); take another seed | F10 and O01, seed 11; O01a, seed 202 |
| a key brighter and crisper than the shot | a second edit pass adds contrast | grade the key to the start frame (LAB mean and spread) | 305 key D |
| the blows land but nothing follows from them | keys with "they fight" | keep the numbered beat list | 305 L1 + keys, 2 of 2 |
| the shot's last beat undone at the end | the set's end frame shows them standing | paint the last beat into the end frame | duel orbit O01, 2 of 2 |
| a prop nobody has (a whip) | the editor reads a verb as a prop ("whips a backfist") | plain verbs; "his hands are empty" | duel orbit O01b, 2 of 2 |
| a costume detail changes in a posed frame (boots to sandals) and the take swings her round into it | the editor redraws a figure it poses | name the facing and the costume in the key's words | forest-duel D07 end key |
| the first frame is not the shot's | workflow `83`: its first image is a subject reference | `65` plus a guide per key | 305, before the first take |
| the posed character is also still standing where he was | the editor drew the pose as a second figure | a second edit removes the copy (`"fx"` as a list) | ember-thief 060 seed 202 |

## Evidence

- `studio/samples/fight/forest-fight/keypose/` (the keys, the takes, `board.jpg`, `board4.jpg`), `studio/samples/fight/forest-duel/keys_F10/`, `h3f_F10_s7011.mp4`; the guide node: `MiniMaxH3AddGuide` in ComfyUI's `comfy_extras/nodes_minimax_h3.py`; `studio/LTX_PLAYBOOK.md` §100.10.

## Open questions

