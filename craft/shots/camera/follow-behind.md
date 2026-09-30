# Following behind (`cam-follow-behind`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | works-with-caveats | 2026-09-30 | quantum-courier 203, grade B+ |

**Also called:** follow shot, tracking behind, chase from behind, follows her, over-the-back tracking
**Not the same as:**
- [`cam-fpv-chase`](fpv-chase.md) - a flying drone diving after a falling or flying subject
- [`cam-track-alongside`](track-alongside.md) - beside her, in profile

## Recipe (v1, 2026-09-30)

A start frame that already shows her from behind IN MOTION (her back view from her sheet, mid-stride); the follow in words; H3 when cloth or straps must whip.

## Checks before picking

- She is moving away (not standing); the camera keeps its distance.

## Progression

### 2026-08-03 · CINEMATOGRAPHY §5 #3 · "runs away ... camera tracks fast behind" · grade D
- **Did:** the run and the follow in the motion prompt over a keyframe of him standing.
- **Got:** he came back standing.
- **Learned:** the start frame must already show the motion the prompt describes (reading motion text against the keyframe caught 10 such shots).

### 2026-09-30 · quantum-courier 203 · low and close behind the running courier · grade B+
- **Did:** "a LOW CLOSE TRACKING SHOT behind the running woman" as the start frame; "the camera tracks low and close behind" (H3 seed 11).
- **Got:** coat tails and straps whipping as she runs away.
- **Learned:** a moving start frame gets a moving shot.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the runner stands still | a standing keyframe | draw the start frame mid-stride | CHRONO 030 |

## Evidence

- `craft/CINEMATOGRAPHY.md` §5; `studio/samples/fight/quantum-courier/h3_203_s11.mp4`.

## Open questions

- None open.
