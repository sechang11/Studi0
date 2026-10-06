# One moment told as a chain of shots - the relay (`cont-relay`)

| family | status | last tested | best result |
|---|---|---|---|
| continuity | works-with-caveats | 2026-10-05 | the fire esper, 23 legs, grade A- |

**Also called:** relay, expand this shot, elaborate this shot, break a shot into shots, multi-shot sequence, coverage of one moment, the same moment from several angles, a spell cast across shots, legs, baton
**Not the same as:**
- [`cont-shot-chain`](shot-chain.md) - every shot caused by the one before it across a whole story; a relay is ONE moment stretched across shots
- [`trans-montage`](../transitions/montage.md) - details cut together with no story time
- [`trans-in-shot-cut`](../transitions/in-shot-cut.md) - a cut inside one generation

## Recipe (v1, 2026-10-05)

One moment, carried by a chain of shots like a baton: each shot is a LEG with a window of story time and something it hands to the next (LTX_PLAYBOOK §101).

1. **One sentence:** the moment and its payoff ("Terra prays; a fire esper answers, hunts the jester and turns the forest into a volcanic warzone").
2. **Story time in seconds:** the cause, the build, the turn, the payoff, the cost. Each shot gets a window, `t a-b`.
3. **Legs** - *advance* (time moves on: 0-3, 3-4, 4-6), *echo* (the same window again from another angle - same start time to replay it, a later start for a closer look), *answer* (the other side reacts), *breath* (a cutaway while time passes: birds, wind, the overview), *reveal* (the payoff from its best angle). Alternate advance and answer; echo only the payoff; a breath before the payoff and after it.
4. **A baton per leg** - a look, a motion, a rhyme, an object, a sound or a light the next leg picks up - and the glue at every cut ([`trans-sound-bridge`](../transitions/sound-bridge.md), [`trans-held-object`](../transitions/held-object.md), [`trans-flash`](../transitions/flash.md), [`trans-dissolve`](../transitions/dissolve.md)).
5. **The place progresses** with the relay: one set, its dress worse each act (dusk → red sky → burning → volcanic).
6. **Frames first** in a set ([`pipe-3d-set`](../pipeline/3d-set.md)), one line of action ([`cont-screen-direction`](screen-direction.md)); the pose the story needs (a prayer, a kneel) painted as a key ([`pipe-key-poses`](../pipeline/key-poses.md)) - the cast draws everyone standing, arms down.
7. The maker checks the story time (an echo repeats told time; nothing else runs backward) with the line, the picture, the facing and the marks: `studio/shotscripts/_make_fire_esper_1005.py`.

## Checks before picking

- Read the legs in order: does each window follow the last (or repeat it, for an echo)?
- Does every leg hand the next something? Name it.
- Play the cut with the sound off: can you tell where the story time moves on and where it replays?

## Progression

### 2026-10-05 · the fire esper · 23 legs, 62 s of story · grade A-
- **Did:** the recipe above; the director asked for it by name ("expand or elaborate on this shot").
- **Got:** played in order every leg picks up the last (his look down → the runes at her feet → the circle from above → her face → the birds → his fear → her call → the column → the esper rising from in front of her, from behind him, then its eyes → the wind in his face → the hunt → the comet → the ruin → his bow → the esper into her hands → her alone). The payoff's echoes (100 → 110 → 120) are the strongest stretch; the answers make the magic land. 16 keys in 10 shots painted what the set cannot draw. Weakest: the small wides (010, 140, 230), 050's pale circle, 070's dot-sized birds.
- **Learned:** an echo must repeat its details in words (030's orbs, 050's circle); the last frame decides how a beat ends (080's grin came back); a style line can run ahead of the relay (020 lit the runes before 040 did) - each leg gets the style of its own moment.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the pose the story needs is missing (she prays in the words, stands arms-down in the take) | the set's cast draws everyone standing | paint the pose into the frames as keys | fire-esper 020-100, 210-220 |
| a beat comes and goes inside a shot (his grin falters, then returns) | the last frame is the shot's FIRST state | paint the last frame in the state the beat ends in | fire-esper 080 |
| a cutaway with nothing in it (no birds) | a breath leg's subject asked only in words | paint it into the last frame | fire-esper 070 |
| an echo shows something different from the shot it echoes (multicoloured balls, not the purple orbs) | the echo's words did not repeat the detail | repeat every detail an echo must match | fire-esper 030 |

## Evidence

- `studio/shotscripts/fire-esper.md` (the script as a relay), `fire-esper.json` (each shot's leg, story time, baton, glue), `studio/shotspecs/fire-esper/` (each shot's promises), `fire-esper.cut.json` (the glue).

## Open questions

- How short can an echo be before it reads as a flash frame?
- A relay over dialogue, not action.
