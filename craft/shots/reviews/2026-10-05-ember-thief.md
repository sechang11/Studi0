# Review: THE EMBER THIEF (2026-10-05)

Graded from the cut (a frame a second), the takes behind it (eight frames across each, two to four takes a
shot) and the set's frames. The brief was the director's note on THE DUEL IN THE CLEARING: "a lot of awkward
striking and facing the wrong direction... the sequences don't string together in a solid context... like many
individual scenes strung together randomly and not a story where each shot before it led to the next one" -
then: one minute, the script first, a prompt per shot, the film on shots & specs. Grades on
[the book's scale](../README.md#grades).

| film | length | shots | grade | in one line |
|---|---|---|---|---|
| THE EMBER THIEF | 62 s + title and end card (68.7 s) | 20 | **A-** | one goal, one line of action, every contact keyed: it plays as a story; the small wides (the pendant at 010, his flips at 040) keep it off an A |
| (the duel in the clearing, for comparison) | 3:04 | 58 | B+ | spectacle shot by shot; facing mirrored by a bug; no goal between the exchanges |

## What was asked

| the director asked for | where | grade | what is on screen |
|---|---|---|---|
| no more facing the wrong direction | all 20 | A | the cause was a bug (the cast pasted the sheets' side and three-quarter views mirrored) - fixed; every camera east of the line, so Terra is on the left and the jester on the right in every two-shot, facing each other ([`cont-screen-direction`](../continuity/screen-direction.md)) |
| no more awkward striking | 050, 060, 110 (keyed) | A- | the hook sweeps over his arched back on its frame; his palm lands on her shoulder and throws her left; the uppercut lands as 110 ends ([`pipe-key-poses`](../pipeline/key-poses.md)) |
| a story where each shot leads to the next | the whole cut | A- | the pendant is the goal in every shot; looks, throws and blows carry across the cuts; 110 ends ON the blow and 120 is the pendant flying up ([`cont-shot-chain`](../continuity/shot-chain.md)) |
| one minute | the cut | A | 62 s of story in 20 shots of 2.3-4.5 s |
| the script first, detailed | `studio/shotscripts/ember-thief.md` | n/a | four acts, twenty beats, the rule of the camera written into it |
| a prompt for each shot | the shot script, shots & specs | n/a | each shot's prompt, story note and spec sheet (its promises) on the page |
| the magic needs work | 080-100, 140-180 | B+ | the fireballs and the exploding boulder, the fist-sized orbs, the leap, the torrent, the white-hot pendant, the fire ring and the purple aura read |

## Shot by shot

| shot | take in the cut | grade | on screen |
|---|---|---|---|
| 010 the thief | H3 s11 | B+ | she walks up the path into the clearing; he waits by the boulder - too small to see what he swings |
| 020 her pendant | H3 s202 | B+ | her hand to her bare throat, a spark at her fingers |
| 030 come and get it | H3 s11 | A- | the glowing pendant dangled, looped over his head, the beckon |
| 040 the charge | H3 s11 | B+ | her dash in fire and speed lines; he somersaults in from the right and lands facing her |
| 050 the hook | H3 + key s202 | A | the flaming hook over his arched back on frame 30; both upright at the end |
| 060 his counter | H3 + key s11 | A- | the palm into her shoulder, she skids left and stays on her feet |
| 070 now she is angry | H3 s11 | A- | the wrist across her mouth, embers, fists alight |
| 080 the boulder | H3 s11 (re-framed) | A- | the third fireball blows the boulder apart behind him; first shot as a wide where his cartwheels were too small to read, re-framed closer over her shoulder |
| 090 out of the smoke | H3 s11 | A- | he coughs out of the dust, three orbs, thrown left |
| 100 his orbs | H3 s7777 (re-worded) | A- | the fiery swat, the duck, the third orb bursting at her feet, the roll; the first words drew orbs the size of her body - "the size of a fist" fixed it |
| 110 the uppercut | H3 + key s11 | A | smoke, his high kick over her as she ducks, the uppercut landing in a burst as the shot ends |
| 120 the pendant flies | H3 s202 | B+ | the pendant and its chain spinning up through the clearing |
| 130 the leap | H3 s6161 (last frame re-staged) | A- | he rises as a whole body in a purple aura above her as she jumps and falls short; with no last frame (he left the top of the picture) he was a purple pillar on four seeds, and words alone only thinned it - the last frame now has him in the air above her |
| 140 he catches it | H3 + key s11 | A- | a purple streak into an open sky; the painted catch, pendant held high |
| 150 she calls it | H3 s11 | A- | her raised hand, a ring of fire, her eyes gone orange |
| 160 too hot to hold | H3 s11 | A- | he lands, the pendant blazes white-hot, smoke, the throw to the left (re-shot from in front of him) |
| 170 back in her hand | H3 s202 | A- | the pendant arcs in from the right into her palm |
| 180 the torrent | H3 s202 | A- | a cone of fire from her palm sweeps him away to the right |
| 190 the bow | H3 s11 | A- | scorched, smoking, the bow, the purple smoke |
| 200 the pendant | H3 s11 | A- | the push-in, her hands at her neck, the smile |

## What it took

- Two bugs in the set pipeline, both in every set film before today: the mirrored turnaround views
  (`set_test.py` VIEWS8, plus a mirrored twin where a sheet drew both three-quarters one way) and a shot with
  nobody in it stopping the cast.
- A maker that checks every frame before it renders - the camera's side of the line, everyone in the picture,
  facing on screen, nobody seen from behind unless over their shoulder, the marks chained
  (`studio/shotscripts/_make_ember_thief_1005.py`): 9 bad frames in the first draft, and 160's camera behind the
  jester after a mark moved.
- Four keys (050, 060, 110, 140), one with a second edit to remove the copy of the jester the pose left behind.
- Four shots re-framed after the first takes (130, 140, 150, 200), then 160 and 080.

Lessons filed: [`cont-screen-direction`](../continuity/screen-direction.md),
[`cont-shot-chain`](../continuity/shot-chain.md), steps in [`pipe-3d-set`](../pipeline/3d-set.md),
[`pipe-key-poses`](../pipeline/key-poses.md) and [`move-fight`](../motion/fight.md).
