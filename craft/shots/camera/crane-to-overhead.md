# Crane up to overhead (`cam-crane-to-overhead`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | works-with-caveats | 2026-09-30 | quantum-courier 107-109, grade A- |

**Also called:** crane up to top-down, rise to bird's eye, boom up overhead, over the shoulder to aerial
**Not the same as:**
- [`cam-crane`](crane.md) - a vertical rise that keeps the camera looking roughly level; this one ends looking straight down
- [`frame-overhead-aerial`](../framing/overhead-aerial.md) - the static top-down framing itself; this is the move into it

## Recipe (v1, 2026-09-30)

Three shots that cut as one move: the start framing, the rise, and the top-down, each from its own composed start frame.

1. The start: an over-the-shoulder frame (Qwen-Image-2.1 with [her back view from her sheet, the place]).
2. The rise: a start frame that is ALREADY a high angle looking steeply down, with her in the centre. Its references are [the place from above, her]. The place from above is a `"place_view": [place, "angle_aerial"]` made by the angles LoRA through `studio/_tools/sheet_refs.py`. Prompt: "The camera cranes straight up and away from her, rising until it looks directly down on the market; she stays in the centre of the frame". LTX.
3. The top-down: a start frame straight down with her in the exact centre, same references. Prompt: "Static camera".
4. Cut on her motion, so the three read as one move.

## Checks before picking

- Her hair colour and coat visible and centred in the top-down (the brief's test).
- The crowd does not grow a second her.

## Progression

### 2026-09-30 · quantum-courier 107 → 108 → 109 · three shots cut as one rise · grade A-
- **Did:** the recipe above (LTX s11, s11, s202).
- **Got:** it reads as one crane from over her shoulder to straight down, with her blue hair centred in the market.
- **Learned:** a move that ends in a very different framing is easier as cuts along its path than as one generation.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| (none recorded yet) | | | |

## Evidence

- `studio/samples/fight/quantum-courier/shot_108_s11.mp4`, `shot_109_s202.mp4`; `ref_market_high.png` (the place from above).
- `studio/_tools/sheet_refs.py`.

## Open questions

- One continuous crane (previz of a rising camera) - not tried.
