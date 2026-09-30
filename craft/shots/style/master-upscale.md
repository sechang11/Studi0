# The 2x master (`master-upscale`)

| family | status | last tested | best result |
|---|---|---|---|
| style | proven | 2026-09-30 | storm-sonata SeedVR2 master, grade A |

**Also called:** upscale, 2x master, SeedVR2 master, ESRGAN master, delivery master, 4K
**Not the same as:**
- [`style-photoreal`](photoreal.md) - the look of the film; the master only sharpens it
- [`pipe-finish`](../pipeline/finish.md) - the whole finishing chain; the master is its last step
- [`style-grade`](grade.md) - colour, not resolution

## Recipe (v2, 2026-09-30)

ESRGAN 2x for every film (`fight.py --finish --master`, 0.13-0.22 s a frame); SeedVR2 3B for photoreal films worth 2 s a frame (`studio/_tools/seedvr2_master.py`).

1. `fight.py --finish --picks ... --master`, then `film_cards.py` for `_final_2x.mp4`.
2. Photoreal: `seedvr2_master.py` cuts at the shot boundaries and runs SeedVR2 per shot with temporal chunking.

## Checks before picking

- Compare the 2x with the 1x BY TIME, not by frame index: the 2x repeats frames where the 1x has timestamp gaps (+6 frames on the Courier, +13 on the Alchemist) and stays within one frame in time.

## Progression

### 2026-09-04 · §34 · ESRGAN x4 as a master · grade D
- **Did:** RealESRGAN x4 in 12-frame chunks.
- **Got:** 3.3 s a frame (a 3:08 film in about 4 h); a chunk stalled.
- **Learned:** a deliverable, not a master step.

### 2026-09-07 · §96.8 · RealESRGAN x4 on a halved frame · grade A-
- **Did:** the 2x master path.
- **Got:** 0.35 s a frame, cleaner than the full-frame path.
- **Learned:** the default master.

### 2026-09-24 · §98.6 · where an extra frame comes from · grade n/a
- **Did:** counted frames through concat, libx264 and the master.
- **Got:** the re-encode, not the upscaler, adds the frame (621/621/622).
- **Learned:** count the way the consumer counts.

### 2026-09-30 · storm-sonata · ESRGAN against SeedVR2 · grade A
- **Did:** both masters of the same film.
- **Got:** raindrops, wet skin and hair strands survive in SeedVR2 where ESRGAN paints them smooth; 35 minutes against about 2.
- **Learned:** SeedVR2 for photoreal when time allows. SeedVR2 needed temporal chunking (it ran out of memory at 28.3 GB without), and the fetch had to take the file under its own prefix, not the first video (the input preview).

### 2026-09-30 · cyber-alchemist · the 2x frame count · grade n/a
- **Did:** counted the 2x master's frames against the 1x.
- **Got:** 3758 against 3745; by timestamp the 2x is within one frame of the 1x throughout.
- **Learned:** not a desync: the 1x has timestamp gaps that the 2x fills.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| SeedVR2 runs out of memory | no temporal chunking | chunked graph | storm-sonata |
| the fetch returns the input | the collector took the first video | filter by the output prefix | storm-sonata |
| frame counts differ | 1x timestamp gaps filled in the 2x | compare by time | quantum-courier, cyber-alchemist |

## Evidence

- `studio/_tools/seedvr2_master.py`; `challenge-films-2026-09-30/storm-sonata_master_esrgan_vs_seedvr2.jpg` (local).

## Open questions

- SeedVR2 on anime and puppets.
