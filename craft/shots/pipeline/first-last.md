# First-last frame (`pipe-first-last`)

| family | status | last tested | best result |
|---|---|---|---|
| pipeline | works-with-caveats | 2026-09-30 | cyber-alchemist 112, 210, grade A- |

**Also called:** first-last frame, FLF, start and end frame, keyframe interpolation, in-between
**Not the same as:**
- [`pipe-previz`](previz.md) - geometry for every frame; first-last only pins the ends
- [`pipe-key-poses`](key-poses.md) - a posed frame anchored between the two ends

## Recipe (v1, 2026-09-30)

`studio/_tools/flf_shots.py render`: LTX-2.5 first-last (`workflows/72_ltx25_flf2v.json`, both frames as guides at 0.9) and H3 first-last turbo (`workflows/65_minimax_h3_fl_turbo_v4.json`, 17n+5 frames). The two frames must be views of ONE moment in ONE space.

1. `"engine": "flf"`, `"flf": {"first": "end:<take>.mp4", "last": "anchor_<id>e.png"}`; the end frame is a `"engine": "key"` shot.
2. Both engines, two seeds.

## Checks before picking

- A move, not a cross-fade: look for doubled objects mid-take.

## Progression

### 2026-08-30 · §23 · pins hold in-place motion · grade B+
- **Did:** H3 first-last ("a pin") for turns and crouches.
- **Got:** near-locked frames; a crouch lowers across all 192 frames. A floor on change per second (0.009/s, later 0.002-0.0026 against the plate) separates pins that work from pins that invent.
- **Learned:** pin in-place motion above the floor.

### 2026-09-04 · §26, §29 · end frames on the pristine plate; walks not honoured · grade B
- **Did:** qwen-edited end frames; a pinned walk.
- **Got:** the regenerated background slid (a car moved); the pinned walk grew a path and trees.
- **Learned:** build end frames on the pristine plate; never pin a walk.

### 2026-09-06 · §60-§62 · the end frame differs in exactly one thing · grade A-
- **Did:** constructed end frames (`orb_end.py`, `figure_paste.py`).
- **Got:** the room held; asking qwen to change the frame changed the room.
- **Learned:** construct the end frame.

### 2026-09-07 · §71, §94 · both ends on one plate; frames that share provenance · grade A-
- **Did:** a worm's-eye step-over with both ends on the same plate; a pin to another engine's close-up.
- **Got:** the step-over worked first time; the pin to another engine's frame read as a CUT.
- **Learned:** the two frames must come from the same source.

### 2026-09-30 · cyber-alchemist 104 · between two angles-LoRA keys · grade D
- **Did:** keys that each invented the room.
- **Got:** a cross-fade of the room.
- **Learned:** the two frames must agree about the space.

### 2026-09-30 · cyber-alchemist 112, 210 · tilts within one space · grade A-
- **Did:** the previous take's end frame to a composed end frame.
- **Got:** real moves.
- **Learned:** as above.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a cross-fade | frames that disagree about the room | previz instead | cyber-alchemist 104 |

## Evidence

- `studio/_tools/flf_shots.py`.

## Open questions

- None open.
