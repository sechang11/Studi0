# Running (`move-run`)

| family | status | last tested | best result |
|---|---|---|---|
| motion | works-with-caveats | 2026-09-30 | quantum-courier 111, 201, 202, grade B+ |

**Also called:** run, sprint, running away, chase on foot, breaks into a run
**Not the same as:**
- [`move-walk-toward-camera`](walk-toward-camera.md) - a walk; the face matters more and lasts about 4 s
- [`move-fall`](fall.md) - the body leaves the ground

## Recipe (v1, 2026-09-30)

Start frames that already show the run (mid-stride, the coat flaring); LTX for the runs; H3 for the cloth behind her; the camera's job in words.

1. Start frames: "breaking into a run ... her coat flaring" (111), "bursting in at the far end, running toward the camera" (201), side-on from her sheet's side view (202).
2. LTX (seeds 11/202 in the cut); the coat tails on H3 (203).
3. Prompt: the direction and the camera ("The camera whips after her", "Static camera", "tracks alongside her in profile, fast").

## Checks before picking

- Her face on the runs that face the camera (a run is a motion shot: the ranker flagged 111 and 202 for drift).

## Progression

### 2026-08-03 · CINEMATOGRAPHY §5 #3, EDITING §5 · a run over a standing keyframe · grade D
- **Did:** 030_crono "runs away ... camera tracks fast behind".
- **Got:** he came back standing; a run should last 2.5-3.0 s.
- **Learned:** the start frame shows the run already.

### 2026-09-30 · quantum-courier 111, 201, 202, 203 · running through a market and a corridor · grade B+
- **Did:** the recipe above.
- **Got:** all read as runs; 111 (0.41) and 202 (0.50) were picked as "fewest faults" on face drift.
- **Learned:** in a run the face drifts; keep faces for the still beats.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| face drift | a moving head | pick by eye; keep runs short | quantum-courier 111, 202 |

## Evidence

- `studio/samples/fight/quantum-courier/shot_111_s11.mp4`, `shot_201_s11.mp4`, `shot_202_s202.mp4`, `h3_203_s11.mp4`.

## Open questions

- None open.
