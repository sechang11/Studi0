# POV walking or running (`pov-walk-run`)

| family | status | last tested | best result |
|---|---|---|---|
| pov | works-with-caveats | 2026-09-30 | quantum-courier 207, grade B+ |

**Also called:** first-person view, POV shot, body cam, running POV, point of view, first person
**Not the same as:**
- [`cam-push-into-pov`](../camera/push-into-pov.md) - the move that hands over INTO the POV; this is the POV shot itself
- [`cam-handheld`](../camera/handheld.md) - a shaky third-person camera; a POV is the character's own eyes
- [`frame-over-the-shoulder`](../framing/over-the-shoulder.md) - the character is in the frame; in a POV she is the camera
- [`pov-vault-action`](vault-action.md) - a POV of a physical action with the hands; walking or running is the stride alone
- [`pov-drift`](drift.md) - a slow glide through a place with no body in view

## Recipe (v1, 2026-09-30)

A start frame drawn as the POV itself, with her own hands (gloves, sleeves) at the bottom of the frame; LTX; the stride in words.

1. Start frame (Qwen-Image-2.1 with [place, her]): "a FIRST-PERSON POINT-OF-VIEW SHOT running down the corridor ... two hands in matte black tactical gloves reaching forward at the bottom of the frame".
2. LTX.
3. Prompt: "First-person view: the camera bobs with her running stride as the barrier rushes closer; her gloved hands reach out in front."

## Checks before picking

- No one else's body enters the frame from "her" position.
- The hands keep her gloves and sleeves (the amber circuit on the left sleeve).

## Progression

### 2026-09-30 · quantum-courier 207 · running POV toward a barrier · grade B+
- **Did:** the recipe above, LTX seed 11.
- **Got:** a running POV with her gloved hands reaching forward.
- **Learned:** drawing the POV into the start frame, hands included, is what makes it a POV.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| (none recorded for the stride itself) | | | |

## Evidence

- `studio/samples/fight/quantum-courier/shot_207_s11.mp4`.

## Open questions

- A long walking POV (over 5 s) through a changing space.
