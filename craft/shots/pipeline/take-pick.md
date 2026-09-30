# Rendering and picking takes (`pipe-take-pick`)

| family | status | last tested | best result |
|---|---|---|---|
| pipeline | proven | 2026-09-30 | all five films, grade A- |

**Also called:** takes, seeds, picking, ranking, take selection
**Not the same as:**
- [`pipe-finish`](finish.md) - what happens to the picked takes

## Recipe (v1, 2026-09-30)

Two seeds on LTX-2.5 for every shot and two on H3 for every shot with a physical effect or interaction (`"engine": "both"`); rank; then pick by eye on contact strips.

1. `fight.py --shots --only-shots <ltx ids> --seeds 11 202` (`workflows/70_ltx25_i2v.json`) and `fight.py --h3 all --seeds 11 202` (`workflows/67_minimax_h3_i2v_sparse.json`).
2. `take_rank.py`: faults (face under 0.60 against its start frame, a line not heard, silence) block a pick.
3. Contact strips of every take; override the ranker by eye (its 0.700 for faceless shots is a default).
4. H3 renders 17n+5 frames: a "5 s" H3 take is 4.5 s; plan the runtime on the takes.
5. Two background processes both waiting for an empty ComfyUI queue starve each other: run one GPU job stream at a time.

## Checks before picking

- The shot's own entry's checks.

## Progression

### 2026-09-05 · §55 · a repair must not win the pick · grade n/a
- **Did:** a full take against a face-trimmed one.
- **Got:** the trimmed one won on camera exactness.
- **Learned:** "what a take delivers against what the shot asked sorts above camera exactness".

### 2026-09-07 · §95 · faults and notes · grade n/a
- **Did:** the method's pick rule.
- **Got:** a take is picked iff its faults are empty; notes never block.
- **Learned:** one rule for every path.

### 2026-09-24 · ACTION_SEQUENCE · three seeds and the ranker's blind spots · grade n/a
- **Did:** the fight film's picks.
- **Got:** three seeds is the floor; `take_rank` cannot see a stranger walking in.
- **Learned:** look at every take before the pick.

### 2026-09-30 · cyber-alchemist · 27 LTX shots and 12 H3 shots, two seeds each · grade A-
- **Did:** the recipe above.
- **Got:** of the twelve shots rendered on both, H3 won eight (113, 202, 204, 301, 302, 303, 306, 309); an H3 first-last take won 112; LTX won everything else.
- **Learned:** H3 for physical interaction; LTX for everything held.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| H3 takes stall for half an hour | another process keeps the queue busy | one GPU stream at a time | cyber-alchemist H3 stage |
| the film comes out short | H3 lengths are 17n+5 frames | plan on the takes' frames | cyber-alchemist (2:36 for 3:00) |

## Evidence

- `studio/_tools/take_rank.py`, `studio/_tools/fight.py`.

## Open questions

- None open.
