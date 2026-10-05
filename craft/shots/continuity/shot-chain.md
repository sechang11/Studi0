# Each shot caused by the one before it (`cont-shot-chain`)

| family | status | last tested | best result |
|---|---|---|---|
| continuity | works-with-caveats | 2026-10-05 | the ember thief, 20 shots, grade A- |

**Also called:** a story not a montage, cause and effect, the end of one shot is the start of the next, shots strung together randomly, story-first fight
**Not the same as:**
- [`cont-screen-direction`](screen-direction.md) - who is on which side of the screen
- [`move-fight`](../motion/fight.md) - how a single exchange of blows is drawn
- [`cont-prop-state`](prop-state.md) - a prop's state carried across cuts

## Recipe (v1, 2026-10-05)

Write the story before the shots, give it one goal, and make every shot end where the next begins.

1. **A script first, in words a reader can follow** (`studio/shotscripts/ember-thief.md`): one goal both characters want - the jester has stolen Terra's ember pendant, she wants it back - and acts that turn on it (the theft, the fight he is winning, the turn when the pendant flies, the end). Every shot gets one sentence of what it does in the story and which shot it leads to (the shot script's "note", shown on shots & specs).
2. **Cause, then effect, across every cut:** a look to the right cuts to what she looks at; a throw to the left cuts to it arriving from the right; a blow that sends him out of the top of the frame cuts to him coming in from below. Cut ON the action (110 ends on the uppercut, 120 is the pendant flying up).
3. **One chain of marks:** where a character ends a shot is where they start the next (`_make_ember_thief_1005.py` checks it), unless the story moves them - a vanishing trick, a leap, a blast - and the maker says so ("jump").
4. **Words and frames agree:** the set draws people standing, so a beat that ends crouched becomes "skids to a stop, still on her feet"; a shot that must end mid-blow gets a painted last frame ([`pipe-key-poses`](../pipeline/key-poses.md)).
5. One minute is about twenty shots of 2-4.5 s: an establishing wide, then close ups only where a decision is made (020 she finds her throat bare, 070 she gets angry, 150 she calls the pendant).

## Checks before picking

- Read the shot notes in order: does each one say why the next happens?
- Play the picks in order with the sound off: does every cut continue the movement of the last shot?

## Progression

### 2026-10-01 · the duel in the clearing · 58 shots from a list of exchanges · grade C
- **Did:** acts of exchanges (orbs, fireballs, a kick, a clash in the air, a beam struggle), each shot designed on its own.
- **Got:** the director: "the sequences don't string together in a solid context... like many individual scenes strung together randomly, not a story where each shot before it led to the next one".
- **Learned:** a fight needs a goal and a chain, not a list of moves.

### 2026-10-05 · the ember thief · one goal, 20 shots chained · grade A-
- **Did:** the recipe above.
- **Got:** played in order the film reads as one story (title -> theft -> dare -> exchanges he wins -> the uppercut that frees the pendant -> the race for it -> it burns him -> it comes home -> the finish -> his bow): every cut continues the last shot's movement - her look right cuts to him, his throw left arrives from the right, 110 ends ON the uppercut and 120 is the pendant flying up. Weak links found and fixed after the first takes: 130 (he left through the top of the picture, so H3 drew a purple pillar - a last frame with him in the air above her drew his body) and 080 (a wide where his dodges were too small to read - re-framed closer).
- **Learned:** the goal does the work - once every shot is about the pendant, the order of the shots stops being arbitrary; and cutting on the action needs the shot to END on it (a posed last frame).

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| shots feel like separate scenes | no goal, no cause between cuts | a script with one goal; each note names what it leads to | forest-duel |
| a character teleports across a cut | the next shot's marks were set on their own | the chain check | forest-duel |
| the words say crouched, the frame says standing | the set draws standing people | words that agree with the frames, or a key | ember-thief 060/070 (fixed before rendering) |

## Evidence

- `studio/shotscripts/ember-thief.md` (the script), `ember-thief.json` (notes per shot), `studio/shotspecs/ember-thief/` (each shot's promises).

## Open questions

- Whether a story beat can be held across a cut by sound alone (a sound that starts in one shot and lands in the next) has not been tried.
