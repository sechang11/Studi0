# Whip pan (`cam-whip-pan`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | works-with-caveats | 2026-09-30 | builder whip 25% (§53); quantum-courier 202, grade B+ |

**Also called:** whip pan, swish pan, snap pan, whip, fast pan
**Not the same as:**
- [`cam-pan`](pan.md) - the same turn at a readable speed
- [`cam-whip-tilt`](whip-tilt.md) - the same speed on the vertical axis, built between two frames

## Recipe (v2, 2026-09-30)

**/film builder:** a post move at zoom 1.25 (the travel cap), with a snap or a bounce ease. **Shot-script pipeline:** a fast tracking move in words on a start frame that already shows the subject side-on at speed.

## Checks before picking

- The travel reached (25% at zoom 1.25); motion blur present.

## Progression

### 2026-09-05 · §51, §53, §55 · the whip as a post move · grade B+
- **Did:** a post whip; then eases with mass.
- **Got:** 0.25 at zoom 1.16 returned 0.16, so the whip runs at 1.25; the entry measured a 25% pan; "snap pan" and "whip with a bounce" joined the picker.
- **Learned:** a whip needs the zoom to give it room.

### 2026-09-30 · quantum-courier 202 · the brief's "whip pan action shot" as side-on tracking · grade B+
- **Did:** "She sprints at full speed and the camera tracks alongside her in profile, fast", LTX seed 202.
- **Got:** a fast side-on run with the coat tails whipping.
- **Learned:** the brief's whip was delivered as a fast track; a true whip between two subjects was not tried.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the whip falls short | the travel cap | zoom 1.25 | §51 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §51, §53, §55; `studio/samples/fight/quantum-courier/shot_202_s202.mp4`.

## Open questions

- A whip pan between two subjects in the shot-script pipeline (first-last between the two framings, like [`cam-whip-tilt`](whip-tilt.md)).
