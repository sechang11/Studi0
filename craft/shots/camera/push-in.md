# Push-in (`cam-push-in`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | proven | 2026-10-05 | builder post move 1.127 for 1.14 asked (§52), grade A |

**Also called:** push in, dolly in, move in, slow push, creep in, pull in close, camera moves closer
**Not the same as:**
- [`cam-dolly-zoom`](dolly-zoom.md) - the subject holds size while the background changes
- [`cam-push-into-pov`](push-into-pov.md) - pushes into a head and becomes her eyes
- [`cam-pull-back`](pull-back.md) - the opposite direction; engines do it far less often
- [`cam-crash-zoom`](crash-zoom.md) - a fast zoom with a settle
- [`cam-locked-off`](locked-off.md) - what an unasked push-in ruins
- [`cam-rack-focus`](rack-focus.md) - the focus moves, not the camera

## Recipe (v3, 2026-09-05)

A push you can promise is a post move on a stabilised take; LTX will usually push anyway, by an amount no word controls.

1. **/film builder:** camera *push in* = `postmove`: the engine's own drift is stabilised first (when above 3% and measured with confidence), then the push is applied: 1.14 asked, 1.127 got. Studio pushes across the matrix measured within two points of the ask.
2. **Shot-script pipeline:** LTX pushes on most takes by itself; when a controlled push matters, render the move as previz (`studio/_tools/previz_blender.py` with `--radius` and `--radius-to`) or post-process.
3. Stand people farther back than the final framing (stand 0.40 for a wide, 0.22 for a medium) because the engine pushes.
4. Measure the push on the RAW render (`<take>_raw.mp4`), not the cropped one.

## Checks before picking

- The push measured against the ask; a runaway (past about 1.35) keeps its move and is reported.

## Progression

### 2026-07-30 · EDITING §10 · pushes across chained takes · grade C
- **Did:** a take continued over several links.
- **Got:** the push accumulated link after link.
- **Learned:** restate the camera in each link.

### 2026-09-04 · §38, §39, §46, §48 · LTX pushes in on every take · grade C
- **Did:** coverage films (THE STATION MASTER, NIGHT DINER) and make-all on LTX.
- **Got:** figures that started close ended cropped; a zoomed close-up lost 71% of its picture; Tomas's medium drifted 67% and 72%.
- **Learned:** stand people farther back; compose close-ups instead of pushing to them.

### 2026-09-05 · §50-§52 · push by words, then by arithmetic · grade A
- **Did:** LTX *push in* (10 takes); the keyword bench; a post push on a drifted take; then stabilise-then-push.
- **Got:** LTX *push in*: median 1.39, only half pushed. The bench: LTX *push in* 1.007 (no push); H3 [Push in] 36%, 16 points over its drift. A post push of 1.15 on a take that drifted 1.16 gave 1.31 ("the compounding law"). With stabilise first: 1.127 for 1.14.
- **Learned:** asked, done, measured - and the measurement chooses.

### 2026-09-05 · §54, §55 · rulers on the raw render; moves with mass · grade n/a
- **Did:** the drift and edge rulers read the raw render; second-order eases (`settle`).
- **Got:** shot 250: 1.15 asked, 1.147 measured; the eases' worst step error 0.026.
- **Learned:** measure the engine's picture, not the studio's crop.

### 2026-09-07 · §94 · a push pinned to another engine's close-up · grade D
- **Did:** a kiss beat pinned (first-last) to a Qwen close-up.
- **Got:** "the kiss is changing the camera view": a Qwen close-up has its own lens, hall and light, so the pin CUT to a different camera.
- **Learned:** for a move, both pinned frames must be composites of the same plate at two scales.

### 2026-09-30 · system-error 030; cyber-alchemist 101 · "The camera pushes in slowly" on LTX · grade A-
- **Did:** the push in words, in the shot-script pipeline.
- **Got:** slow push-ins, as LTX tends to do anyway.
- **Learned:** in this pipeline the push comes free; the size of it does not.

### 2026-10-05 · the fire esper 010, 020, 120 · a push-in as a shot option, in a 3D set · grade n/a
- **Did:** a `camera_move` option (shot_options.py: push_in 0.2-0.3 = 8-12% of the way to the subject) turned into the set's end camera; the set's two frames painted separately, H3 at 12 steps between them.
- **Got:** a slow creep in on the wide (010), on her prayer (020), into its eyes (120) - the two paintings of one place hold together; 120's push meets the roar.
- **Learned:** a push-in is an option now, not a default; a set film gets it exact from the set's two cameras - check `set_film.py check` before rendering (a push over a shoulder can run into it).

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a push nobody asked for | LTX's prior | stabilise (builder); stand people back | §38, §50 |
| a push much bigger than asked | the engine's drift compounds with the post move | stabilise first | §51 |
| rulers call a studio push "scene drift" | they read the cropped take | read `<take>_raw.mp4` | §54 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §38-§39, §41, §46, §48, §50-§55; `studio/_tools/cammeasure.py`.

## Open questions

- None open.
