# Extreme close-up of an eye (`frame-ecu-eye`)

| family | status | last tested | best result |
|---|---|---|---|
| framing | proven | 2026-09-30 | quantum-courier 102; cyber-alchemist 111, grade A- |

**Also called:** ECU, extreme close-up, eye macro, macro of the eye, iris shot, eye detail
**Not the same as:**
- [`frame-close-up-face`](close-up-face.md) - the whole face
- [`frame-macro-object`](macro-object.md) - a macro of a thing; an eye macro carries identity

## Recipe (v1, 2026-09-30)

Flux 2 for the start frame (it obeys "extreme macro"; Qwen came back with half a face), with the eye's side written in picture terms; LTX; a blink or a refocus.

1. Start frame: Flux 2 ref3 with [her face view, her reference, place]: "an EXTREME MACRO CLOSE-UP of the left eye ... the pupil adjusting, individual lashes and skin pores".
2. LTX; "she blinks once", "the iris rotates and refocuses". Macro lens, static.
3. The design of the eye must match her close-ups (see [`cont-asymmetric-mark`](../continuity/asymmetric-mark.md)).

## Checks before picking

- It is the correct eye (her left: the nose is to the picture's LEFT of it).
- The iris matches the close-ups.

## Progression

### 2026-09-30 · quantum-courier 102 · her left eye and nose ring, rain on the cheek · grade A-
- **Did:** the macro in the start frame; LTX seed 11.
- **Got:** the eye, the ring and the raindrop.
- **Learned:** the macro holds on LTX.

### 2026-09-30 · cyber-alchemist 111 · the silver iris · grade A-
- **Did:** both compositors; Flux 2 picked by override (Qwen seeds came back as a close-up of half the face).
- **Got:** an ECU with the iris turning; both LTX seeds blinked. Flux 2 drew mechanical rings where her close-ups show a plain silver iris.
- **Learned:** Flux 2 for the framing; state the eye's design so the macro and the close-ups agree.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| half a face instead of an eye | Qwen ignores "extreme macro" | Flux 2 | cyber-alchemist 111 |
| the eye's design differs from the close-ups | Flux 2 reinvents the detail | describe the design in words | cyber-alchemist 111 |

## Evidence

- `studio/samples/fight/cyber-alchemist/anchor_111_flux2.png`, `shot_111_s11.mp4`; `studio/samples/fight/quantum-courier/shot_102_s11.mp4`.

## Open questions

- None open.
