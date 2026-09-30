# POV inside a helmet, with a HUD (`pov-helmet-hud`)

| family | status | last tested | best result |
|---|---|---|---|
| pov | works-with-caveats | 2026-09-30 | cyber-alchemist 208, grade B |

**Also called:** helmet POV, visor view, HUD POV, inside the helmet, heads-up display view
**Not the same as:**
- [`text-hud-overlay`](../text/hud-overlay.md) - the HUD graphics themselves; this is the whole shot through the visor
- [`pov-hands-in-frame`](hands-in-frame.md) - the same view without the visor and the HUD

## Recipe (v1, 2026-09-30)

Draw the visor's rim, the HUD and her hands into the start frame, so the painter only has to keep them; LTX.

1. Start frame (Qwen-Image-2.1 seed 11 picked, [her, her, place]): "a FIRST-PERSON POINT-OF-VIEW SHOT from inside a brass mechanical helmet looking out through its curved glass visor ... the rim of the helmet framing the view, a glowing blue heads-up display ... the display glitching with digital static ... the gloved hands of the woman at the bottom of the frame".
2. LTX; both seeds.
3. Prompt: "the blue heads-up display boots up across the visor, flickers and glitches with bursts of digital static and scanlines, then steadies".

## Checks before picking

- No face appears IN the visor (seed 202 put a stranger's face there, as if reflected).
- The glitch actually happens (it was slight in the cut).

## Progression

### 2026-09-30 · cyber-alchemist 208 · inside the helmet · grade B
- **Did:** the recipe above, LTX seeds 11 and 202.
- **Got:** seed 11 (in the cut) keeps the oval visor, the HUD and the view; the glitch is slight. Seed 202 painted a stranger's face inside the visor.
- **Learned:** a visor invites a face; check every frame.

### 2026-09-30 · cyber-alchemist 209-210 · the same visor over the railing and the shaft · grade A-
- **Did:** the same visor language in the railing and shaft frames; the tilt between them on first-last.
- **Got:** the oval visor held across the cut and the tilt.
- **Learned:** keep the visor's shape word-for-word across a sequence of POV frames.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a face appears in the visor | the painter reads a visor as a face-holder | pick another seed | 208 seed 202 |
| the glitch barely shows | a HUD glitch is small at delivery size | glitch it in post, or a bigger HUD | 208 |

## Evidence

- `studio/samples/fight/cyber-alchemist/shot_208_s11.mp4`, `shot_208_s202.mp4`.

## Open questions

- A post-applied glitch (scanlines, RGB split) over the take.
