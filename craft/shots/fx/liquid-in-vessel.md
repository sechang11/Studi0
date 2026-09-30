# Liquid moving in a vessel (`fx-liquid-in-vessel`)

| family | status | last tested | best result |
|---|---|---|---|
| fx | works-with-caveats | 2026-09-30 | system-error 050, grade A-; cyber-alchemist 114, grade C+ |

**Also called:** swirling broth, liquid in a glass, mercury in a vial, noodles lifted from broth, pouring, stirring
**Not the same as:**
- [`fx-glass-shatter`](glass-shatter.md) - the vessel breaking; here the liquid stays inside it

## Recipe (v1, 2026-09-30)

Draw the liquid's look into the start frame at a size that reads, and keep the vessel still in the frame; H3 for things lifted out of it.

1. Start frame: the vessel large in frame with the liquid's colour and shine already visible (iridescent broth, silver mercury).
2. H3 for lifting something out (noodles on chopsticks); LTX for a gentle tilt.
3. Prompt: the liquid's motion ("swirling", "rolls inside the glass like a heavy mirror").

## Checks before picking

- The liquid reads as the right substance (mercury as silver, not clear glass).
- The vessel does not grow toward the lens.

## Progression

### 2026-09-30 · system-error 050 · glowing noodles lifted from swirling iridescent broth · grade A-
- **Did:** a start frame that was an extreme close-up of the bowl with the chopsticks already in the gloved hand; "The chopsticks lift the glowing noodles slowly up out of the broth; the translucent strands stretch and sway, broth drips from them in bright droplets back into the swirling bowl ... The camera holds close and still." H3 seed 202.
- **Got:** glowing translucent noodles hang from the chopsticks over an iridescent broth.
- **Learned:** H3 lifts something out of a liquid cleanly.

### 2026-09-30 · cyber-alchemist 114 · mercury rolling in a vial at eye level · grade C+
- **Did:** LTX, two seeds.
- **Got:** seed 202 (in the cut) is stable but the vial looks clear, not mercury. Seed 11 swelled the vial into a giant glass bulb toward the camera.
- **Learned:** the substance must be unmistakable in the start frame; LTX can inflate a held object toward the lens.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| mercury looks like clear glass | the start frame drew an empty-looking vial | a start frame with silver liquid clearly visible | 114 |
| the vessel swells toward the lens | LTX pushes a held object | pick the stable seed; shorter take | 114 seed 11 |

## Evidence

- `studio/samples/fight/system-error/h3_050_s202.mp4`; `studio/samples/fight/cyber-alchemist/shot_114_s202.mp4`.

## Open questions

- A pour (liquid leaving the vessel in a stream).
