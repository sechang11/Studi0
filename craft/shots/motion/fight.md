# A fight beat (`move-fight`)

| family | status | last tested | best result |
|---|---|---|---|
| motion | works-with-caveats | 2026-10-01 | fight_words L4: six told beats, 6 of 6 on 2 of 2 seeds (§100.1); four key poses on their frames 2 of 2 (§100.10); the duel in the clearing (§100), grade A- |

**Also called:** fight, punch, strike, combo, brawl, action beat, martial arts
**Not the same as:**
- [`style-shonen-battle`](../style/shonen-battle.md) - the genre's marks on a fight, not the choreography
- [`fx-impact-burst`](../fx/impact-burst.md) - the dust or ash at the moment of a strike
- [`frame-wide-with-figure`](../framing/wide-with-figure.md) - the framing that swallows a fight
- [`pipe-key-poses`](../pipeline/key-poses.md) - the blows painted as frames and anchored where they land; the choreography still in words
- [`move-crash-landing`](crash-landing.md) - a body arriving from the sky into the ground, not blows on the ground
- [`cont-shot-chain`](../continuity/shot-chain.md) - how the shots of a fight follow from each other

## Recipe (v2, 2026-10-01)

Many short shots, each a camera in a 3D set with the fighters' marks at its first and last frames; the exchange told as a numbered beat list; H3 first-last between the two frames; a key pose for every blow that must land on a given frame or that words fail to draw (§100).

1. **The set gives the frames** ([`pipe-3d-set`](../pipeline/3d-set.md)): a camera per shot, where each fighter stands and faces at the first and last frame (or "hidden" - entering or gone), the physics each shot breaks; `set_test.py cast --ends` paints both frames. Frame the exchange, not the run-up: a fighter can come in from out of the frame (D07). Check every shot's framing before any take (`set_film.py check`, then look at the frames).
2. **Words: a numbered beat list**, at most six beats per 3-4 s shot - who moves which limb where, and what each hit does to the other body and to the ground. "They fight" is a scuffle (§100.1).
3. **The style line only where something is fought** (90s shonen battle: glowing auras, speed lines, afterimages, a white impact frame on every hit - [`style-shonen-battle`](../style/shonen-battle.md)); wuxia is shot design, not an adjective (§100.2).
4. **The take:** H3 first-last (`workflows/65_minimax_h3_fl_turbo_v4.json`), two seeds; `set_test.py take`.
5. **Key poses** ([`pipe-key-poses`](../pipeline/key-poses.md)) for a blow that must land on its frame, a move words cannot draw, or a shot that must END mid-action (a posed last frame): `"keys"` in the shot script, `set_test.py key`, a look at the board, then `take`. A dense flurry keyed every 6 frames holds but goes calm - paint the impact flash into each key, at the contact only.
6. A camera move round a fight: two frames give a whip, waypoint keys a stepped orbit ([`cam-arc`](../camera/arc.md)).

## Checks before picking

- The blows land (count them against the beat list); keys on their frames; both faces against their shot's own start frame; costumes the same in the last frame as in the first (a posed end frame can change them).

## Progression

### 2026-07-29 · EDITING §5, §12 · the length of a blow · grade B
- **Did:** fight beats in the cut.
- **Got:** silent action beats all came out 4.04 s; blows should be 2.0-2.5 s; a 174-shot fast cut felt "random" and was rejected.
- **Learned:** trim blows short; cut on action, not on a clock.

### 2026-09-24 · §98.2 · a combo in a wide, then restaged · grade B+
- **Did:** both fighters whole in a wide of the court, 6 s; then a medium from a low angle, both bodies large, 4 s, one beat - same engine, words and cast.
- **Got:** the wide measured a 50% push-in and ended with the two standing still: "the combo never happened". Restaged, the punches read on all three seeds.
- **Learned:** "a wide swallows a fight"; staging close "is not style, it is what makes the action survive".

### 2026-09-24 · §98.5b · identity across the fight sequence · grade A-
- **Did:** faces scored against each shot's own start frame.
- **Got:** 0.894-0.925 for a 3.8 s H3 take; 0.75 across the cut; against the neutral cast reference only 0.22-0.33.
- **Learned:** score against the shot's own start frame; the neutral reference is a conditioner, not a yardstick.

### 2026-09-30 · the jester in the wood 305 · an exchange choreographed by puppets in a set · grade B+
- **Did:** a lunge and punch, a forearm block, a front kick and a stagger, keyed on two jointed puppets in a 3D set ([`pipe-3d-set`](../pipeline/3d-set.md)); start frame composed by the set; LTX-2.3 IC-LoRA on the puppets' depth, pinned at both ends.
- **Got:** every beat read where the choreography put it (motion r 0.97-0.99 against the set); unpinned, the jester's diamond costume turned into a bare torso; pinned, both held.
- **Learned:** blows land exactly when they are keyed; the look needs a pin at each end.

### 2026-09-30 · the jester in the wood 305, again · the exchange drawn between a set's frames on H3 · grade A-
- **Did:** the same exchange (a lunge and punch, a block, a kick, a skid back) drawn between the set's first and last frames ([`pipe-3d-set`](../pipeline/3d-set.md)) on H3 (`65`) and LTX-2.5 (`72`), and on the puppets' pose skeleton, against the old take on their depth; two seeds each.
- **Got:** H3 played it as a fight, 2 of 2: a flying lunge, the block with a flash, the kick to the chest, a skid back through the dirt in a trail of dust, straightening into the end frame (one seed added a swoosh and knocked him flat). LTX-2.5 tangled the two bodies and sprayed debris, 2 of 2; the depth and the skeleton moved exactly as keyed, stiffly.
- **Learned:** pin the exchange between two frames from the set and let H3 fight it; keyed choreography is exact and stiff.

