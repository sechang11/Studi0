# Tilt (`cam-tilt`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | works-with-caveats | 2026-10-05 | builder tilt 10-12% (§53); cyber-alchemist 310 (previz), grade A- |

**Also called:** tilt up, tilt down, reveal by tilting up, pan up (to a face), tilt reveal, reveal by tilt
**Not the same as:**
- [`cam-whip-tilt`](whip-tilt.md) - the fast version, between two frames
- [`cam-pan`](pan.md) - the same turn, horizontally
- [`cam-crane`](crane.md) - the camera RISES; a tilt only turns

## Recipe (v2, 2026-09-30)

**/film builder:** a post move (10-12% measured). **Shot-script pipeline:** a previz with the look target moving (`previz_blender.py --look-z A --look-z-to B`), drawn by LTX-2.3 IC-LoRA; to END on a face, draw it the other way from the face's composed frame and reverse it (see [`cont-face-identity`](../continuity/face-identity.md)).

1. `"engine": "previz"`, `"previz": {"scene": "street", "radius": 1.0, "radius_to": 1.4, "lens": 35, "lens_to": 24, "cam_z": 1.58, "cam_z_to": 0.22, "look_z": 1.47, "look_z_to": 0.12, "figure_turn": 35, "reverse": true, "start": "anchor_311.png", "figure_glb": ...}`.
2. Name every garment the tilt passes ("the crimson velvet coat hanging open over her dark leather trousers") and put bare skin in the negative (`"avoid_extra"`).

## Checks before picking

- The costume is right in every frame of the move (the painter invents what the start frame did not show).
- The last frame is the composed frame.

## Progression

### 2026-09-05 · §52-§54 · tilt by words; tilt as a post move · grade B+
- **Did:** the keyword bench; the tilt and reveal-by-tilt entries.
- **Got:** LTX *tilt up* gave the same 86% push as *pan left* and *dolly in* (the seed decided). Post tilts measured 10-12%. Reveal by tilt first read "a different face" until the ruler was fixed to look inside the cropped window (0.42 → 0.64).
- **Learned:** measure inside the studio's window.

### 2026-09-30 · cyber-alchemist 310 v1 · previz tilt from a dressed start frame · grade D
- **Did:** the previz's first frame dressed into a start frame by Qwen-Image-2.1.
- **Got:** Qwen drew her full-length and far away, ignoring the low angle; the move had nothing to land on.
- **Learned:** do not trust a dress for framing; start from a frame the film already has.

### 2026-09-30 · cyber-alchemist 310 v2 · drawn down from 311's frame and reversed · grade B
- **Did:** the recipe above without the garment words.
- **Got:** a true rise from the boots to her face - with bare thighs and red briefs painted where she wears leather trousers.
- **Learned:** the painter invents what the start frame did not show.

### 2026-09-30 · cyber-alchemist 310 v3 · the trousers named, bare skin in the negative · grade A-
- **Did:** the recipe above.
- **Got:** boots, crimson coat, dark leather trousers, brass corset, gauntlet, her face with the silver iris; it lands on 311's first frame (seed 202, motion agreement 0.99).
- **Learned:** name what the move will reveal.

### 2026-09-30 · plaza 104 · a tilt up a tower in a 3D set · grade C+
- **Did:** the tilt as a camera in one set ([`pipe-3d-set`](../pipeline/3d-set.md)), drawn down from the clock and reversed; start frames dressed from the render (8 seeds from the tower's foot, 4 from its clock), a ControlNet start frame, and the set's depth alone (`pvb`).
- **Got:** every dress straightened the steep look up to eye level, and from the foot the tower's plain shaft became a house with a roof. From a straightened start the depth still pulled the take onto the set by its end (fit 0.34 -> 0.44); from the depth alone the angle was exact but the colours were its own (a maroon hall, dE 24-26 against the plate).
- **Learned:** a steep angle is where the start frame fails, not the set: keep a tilt's start gentle, or accept the depth-only look.

### 2026-10-05 · the fire esper 110, 160 · a tilt up as a shot option, in a 3D set · grade n/a
- **Did:** `camera_move` tilt_up 0.2 (5 degrees) with the esper rising over his shoulder (110), 0.35 (9 degrees) as it raises its hand to throw (160).
- **Got:** the tilt follows the thing rising; 110's push-in first try ran into his shoulder (the frame check caught it) - the tilt kept the over-the-shoulder framing.
- **Learned:** over a shoulder, tilt or pan; do not push.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a steep look up comes back level | the start frame's dress straightens perspective | a gentler angle, or the set's depth alone (`pvb`) | plaza 104 |
| a push instead of a tilt | the phrase is ignored | post move or previz | §52 |
| the move has nowhere to land | a dressed start frame ignored the framing | `"start"`: a frame the film has | 310 v1 |
| wrong or missing clothing on the way | not in the start frame, not named | name every garment; negative bare skin | 310 v2 |

## Evidence

- `studio/samples/fight/cyber-alchemist/pvr_310_s202.mp4`, `previz_310/`; `studio/LTX_PLAYBOOK.md` §52-§54.
- `studio/_tools/previz_blender.py` (`build_street`, `_move_camera`), `studio/_tools/previz_shot.py`.

## Open questions

- None open.
