# Locked-off camera (`cam-locked-off`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | works-with-caveats | 2026-09-30 | builder stabilise 1.016 (§51); cyber-alchemist 102, grade B+ |

**Also called:** static, static shot, locked off, tripod shot, still camera, no camera movement, hold the frame
**Not the same as:**
- [`cam-push-in`](push-in.md) - the move a "static" LTX take usually makes on its own
- [`cam-handheld`](handheld.md) - a camera that moves a little on purpose

## Recipe (v3, 2026-09-05)

Do not ask the engine to hold still: it pushes in. Hold the frame by arithmetic, by a pin, or by keeping the take short.

1. **/film builder:** camera *static* means the `postmove` stabilise pass: the engine's drift is measured and cropped out (1.163 → 1.016, pan 0.000, tilt 0.001). Past about 1.35x it over-corrects; such a take keeps its move and a runaway fault is raised (§55).
2. **A pin** (H3 first-last with both ends on the same plate, §71): holds the frame near-locked. **The camera rig** (`still_push` at zero) holds it exactly, with no generation.
3. **Shot-script pipeline (fight.py):** no stabilise pass yet. Keep static shots short and trim them (cyber-alchemist 102 was cut to 2.5 s).

## Checks before picking

- Zoom, pan and tilt between the first and last frames (`cammeasure`): a static take that ended 6% closer has pushed.

## Progression

### 2026-07-30 · CINEMATOGRAPHY §5b · "Nothing else moves." · grade D
- **Did:** a still subject with that sentence in a 15-minute film.
- **Got:** a 1.54 s freeze, caught by `freezedetect` at 761 s. The freeze that shipped was in the third link of a chained take ("stop dead"); a text search flagged 8 shots and only 1 froze.
- **Learned:** the subject may be still, the frame may not: keep ambient movement and a slow camera move; let `freezedetect=n=-60dB:d=0.7` decide.

### 2026-08-30 · §23 · "static" by prose on LTX · grade D
- **Did:** camera *static*, then the prompt enhancer off, then a locked-off-tripod clause, then the action first in capitals.
- **Got:** the clip zoomed in every time; frame 0 was 0.081 from the composite, so the zoom is the engine's prior.
- **Learned:** a camera option is only `enforced` when it is pinned.

### 2026-09-04 · §49 · "The camera is locked off on a tripod; the framing never changes" · grade D
- **Did:** shot 010 again on two seeds with that sentence.
- **Got:** 3 of 3 new takes ended closer than they started, like the 3 before.
- **Learned:** the push-in is the engine's prior, not a wording problem.

### 2026-09-05 · §50-§52 · 625 takes measured; stabilise · grade B+
- **Did:** measured every take on disk by engine and camera word; built `postmove` stabilise.
- **Got:** LTX *static* (180 takes): median zoom 1.02, 45% pushed in more than 6%, 10% pulled back, 21% panned. H3 *static* (71): median 1.06. H3 pinned (20): 1.000. Rig (14): 1.000. An empty wide drifted 1.09-1.16; stabilised to 0.986, then (holding pan and tilt too) 1.016. The keyword bench at seed 4242: LTX *static* 1.005 (still), H3 *static* pushed 20% and panned 12%, H3 [Static shot] panned 16%.
- **Learned:** "a camera word is a coin flip"; stillness is done by arithmetic.

### 2026-09-05 · §55 · a runaway on a still shot · grade n/a
- **Did:** swept 11 shots with angles and mass.
- **Got:** a take pushed 204% on a shot asking to hold still, with no fault; 2 of 11 ran away, both at the night diner.
- **Learned:** a runaway is now a fault by name.

### 2026-09-06 · §60 · "locked off, no zoom, the hall stays exactly as it is" on H3 · grade D
- **Did:** the words on H3.
- **Got:** the staircase narrowed, the arches shifted, the torches walked.
- **Learned:** an element only described is reinvented every step; a first-last pin holds the room.

### 2026-09-30 · cyber-alchemist 102 · the static master on LTX · grade B+
- **Did:** "She stands completely still ... The camera is locked off, perfectly still", LTX seed 11.
- **Got:** near-still, with a small change by the end; trimmed to 2.5 s before the orbit.
- **Learned:** in the shot-script pipeline, keep static shots short.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a static shot pushes in | LTX's prior | stabilise (builder), a pin, or short takes | §23, §49, §50 |
| a runaway push on a still shot | a place that makes the engine bolt | the runaway fault; roll again | §55 |
| the room changes on a "locked" H3 shot | described elements are reinvented | a first-last pin | §60 |
| the picture freezes | nothing left moving | ambient movers and a slow move; `freezedetect` | CHRONO |

## Evidence

- `studio/LTX_PLAYBOOK.md` §23, §49, §50-§52, §55, §60, §71; `studio/_tools/cammeasure.py`.

## Open questions

- A stabilise pass in fight.py's finish.
