# Overhead, straight down (`frame-overhead-aerial`)

| family | status | last tested | best result |
|---|---|---|---|
| framing | proven | 2026-09-30 | quantum-courier 109; cyber-alchemist 308, grade A- |

**Also called:** top-down, bird's eye, aerial view, overhead shot, god's eye view, straight down, birds eye
**Not the same as:**
- [`frame-high-angle`](high-angle.md) - looking down at an angle
- [`cam-crane-to-overhead`](../camera/crane-to-overhead.md) - the move that arrives at this framing

## Recipe (v1, 2026-09-30)

The place turned to the aerial by the angles LoRA as a made reference (`"place_view": [place, "angle_aerial"]`), or Flux 2 for a composed aerial; her centred; LTX.

## Checks before picking

- She stays centred and readable (hair colour, coat) among what surrounds her.

## Progression

### 2026-08-03 · CINEMATOGRAPHY §1.3 · a named thing seen from above · grade D
- **Did:** "a continent burning from above".
- **Got:** a map of Europe and North Africa.
- **Learned:** say "an unnamed continent": names and similes are drawn literally.

### 2026-09-05 · §55 · the builder's bird's eye · grade B
- **Did:** the keystone at its clamp.
- **Got:** pitch -0.75: "a camera raised and tilted, not a camera flown".
- **Learned:** a true overhead needs a plate drawn from above.

### 2026-09-30 · quantum-courier 109; cyber-alchemist 308 · the market from above; her descent on jets · grade A-
- **Did:** 109: [the market from above, her], Qwen; LTX seed 202. 308: Flux 2 aerial (Qwen drew a flat street view), LTX seed 11.
- **Got:** her blue hair centred in the crowd; puddle rings under her jets.
- **Learned:** a made aerial reference keeps the place the same place.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a street-level view instead of an aerial | Qwen ignores the framing | Flux 2 | cyber-alchemist 308 |

## Evidence

- `studio/samples/fight/quantum-courier/ref_market_high.png`, `shot_109_s202.mp4`; `studio/samples/fight/cyber-alchemist/shot_308_s11.mp4`.

## Open questions

- None open.
