# Thruster flames (`fx-thruster-flames`)

| family | status | last tested | best result |
|---|---|---|---|
| fx | proven | 2026-09-30 | cyber-alchemist 306, 308, grade A- |

**Also called:** jetpack flames, jets firing, rocket exhaust, thrusters igniting, blue flames
**Not the same as:**
- [`cont-prop-state`](../continuity/prop-state.md) - the jetpack unfolding (the object changing state); flames are the effect it produces
- [`fx-fire`](fire.md) - flame in the scene itself (torches, candles)

## Recipe (v1, 2026-09-30)

Flux 2 for the start frame (Qwen put the helmet on her back instead of the jetpack), then H3 for the ignition.

1. Start frame: Flux 2 ref3 with [place, her back view, the helmet], the jetpack visible on her back.
2. H3 for the ignition; LTX carries flames that are already burning (the descent).
3. Prompt: what ignites and the colour ("nozzles swinging open and igniting in bright blue flame").

## Checks before picking

- The flames come out of the nozzles, not her hands (seed 202's vertigo start frame put the flames at her hands).
- The jetpack is on her back and the helmet on her head.

## Progression

### 2026-09-30 · cyber-alchemist 306 · the jetpack deploys and ignites · grade A-
- **Did:** Flux 2 start frame; LTX and H3, two seeds.
- **Got:** H3 seed 11 unfolds and ignites four blue flames (in the cut). Both Qwen start frames had painted the round helmet on her back in place of the jetpack.
- **Learned:** check what the compositor put on her back.

### 2026-09-30 · cyber-alchemist 307, 308 · jets during the dolly zoom and the descent · grade A-
- **Did:** flames already burning in the start frames.
- **Got:** steady blue jets; the puddle rings under her in 308.
- **Learned:** continuing flames are safe on LTX.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the helmet on her back instead of the jetpack | Qwen merged two brass objects | Flux 2 start frame | 306 anchors |
| flames from her hands | the start frame placed them there | check where the flames start before picking a start frame | 307's prompt-only takes (Qwen seed 202 start frame) |

## Evidence

- `studio/samples/fight/cyber-alchemist/h3_306_s11.mp4`, `shot_308_s11.mp4`; anchors board 4.

## Open questions

- None open.
