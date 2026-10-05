# Screen direction across a scene (`cont-screen-direction`)

| family | status | last tested | best result |
|---|---|---|---|
| continuity | works-with-caveats | 2026-10-05 | the ember thief, 20 shots, grade A- |

**Also called:** the 180-degree rule, the line of action, crossing the line, facing the wrong way, who is on which side, eyeline direction, left-right continuity
**Not the same as:**
- [`frame-shot-reverse`](../framing/shot-reverse.md) - the two-shot cut back and forth in a conversation
- [`cont-place`](place.md) - the place itself staying the same place
- [`cont-shot-chain`](shot-chain.md) - each shot caused by the one before it

## Recipe (v1, 2026-10-05)

One line of action for the whole scene, every camera on one side of it, and every frame checked before it is drawn.

1. **The line:** in a set ([`pipe-3d-set`](../pipeline/3d-set.md)) the line runs between the two characters' marks; she comes from one end, he waits at the other. Pick the side every camera stands on (the ember thief: east, so Terra is always on the LEFT of the screen and attacks to the right, the jester always on the RIGHT).
2. **The check before anything renders:** for every shot's first and last frame, the camera is on the chosen side of the line through where the two of them stand (or last stood, if one is out of the shot), each visible character is inside the picture, each faces the other ON SCREEN (the facing vector against the camera's right vector), and nobody is seen from behind unless the shot is over their shoulder on purpose. `studio/shotscripts/_make_ember_thief_1005.py` refuses to write the film until all three hold; its first draft failed 9 frames (two cameras across the line, a character above the frame, two out of it).
3. **The facing the set draws must be the facing the set says:** `set_test.py cast` pastes the turnaround view of a character's sheet nearest the camera's side of her. The sheets name a view by the way the CAMERA went round (turn_right = the camera orbited right = it stands at her left, she faces screen-left); until 2026-10-05 the cast read the names the other way round and every side and three-quarter view went in mirrored. Fixed in `studio/_tools/set_test.py` (VIEWS8), and a three-quarter view drawn facing the same way as its twin (Terra's turn_front_l, the jester's turn_back_l) is replaced by the twin mirrored.
4. **The words say the directions too:** "she breaks into a sprint toward the right", "the orb streaks in from the right", "he flings it away to the left" - the same directions the frames show.
5. A crossing of the line, when the story needs one, is a shot of its own that shows the camera or the character moving round (not a cut).

## Checks before picking

- Look at every shot's two frames side by side before any take: she left, he right, facing each other.
- In a take: nobody turns round to face away mid-shot; an attack goes the way the words say.

## Progression

### 2026-10-01 · the duel in the clearing · cameras anywhere round the fight · grade C
- **Did:** 58 cameras placed shot by shot where each looked best; the cast pasted the sheet's views by the camera's side.
- **Got:** the director: "a lot of awkward striking and facing the wrong direction". D07's last frame: Terra in profile facing AWAY from the jester she is locked with - the views were mirrored (step 3), and cameras on both sides of the fight swapped who was on which side between cuts.
- **Learned:** the line is a rule, not a taste; and check the facing the frames actually draw.

### 2026-10-05 · the ember thief · one line, 20 cameras east of it, facing checked · grade A-
- **Did:** the recipe above; the mirror fixed; the maker's check on every frame.
- **Got:** in every two-shot of the 20 she is on the left and he on the right, facing each other; the set's frames drew the right profile every time (050: her three-quarter view facing right, his profile facing left). The check caught 9 bad frames in the first draft and, after a mark moved, a camera that had ended up BEHIND the jester (160: facing screen-left as asked, but his back to the lens) - the check now names a back view too.
- **Learned:** check the facing the frames actually draw, not the facing the marks say; and a camera can be on the right side of the line and still behind the character.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a character faces away from the one she fights | the sheet's turnaround view pasted mirrored | set_test.py VIEWS8 fixed 2026-10-05 | forest-duel D07 |
| who is on which side swaps between two cuts | the cameras stood on both sides of the line | one side for the scene, checked | forest-duel |
| a three-quarter view faces the wrong way on one side only | the sheet drew the left and right three-quarters the same way | the twin mirrored (`_same_facing`) | Terra's sheet, the jester's back pair |

## Evidence

- `studio/samples/fight/forest-duel/anchor_D07_end.png` (mirrored), `studio/samples/fight/ember-thief/anchor_*.png`, `blocking.png` (the 20 cameras from above).
- `studio/samples/settest/work/patch_1005/` (the fix and its before copy).

## Open questions

- A deliberate crossing (an orbit round the two) has not been written as a recipe of its own yet.
