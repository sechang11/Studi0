# A 90s shonen battle (`style-shonen-battle`)

| family | status | last tested | best result |
|---|---|---|---|
| style | works-with-caveats | 2026-10-01 | fight_words shon, every mark on 2 of 2 seeds, grade A- |

**Also called:** shonen battle, dragon ball style fight, battle anime, power-up fight, aura fight, anime battle, ki battle
**Not the same as:**
- [`style-2d-anime`](2d-anime.md) - the look of the drawing; this is how a fight moves inside it
- [`move-fight`](../motion/fight.md) - the choreography itself, in any style
- [`fx-impact-frame`](../fx/impact-frame.md) - one of the marks this style names

## Recipe (v1, 2026-10-01)

1. The look is the film's ([`style-2d-anime`](2d-anime.md)); the fight is drawn between two frames from the set on H3 ([`pipe-3d-set`](../pipeline/3d-set.md), §99.10).
2. One style line before the beats, on shots where something is fought: "A fight in the manner of a 90s shonen battle anime - glowing auras, speed lines, afterimages, a white impact frame on every hit." Name the genre's marks, never a show or a character from one.
3. Then the numbered beat list (L4, [`move-fight`](../motion/fight.md)), and the effect that ends the exchange - "a shockwave ring of dust bursts out across the path".
4. Quiet shots - the establishing walk, a look, the aftermath - go without the style line (forest-duel D01).
5. Wuxia is not a style line: named the same way ("graceful, wire-assisted movement, flowing fabric") it changed nothing at a medium side view. It is shot design - wide, airborne, slow, the whole body in frame (forest-duel E06b).

## Checks before picking

- Every hit has its mark (flash, speed lines) and nothing else does.
- The six beats are all there, in order.
- Faces and costumes survive the flashes.

## Progression

### 2026-10-01 · fight_words shon vs wux · two dialects on one exchange · grade A-
- **Did:** the same six-beat exchange (305) on H3 between its set frames, once in the shonen dialect and once in the wuxia one, two seeds each.
- **Got:** shonen: starburst impact frames, radial speed lines, a long dust trail and the shockwave ring on both seeds, the six beats intact. Wuxia: indistinguishable from the plain six-beat take.
- **Learned:** H3 speaks shonen when its marks are named; wuxia has to be built into the shot.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a walk becomes a speed-lined dash; a flash on nothing | the style line on a quiet shot | the style line only where something is fought | forest-duel D01 |
| the wuxia take looks like any fight | wuxia named as adjectives at a medium side view | design the shot: wide, airborne, slow | fight_words wux |

## Evidence

- `studio/LTX_PLAYBOOK.md` §100; `studio/samples/settest/work/fight_words.py`; `studio/shotscripts/_make_forest_duel_1001.py` (STYLES, QUIET).
- Box-local: `studio/samples/fight/forest-fight/fight_words/`, `studio/samples/fight/forest-duel/`.

## Open questions

- A beam struggle and a power-up held for long (forest-duel F12, F01).
