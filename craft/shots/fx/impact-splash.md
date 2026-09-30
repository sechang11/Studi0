# Splash from an impact into liquid (`fx-impact-splash`)

| family | status | last tested | best result |
|---|---|---|---|
| fx | proven | 2026-09-30 | cyber-alchemist 309, grade A |

**Also called:** puddle splash, boots hit the water, landing splash, feet splash, splashdown
**Not the same as:**
- [`fx-glass-shatter`](glass-shatter.md) - a brittle object breaking; here something lands in liquid
- [`fx-surface-spray`](surface-spray.md) - fine spray thrown off a wet surface by repeated strikes; a splash is one heavy impact
- [`fx-impact-burst`](impact-burst.md) - dust or ash thrown up at a strike; LTX makes it a standing haze

## Recipe (v1, 2026-09-30)

A ground-level start frame at the moment of contact, on H3. LTX whites out the frame.

1. Start frame: Flux 2 ref3 at puddle level with the feet just touching down (Qwen drew full figures standing instead).
2. `"engine": "both"`; pick H3.
3. Prompt: "Her boots hit the wet asphalt and the puddle explodes outward in a ring of neon-lit spray; the jets cut out with a sigh; steam curls around her boots."

## Checks before picking

- The frame never whites out.
- The feet are still there after the spray settles.

## Progression

### 2026-09-30 · cyber-alchemist 309 · boots into a neon puddle, LTX and H3 · grade A
- **Did:** the recipe above, seeds 11 and 202.
- **Got:** LTX (both) threw a spray that filled the frame white at about 1 s, then settled. H3 seed 11 landed the boots with a clean ring of spray and steam after. H3 seed 11 is in the cut.
- **Learned:** H3 for impacts into liquid.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the frame goes white for half a second | LTX exaggerates the spray | H3 | 309 LTX |
| full figures instead of feet | Qwen compositor ignored "ground-level" framing | Flux 2 for the start frame | 309 anchors |

## Evidence

- `studio/samples/fight/cyber-alchemist/h3_309_s11.mp4`; strips `ltx_p3b.jpg`, `h3_b.jpg`.

## Open questions

- A splash with the whole figure in frame.
