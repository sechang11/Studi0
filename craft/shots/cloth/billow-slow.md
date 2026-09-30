# Cloth billowing slowly (`cloth-billow-slow`)

| family | status | last tested | best result |
|---|---|---|---|
| cloth | proven | 2026-09-30 | cyber-alchemist 204, grade A |

**Also called:** billowing cape, coat lifting, fabric rising, cape floating up, cloth in reversed gravity, shockwave billow
**Not the same as:**
- [`cloth-whip-fast`](whip-fast.md) - violent flapping in a high wind; billowing is slow and lifted
- [`cloth-knit-texture`](knit-texture.md) - the surface detail of a fabric; here the whole garment moves

## Recipe (v1, 2026-09-30)

A start frame with the cloth ALREADY lifted, on H3 when something else moves too (papers, glass).

1. Start frame: the cape or coat tails already raised (Flux 2 drew the cape lifted high "like wings" for 204; Qwen spread it sideways).
2. `"engine": "both"`; H3 picked for 204, LTX for the Courier's slow rise.
3. Prompt: what lifts it and where it goes ("her coat tails and patched cape lift and billow upward").

## Checks before picking

- The cloth keeps its pattern and edges (no melting into the body).
- It moves the way the force says (upward for reversed gravity).

## Progression

### 2026-08-03 · CINEMATOGRAPHY §5 · what to move instead of faces · grade n/a
- **Did:** motion prompts across CHRONO.
- **Got:** faces morph when asked to act; cloth and hair do not.
- **Learned:** move hair, cloth and light.

### 2026-09-04 · §42 · the ambient word "cloth" · grade D
- **Did:** "hanging cloth and banners lift in the wind" as an ambient phrase.
- **Got:** it drew bunting in a park.
- **Learned:** "an ambient word is a noun the model will draw".

### 2026-09-30 · cyber-alchemist 204 · shockwave lifts the coat and cape · grade A
- **Did:** a Flux 2 start frame with the cape raised; LTX and H3.
- **Got:** LTX (both seeds) billowed the cape upward well. H3 did too and also threw papers and flasks around her; H3 seed 202 is in the cut.
- **Learned:** a billow alone is safe on either engine; H3 adds the things around it.

### 2026-09-30 · quantum-courier 304, 306 · the coat billows skyward as gravity reverses · grade A-
- **Did:** 304 "her coat billows softly up toward the sky as if gravity has turned over" (H3 seed 202); 306 "her coat spreading upward like wings" (LTX seed 11).
- **Got:** both read.
- **Learned:** a slow billow is safe on either engine when the start frame has it lifted.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the cape spreads sideways instead of up | the start frame drew it that way | a start frame with the cape raised (Flux 2 drew it) | 204 Qwen candidates |

## Evidence

- `studio/samples/fight/cyber-alchemist/h3_204_s202.mp4`; `studio/samples/fight/quantum-courier/h3_304_s202.mp4`, `shot_306_s11.mp4`.

## Open questions

- None open.
