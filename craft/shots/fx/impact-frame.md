# The anime impact frame (`fx-impact-frame`)

| family | status | last tested | best result |
|---|---|---|---|
| fx | works-with-caveats | 2026-10-01 | fight_words shon, 2 of 2 seeds on every hit, grade A- |

**Also called:** impact frame, hit flash, starburst on a hit, white flash frame, impact burst frame, sakuga hit
**Not the same as:**
- [`style-shonen-battle`](../style/shonen-battle.md) - the whole battle dialect this flash is one mark of
- [`fx-impact-burst`](impact-burst.md) - debris thrown from a strike
- [`trans-flash`](../transitions/flash.md) - a white flash used as a cut between shots
- [`fx-lightning`](lightning.md) - a flash from the sky lighting a place

## Recipe (v1, 2026-10-01)

1. Draw the exchange between two frames from the set (H3, `workflows/65_minimax_h3_fl_turbo_v4.json`), told as a numbered beat list ([`move-fight`](../motion/fight.md)).
2. Name the mark in the shot's style line: "a white impact frame on every hit" (the shonen dialect, [`style-shonen-battle`](../style/shonen-battle.md)). On H3 it renders as a one- or two-frame white starburst, sometimes a whole-frame flash on black, exactly at each contact.
3. Only on shots where something is hit: with the line on an establishing shot, H3 fired one at nothing (forest-duel D01).

## Checks before picking

- The flash sits on a contact, not on a walk or a look.
- The faces come back the same after the flash.

## Progression

### 2026-10-01 · fight_words L2 / shon · the impact frame, asked for and not · grade A-
- **Did:** the forest's 305 exchange on H3 between its two set frames, told at four depths and in two dialects, two seeds each.
- **Got:** "fast, hard-hitting anime action" alone already produced whole-frame impact flashes (L2, both seeds); named in the shonen dialect they landed on every hit, 2 of 2, with speed lines around them.
- **Learned:** H3 knows the impact frame; name it, and keep it to the shots with hits.

### 2026-10-01 · forest-duel D01 · the dialect on a quiet shot · grade C
- **Did:** the duel's establishing walk told with the shonen style line.
- **Got:** a white starburst over her as she walked (seed 11) and a speed-lined dash (seed 202) - nothing was hit.
- **Learned:** the style line is per shot, not per film.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a white flash on a shot where nothing is hit | the battle style line on a quiet shot | leave the style line off establishing shots, looks and aftermaths | forest-duel D01 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §100.1-100.2; `studio/samples/settest/work/fight_words.py`.
- Box-local: `studio/samples/fight/forest-fight/fight_words/` (board.jpg, the 12 takes), `studio/samples/fight/forest-duel/h3f_D01_s*_styled.mp4`.

## Open questions

- How long an impact frame can hold before it reads as a cut.
