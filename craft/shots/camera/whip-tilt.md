# Whip-tilt, a fast tilt between two framings (`cam-whip-tilt`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | proven | 2026-09-30 | cyber-alchemist 112 and 210, grade A- |

**Also called:** rapid tilt, snap tilt, whip down, whip up, fast tilt reveal, shifting focus down to the hands
**Not the same as:**
- [`cam-tilt`](tilt.md) - a slow tilt; it can reveal something at a walking pace and is built differently
- [`cam-whip-pan`](whip-pan.md) - the same speed on the other axis; a whip pan is a post move on a stabilised take

## Recipe (v1, 2026-09-30)

First-last frame between the LAST frame of the shot before and a composed end frame, on H3 or LTX-2.5, 2-5 s, trimmed to the move.

1. The first frame is `"end:shot_<prev>_s<seed>.mp4"`, the picked take's last frame. `studio/_tools/flf_shots.py` pulls it. Starting from the previous shot's START frame jumps back in time at the cut.
2. The last frame is a shot of its own with `"engine": "key"`: a start frame composed like any other, with no takes. The finish skips it.
3. `flf_shots.py --sequence F render --shots 112,210 --engines ltx,h3 --seeds 11 202`. H3 renders 17n+5 frames, so ask 3 s for about 2.3 s.
4. Prompt: the path of the move in words ("from her eye, past the collar and the corset, to her gloved hands at the bench"); ask for motion blur for a whip.
5. Trim the hold after the move lands (210 kept 3.2 s of 5).

## Checks before picking

- The path goes THROUGH the body between the two frames (face, collar, corset), not a dissolve.
- Asymmetric features on the way (which eye is silver) for every frame: one take flashed the silver iris on the wrong side for about 0.2 s.
- The last frame matches the next shot's start if the cut continues.

## Progression

### 2026-09-30 · cyber-alchemist 112 · eye macro → hands at the bench, 3 s · grade A-
- **Did:** first = the last frame of `shot_111_s11` (the iris macro), last = a Flux 2 composed macro of her gauntlets lifting the vial; LTX first-last and H3 first-last, two seeds each.
- **Got:** all four pulled back from the eye, down past her face and corset, to the hands: a real move. H3 seed 11 (2.3 s) is in the cut. In some other takes the silver iris showed on the wrong eye for about 0.2 s.
- **Learned:** between two frames of the same moment, first-last makes a camera move, not a morph.

### 2026-09-30 · cyber-alchemist 210 · hands on the railing → up the shaft, 5 s · grade A-
- **Did:** first = the last frame of `shot_209_s11` (POV hands on the railing), last = a composed POV of the shaft.
- **Got:** a fast tilt with real motion blur at about 1 s, then a 3 s hold. LTX seed 11 was cut to 3.2 s.
- **Learned:** expect the move in the first second and a hold after it; trim.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a jump back at the cut | first frame = the previous shot's START frame | `end:<take>` as the first frame | caught before rendering |
| a feature flips side mid-move | the engine re-draws the face in passing | check every frame; pick the take without it | 112, some takes |
| a long static tail | the move lands early | trim | 210 |

## Evidence

- `studio/samples/fight/cyber-alchemist/flh3_112_s11.mp4`, `fl_210_s11.mp4`; strip `flf_tilts.jpg`.
- `studio/_tools/flf_shots.py` (`frame()` pulls `end:` frames), `workflows/65_minimax_h3_fl_turbo_v4.json`, `workflows/72_ltx25_flf2v.json`.

## Open questions

- Whip-tilts across two different places (first-last across rooms cross-fades; see [`cam-orbit-360`](orbit-360.md)).