### 2026-10-01 · fight_words · how deep a fight has to be told · grade A-
- **Did:** one exchange (the forest's 305) on H3 between its two set frames, told at four depths: who and where ("they fight"); + camera, pace and sound; + three beats; + six numbered beats with the body mechanics and the effect of every hit. Two seeds each (`studio/samples/settest/work/fight_words.py`).
- **Got:** 0-1 of the six beats, 1-2, 3 of 3, and **6 of 6 on both seeds**: a fight is choreography in words.
- **Learned:** a numbered beat list - who moves which limb where, what each hit does - inside two frames from the set; six beats fit 3.75 s; "they fight" is a scuffle.

### 2026-10-01 · the duel in the clearing · a whole fight, 58 shots, frames first · grade B+
- **Did:** Terra and the jester across a forest clearing and the path south of it: each shot a camera in the set ([`pipe-3d-set`](../pipeline/3d-set.md)) with where both stand at its first and last frames, a numbered beat list, the shonen style line where something is fought, and the physics it breaks; H3 between the two frames, two seeds.
- **Got:** the 30-second fight (10 shots) cut from the first seed pairs: walk-in, orbs, dodge, her fire, the boulder bursting, his aura, the dash and the flurry, the kick into a tree, the mid-air clash, the spells colliding. The long version: see §100.
- **Learned:** many short shots, one exchange each; the set gives every frame, the words give every blow.

### 2026-10-01 · the jester in the wood 305 · the blows drawn as key poses · grade A
- **Did:** the six-beat exchange (fight_words L4) with its blows painted into the shot's frames and anchored where they land ([`pipe-key-poses`](../pipeline/key-poses.md)): his punch at frame 20 and her kick at 44; then four keys - his wind-up at 8, the punch, the kick, his skid-stop crouch at 64. H3 `65`, 90 frames, seeds 11 and 202 (`studio/samples/fight/forest-fight/keypose/board4.jpg`).
- **Got:** every key on its frame, 2 of 2, both times; words alone landed the kick at frame 36. Between the keys H3 drew the wind-up, the spring, the pivot, the launch, the skid and the straighten - all six beats, on a timeline chosen beforehand.
- **Learned:** words say what a blow does; a key says where and when it lands.

### 2026-10-01 · the duel in the clearing D07, again · the flurry re-staged: closer, numbered, keyed · grade A-
- **Did:** v1's camera held his whole dash across the clearing and the flurry played at a quarter of the frame's height. v2: a still medium on the end marks, him streaking in from out of the frame; the flurry as five numbered beats; keys at frames 20 and 42 and a posed end frame in the lock, through `set_test.py key` / `take` ([`pipe-key-poses`](../pipeline/key-poses.md)); seeds 11 and 202 (`studio/samples/fight/forest-duel/keys_D07/`).
- **Got:** every beat readable, 2 of 2: the streak in, the punch on her forearm, the parry, the spinning kick caught, the lock with its ring of dust. In both films now.
- **Learned:** frame the flurry, not the run-up; let the run-up come in from out of the frame.

### 2026-10-01 · a flurry in place · six blows in 1.25 s, in words vs keyed every 6 frames · grade B+
- **Did:** six blows as numbered beats at D07's end marks, told in words and keyed on every blow ([`pipe-key-poses`](../pipeline/key-poses.md)); seeds 11 and 202 (`studio/samples/fight/forest-duel/flurry/`).
- **Got:** words: a frenzy of impact flashes and smears, the blows only roughly; keyed: every blow on its frame, 2 of 2, animated but calm.
- **Learned:** for a battle-anime flurry, words give the frenzy and keys the precision - and keys with the impact flash painted in give both (the next step, grade A-, in [`pipe-key-poses`](../pipeline/key-poses.md)).

### 2026-10-05 · the ember thief · a fight that is a story, one line of action, every contact keyed · grade A-
- **Did:** the director's notes on the duel answered one by one: a script with one goal first ([`cont-shot-chain`](../continuity/shot-chain.md)); every camera on one side of the line ([`cont-screen-direction`](../continuity/screen-direction.md)); the cast's mirrored views fixed; words that agree with the frames (the set draws people standing); a key for every contact.
- **Got:** 20 shots, 62 s: the hook (050) misses over his arched back, his palm (060) lands and throws her left, the uppercut (110) lands as the shot ends; she is on the left and he on the right in every two-shot. Fixed on the way: 080 (re-framed closer), 100 (the orbs given a size in the words), 130 (a leap out of the top of the picture drew a purple pillar; a last frame with him in the air above her drew his body).
- **Learned:** striking reads when the contact is a painted frame and the two fighters already face each other in the set's frames - most of the duel's "awkward striking" was the mirrored views.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a generic scuffle, then standing | "they fight" - no beats | a numbered beat list with the body mechanics (§100.1) | fight_words L1 |
| the two fighters tangle into one shape; debris sprays | LTX-2.5 between two frames on a fast exchange | H3 between the same frames | forest 305, 2 of 2 |
| a fighter's costume melts away mid-exchange | the puppet's depth carries no costume | pin the shot's last frame too | forest 305 unpinned |
| the blows never happen | a wide framing | a close low medium, one beat | §98.2; forest-duel D07 v1 |
| a fast limb ghosts | H3 on a fast limb | one mover per beat | §98 intro |
| a blow aimed away from the other fighter | the cast's views were mirrored, so the frames had them facing apart | `set_test.py` fixed 2026-10-05 | forest-duel |

## Evidence

- `studio/LTX_PLAYBOOK.md` §98; `craft/ACTION_SEQUENCE.md`; `studio/_tools/fight.py`.

## Open questions

- Paid engines for strike beats (§98.7) - not used; the user does not pay for them.
