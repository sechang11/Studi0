# Backlit silhouette (`frame-silhouette-backlit`)

| family | status | last tested | best result |
|---|---|---|---|
| framing | works-with-caveats | 2026-09-30 | quantum-courier 313-314, grade B+ |

**Also called:** silhouette, backlit figure, against the sun, sunset silhouette, rim-lit figure
**Not the same as:**
- [`frame-wide-with-figure`](wide-with-figure.md) - a lit figure; here she is a dark shape against the light

## Recipe (v2, 2026-09-30)

Write the light's direction into the start frame: "the huge orange sun directly behind her so she is backlit and almost a silhouette, orange rim light". A figure lit from the front in front of the sun looks pasted on.

1. Start frame: Flux 2 or Qwen (313 was Flux 2, 314 Qwen seed 202) with [place at sunset, her, her].
2. LTX; she hovers; the camera pulls back or holds.

## Checks before picking

- The figure's light comes from behind (rim), not from the camera.
- Anything that must show in the silhouette (a glowing sleeve) is big enough to read.

## Progression

### 2026-08-03 · CINEMATOGRAPHY §2.1 · what survives across shots · grade A-
- **Did:** a helmeted character and a red scarf across CHRONO.
- **Got:** the helmet and the scarf held in every shot; a face about 200 px high was reinvented each time.
- **Learned:** silhouettes and signature shapes survive where faces do not.

### 2026-09-30 · quantum-courier 313-314, first start frames · lit from the front against the sun · grade D
- **Did:** start frames that placed her in front of the setting sun without saying where her light came from.
- **Got:** she was lit from the front against a sun behind her: a cut-out.
- **Learned:** the light must agree with the sun.

### 2026-09-30 · quantum-courier 313-314, redrawn · backlit · grade B+
- **Did:** the recipe above; new takes (313 seed 202, 314 seed 11).
- **Got:** a real silhouette against the sun. The amber sleeve's glow does not read at that size.
- **Learned:** a small glowing detail disappears in a silhouette.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the figure looks pasted on | lit from the front against the light | backlight her in the words | quantum-courier 313-314 v1 |
| a glowing detail vanishes | too small in a wide silhouette | a closer shot for the detail | quantum-courier 314 |

## Evidence

- `studio/samples/fight/quantum-courier/shot_313_s202.mp4`, `shot_314_s11.mp4`.

## Open questions

- None open.
