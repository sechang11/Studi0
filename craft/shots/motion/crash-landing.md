# A body crashing down into the ground (`move-crash-landing`)

| family | status | last tested | best result |
|---|---|---|---|
| motion | works-with-caveats | 2026-10-01 | the duel in the clearing F10, keyed: a meteor streak, an impact frame, him crouched in a ring of flying dirt, 2 of 2, grade A- |

**Also called:** crash landing, meteor landing, meteor crash, crater landing, superhero landing, slammed into the ground, crashes down from the sky
**Not the same as:**
- [`fx-impact-burst`](../fx/impact-burst.md) - the debris a strike throws; here a whole body arrives from above and the ground takes it
- [`move-fight`](../motion/fight.md) - blows between two fighters standing on the ground

## Recipe (v1, 2026-10-01)

Never by words alone: paint the moment of impact - the body down on one knee or flat, the ground erupting round it - as a key into the shot's own frame and anchor it a few frames in ([`pipe-key-poses`](../pipeline/key-poses.md)).

1. The frames: the place before (empty, or the others in it) and after (the body standing where it landed) - from the set ([`pipe-3d-set`](../pipeline/3d-set.md)).
2. The key, painted from the END frame, where the body already stands drawn from its sheet: erase anyone who arrives later first; then "has just crashed down from the sky into the middle of the path: crouched low on one knee, his fist driven into the ground, the dirt erupting around him in a ring of earth, rocks and dust flying outward, a white impact flash under his fist". Two seeds; keep one that kept the frame's look.
3. H3 first-last (`workflows/65_minimax_h3_fl_turbo_v4.json`) with the key as a `MiniMaxH3AddGuide` at frame 8-12; the shot's words as written (the meteor, the dirt, what happens after). Two seeds.
4. No crater that must outlive the shot unless the set has one: the end frame says what the ground looks like afterwards.

## Checks before picking

- The body is seen arriving - a streak, a fall - not appearing in the dust after a flash.
- The ground after the impact matches the end frame.

## Progression

### 2026-10-01 · the duel in the clearing F10 · "the jester crashes down into the path like a meteor" · grade D
- **Did:** H3 between the empty path and both of them standing on it, the battle dialect; words for the crash, a crater and a ring of earth on seeds 11 and 202, re-worded "crashes down into the path like a meteor" on 3003 and 4242.
- **Got:** 4 of 4 a pillar of light from the sky, then dust; he appears standing in it afterwards and is never seen landing. The end frame's path is whole - the set has no crater - so a crater would have had to vanish.
- **Learned:** an impact from above is a pillar of light to H3, however it is worded.

### 2026-10-01 · the duel in the clearing F10, keyed · one painted frame of the impact · grade A-
- **Did:** the key (step 2) anchored at frame 10 of 73, the same words, seeds 11 and 202 ([`pipe-key-poses`](../pipeline/key-poses.md)).
- **Got:** 2 of 2 him crashing in: s7011 a red-gold meteor streak, a white impact frame, him crouched in a ring of flying dirt, springing up as she lands beyond him; s7202 a short flash with him inside it, then the same. s7011 is in the film (`studio/samples/fight/forest-duel/h3f_F10_s7011.mp4`).
- **Learned:** draw the impact once; the engine draws the fall into it and the dust out of it.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a pillar of light from the sky; the body appears in the dust afterwards | an impact from above told in words | a key of the body at impact | F10, 4 of 4; a landing from a posed mid-air first frame, 1 of 2 |

## Evidence

- `studio/samples/fight/forest-duel/keys_F10/` (`board.jpg`, `s7011_frames.jpg`), `h3f_F10_s*.mp4`; `studio/LTX_PLAYBOOK.md` §100.9, §100.10.

## Open questions

- A crater that stays: a `crater` event in the set, so later shots keep it.
