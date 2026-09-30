# A burst of debris at a strike (`fx-impact-burst`)

| family | status | last tested | best result |
|---|---|---|---|
| fx | works-with-caveats | 2026-09-24 | H3 plateaus after about 1 s, ~40% less occluded than LTX (§98.4), grade B |

**Also called:** impact burst, ash at the punch, dust on impact, debris burst, hit effect
**Not the same as:**
- [`fx-impact-splash`](impact-splash.md) - an impact into liquid
- [`fx-glass-shatter`](glass-shatter.md) - a brittle object breaking
- [`move-fight`](../motion/fight.md) - the strike itself

## Recipe (v1, 2026-09-24)

Render strike beats with a burst on H3; on LTX-2.5 an effect becomes a standing state whatever the words say. Cheaper alternatives: keep the effects beat very short, or composite the burst in post.

## Checks before picking

- The burst clears after the strike (clear_back = (peak - end) / peak).

## Progression

### 2026-09-24 · §98.3 · "one burst per strike" on LTX-2.5 · grade D
- **Did:** two arms (a burst at each punch and no ash between; a standing wall of ash) × three seeds, one sentence apart.
- **Got:** both arms accumulated to the last frame (clear_back 0.02 and 0.03); the wording changed only how much ash.
- **Learned:** "on LTX-2.5 an effect is a standing state whatever you write".

### 2026-09-24 · §98.4 · the same on H3 · grade B
- **Did:** the same anchor and words on H3 (`workflows/67_minimax_h3_i2v_sparse.json`), two seeds.
- **Got:** H3 rose for about a second then plateaued (clear_back 0.10) and ended ~40% less occluded; five H3 takes stayed clear where all eight LTX takes disappeared into haze.
- **Learned:** the strike beat belongs on H3 (two seeds; not yet three).

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the frame fills with haze | LTX accumulates effects | H3; short beats; composite | §98.3 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §98.3-§98.4; `studio/_tools/fight.py` (`--ab`, `--h3`).

## Open questions

- A third seed; a composited burst.
