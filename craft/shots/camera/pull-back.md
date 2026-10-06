# Pull-back (`cam-pull-back`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | works-with-caveats | 2026-10-05 | builder post move 12-22% (§53), grade A- |

**Also called:** pull back, dolly out, pull out, reveal by pulling back, zoom out, move away, reveal by pull
**Not the same as:**
- [`cam-push-in`](push-in.md) - the direction engines drift in by themselves
- [`cam-lead-dolly`](lead-dolly.md) - backing away in front of a subject who walks toward the camera

## Recipe (v2, 2026-09-05)

**Shot-script pipeline:** a depth guide - the move rendered first (arithmetic or Blender), then LTX-2.3 IC-LoRA following its depth (27% on 3 of 3 seeds, §97.2). **/film builder:** a post move on a stabilised take (it crops, so render wider than the final frame). H3 obeying "pull back" was one seed's luck and is withdrawn.

## Checks before picking

- Measured pull against the ask.

## Progression

### 2026-09-05 · §50-§53 · pull back by words on H3; then by arithmetic · grade A-
- **Did:** the keyword bench (seed 4242); the H3 exception built on it; post pulls.
- **Got:** LTX *pull back* tilted 39% and did not pull; LTX *tracking* pulled back 18%. H3 *pull back* pulled 28% and [Zoom out] 41% - then the first build that relied on it pushed in 4.2x on another seed, and the exception was withdrawn. Post pulls measured 12-22% (reveal by pull 22%).
- **Learned:** "one anchor and one seed is a measurement, not a law".

### 2026-09-24 · §97.2 · a pull-back through a depth guide · grade A
- **Did:** the camera rig's arithmetic pull-back (1.35x → 1.0x) as ground truth; arm A words only; arm B the rig's MoGe-2 depth through LTX-2.3 IC-LoRA (`workflows/74_ltx23_ic_lora_control.json`); seeds 11, 202, 3003.
- **Got:** words gave a PUSH in of 17%, 47% and 21% (zoom error 0.542); the depth guide gave a pull back of 27% on all three (error 0.014, curve RMSE 0.008). The room revealed at the border is generated (white roses where the plate has sunflowers). 74-79 s a take against 38-39 s.
- **Learned:** "A depth guide makes the camera do what words cannot" - the ancestor of the previz camera moves.

### 2026-09-30 · quantum-courier 313 · "the camera pulls back sharply away from her" on LTX · grade B
- **Did:** the words, from a backlit start frame, LTX seed 202, into a static wide (314).
- **Got:** the pair reads as a pull back into the sunset wide; the pull inside 313 was not measured.
- **Learned:** a cut to a wider shot carries the pull when the engine may not.

### 2026-10-05 · the fire esper 230 · a pull back as a shot option, in a 3D set · grade n/a
- **Did:** `camera_move` pull_back 0.35 (14% of the distance back) on the last shot; its end key (the kneel) painted again from the new end frame on the picked seed.
- **Got:** she sinks to her knees as the camera pulls away and the ruin grows round her.
- **Learned:** a move that changes the end frame needs its end key painted again (`key --force`).

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a push instead of a pull | engines drift forward | post move | §53 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §50-§53; `studio/samples/fight/quantum-courier/shot_313_s202.mp4`.

## Open questions

- A pull-back by previz (`--radius` growing) in the shot-script pipeline.
