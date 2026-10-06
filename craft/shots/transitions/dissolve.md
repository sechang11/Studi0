# Dissolve (`trans-dissolve`)

| family | status | last tested | best result |
|---|---|---|---|
| transitions | proven | 2026-10-05 | shot 070 → 080, the cut number 17.49 → 1.46 (§75), grade A- |

**Also called:** dissolve, cross-fade, crossfade, mix, fade between shots
**Not the same as:**
- [`trans-match-cut`](match-cut.md) - a hard cut between shapes that rhyme
- [`trans-time-passes`](time-passes.md) - a dissolve between two lights of the same place
- [`trans-fade-to-black`](fade-to-black.md) - to black, for an act break
- [`trans-sound-bridge`](sound-bridge.md) - the picture cuts and the SOUND overlaps

## Recipe (v1, 2026-09-07)

A short dissolve (about 1/3 s) from the previous take's actual last frame; to make someone vanish, dissolve into a de-populated copy of the end pin built by the same script. A cut hidden behind an effect acts as a dissolve.

## Checks before picking

- The frame the dissolve starts from is the PICKED take's last frame.

## Progression

### 2026-07-29 · EDITING §1, §2 · transition lengths · grade B+
- **Did:** a film cut with 0.35 s transitions everywhere.
- **Got:** it read as a slideshow; transitions ate 5.2% of the runtime; the working set: cut 0, soft 0.28, dissolve 0.70, flash 0.50, fade 1.00 s; offsets need the video stream's duration (the container read 219 ms long).
- **Learned:** use cuts by default; dissolves mean time passed.

### 2026-09-07 · §75, §77, §84 · handover dissolves; a figure dissolved away · grade A-
- **Did:** a 1/3 s dissolve from shot 7's last frame; a de-populated copy of the end pin for "she turns transparent".
- **Got:** 070 → 080 went from 17.49 to 1.46; with the camera locked off, the global dissolve removed exactly her. A hardcoded path later opened a shot on a retired take.
- **Learned:** read the picked take, never a filename.

### 2026-09-24 · §98.5 · a cut asked inside a screen-filling cloud · grade n/a
- **Did:** the word *cut* inside an ash cloud.
- **Got:** the cut detector missed it on 2 of 3 takes.
- **Learned:** "a cut hidden behind an effect is a dissolve as far as any detector is concerned, and it is the better-looking choice".

### 2026-10-05 · the fire esper · dissolves as glue · grade A-
- **Did:** 0.8 s dissolves where time passes or a thing becomes another: the impact into the warzone's overview (180 → 190), her glowing hands into her alone in the ash (220 → 230), the title in and THE END in (`glue_cut.py`).
- **Got:** the ruin arrives as time passing; the hands melting into the wide reads as the power gone home.
- **Learned:** inside a relay a dissolve marks the breath legs - it says time moved on without a word.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a torch vanishes in the dissolve | the de-populated copy built differently | build both with the same script | §77 |
| the first word of a narration line is quiet | narration baked into dissolving segments | one continuous narration track | VIDEO_RULES SOUND-03 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §75, §77, §84, §98.5; `craft/VIDEO_RULES.md` (SOUND-03).

## Open questions

- None open.
