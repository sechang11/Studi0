# HUD and interface graphics (`text-hud-overlay`)

| family | status | last tested | best result |
|---|---|---|---|
| text | works-with-caveats | 2026-09-30 | cyber-alchemist 208-210, grade B |

**Also called:** HUD, heads-up display, interface overlay, screen graphics, visor readouts
**Not the same as:**
- [`text-legible-sign`](legible-sign.md) - words that must be read
- [`pov-helmet-hud`](../pov/helmet-hud.md) - the whole POV shot the HUD sits in
- [`text-screen-change`](screen-change.md) - screen content that changes during the shot

## Recipe (v1, 2026-09-30)

Draw the HUD into the start frame; the engine keeps it. Its readouts are decoration unless spelled out.

## Checks before picking

- The HUD stays on the glass (does not slide with the scene).

## Progression

### 2026-09-30 · cyber-alchemist 208-210 · a blue HUD on the visor · grade B
- **Did:** HUD in the start frames; LTX.
- **Got:** it stays; the glitch asked for is slight.
- **Learned:** a glitch is easier to add in post than to ask for.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the glitch barely shows | small at delivery size | post effect | cyber-alchemist 208 |

## Evidence

- `studio/samples/fight/cyber-alchemist/shot_208_s11.mp4`, `anchor_208_flux2.png`.

## Open questions

- A post glitch pass.
