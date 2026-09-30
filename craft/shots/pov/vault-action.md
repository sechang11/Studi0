# POV of a physical action (`pov-vault-action`)

| family | status | last tested | best result |
|---|---|---|---|
| pov | works-with-caveats | 2026-09-30 | quantum-courier 208, grade B+ |

**Also called:** POV vault, first-person parkour, vaulting POV, POV climb, POV jump
**Not the same as:**
- [`pov-hands-in-frame`](hands-in-frame.md) - hands gripping or resting; here the whole body acts through the hands
- [`pov-walk-run`](walk-run.md) - the stride alone

## Recipe (v1, 2026-09-30)

H3. LTX turned the POV vault into a third-person somersault by a stranger.

1. Start frame: the hands planted on the obstacle from her POV, her sleeves visible.
2. `"engine": "both"`; pick H3.
3. Prompt (208): "First-person view: her gloved hands slam down on the barrier and she vaults over it; the camera swings up and over, then jolts hard and tilts down as she lands on the far side."

## Checks before picking

- The camera stays first-person through the whole action: no body appears in front of the lens.

## Progression

### 2026-09-30 · quantum-courier 208 · POV vault over a concrete barrier · grade B+
- **Did:** the recipe above, both engines.
- **Got:** H3 seed 11 kept the POV: up, over, a jolt on landing (in the cut). Both LTX takes turned it into a stranger somersaulting over the barrier in third person.
- **Learned:** a POV body action goes to H3.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a stranger somersaults in front of the camera | LTX loses first person during a body action | H3 | quantum-courier 208 LTX |

## Evidence

- `studio/samples/fight/quantum-courier/h3_208_s11.mp4`.

## Open questions

- A longer POV action (climb, fall) on H3.
