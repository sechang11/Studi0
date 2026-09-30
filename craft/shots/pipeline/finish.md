# Finishing the film (`pipe-finish`)

| family | status | last tested | best result |
|---|---|---|---|
| pipeline | proven | 2026-09-30 | all five films, grade A- |

**Also called:** finish, assembly, the cut, final render, grade and mix
**Not the same as:**
- [`pipe-take-pick`](take-pick.md) - choosing the takes
- [`master-upscale`](../style/master-upscale.md) - the 2x master at the end of the finish

## Recipe (v1, 2026-09-30)

`fight.py --music --music-secs <film length>`, then `fight.py --finish --picks <picks> --master`, then `film_cards.py --sequence F --picks <picks>`.

1. Trims per shot (`"trim": {"take": <pick>, "in": s, "out": s}`), applied only when the trim's take is the pick.
2. The finish conforms H3's 32 kHz audio, concatenates, grades once (filmic), lays the ACE-Step score under at 0.5, normalises to -16 LUFS and checks that the film's frame count equals its takes'.
3. Pass `--music-secs`: the default length counts every shot's `secs`, including end-frame-only "key" shots.

## Checks before picking

- The frame-count invariant line says OK.
- The runtime against the brief.

## Progression

### 2026-07-29 · EDITING §7 · music cues overlapping · grade C
- **Did:** cues laid at their starts with their full lengths.
- **Got:** 30-55 s overlaps; 43 s of the finale never played.
- **Learned:** cue length = next start - this start + 4.0 s; `loudnorm linear=true`.

### 2026-09-07 · §75, §79, §89-§92 · cuts measured; the audio bed · grade n/a
- **Did:** one number per cut; a film with silent composited shots.
- **Got:** `amix=duration=first` truncated the film; a third was silent.
- **Learned:** measure every cut; build the scene's bed yourself; render the mix to a file and measure it.

### 2026-09-07 · §96.8 · the canvas follows the takes · grade n/a
- **Did:** a fixed finishing canvas.
- **Got:** it shrank 1920x1088 takes by a quarter.
- **Learned:** the canvas follows the takes; the frame count must equal the takes'.

### 2026-09-30 · five films · the finish · grade A-
- **Did:** the recipe above.
- **Got:** every invariant OK (3745 of 3745 on the Alchemist). The Alchemist ran 2:36 + title for a 3:00 brief.
- **Learned:** plan the runtime on the takes' real lengths.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the score longer than the film | key shots counted in the default length | `--music-secs` | cyber-alchemist |
| the film short of the brief | H3 lengths, trims | plan on real lengths | cyber-alchemist |

## Evidence

- `studio/_tools/fight.py` (`stage_finish`, `stage_music`), `studio/_tools/film_cards.py`.

## Open questions

- None open.
