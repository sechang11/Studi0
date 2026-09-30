# Pan (`cam-pan`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | proven | 2026-09-05 | builder post pan 0.119 for 0.12 (§50), grade A |

**Also called:** pan, pan left, pan right, panning shot, swing the camera
**Not the same as:**
- [`cam-arc`](arc.md) - the camera travels round the subject; a pan turns where it stands, with no parallax
- [`cam-whip-pan`](whip-pan.md) - a pan so fast it blurs
- [`cam-tilt`](tilt.md) - the same turn, vertically
- [`cam-track-alongside`](track-alongside.md) - the camera travels sideways with a subject

## Recipe (v2, 2026-09-05)

A post move (`postmove` pan). Its travel is capped by the zoom it runs inside: (1 - 1/z)/2 per side.

## Checks before picking

- Pan measured against the ask; people appearing in an empty pan (a known fault).

## Progression

### 2026-09-05 · §50-§52 · pans by words, and by arithmetic · grade A
- **Did:** measured static takes; the keyword bench; post pans.
- **Got:** LTX static takes panned 21% of the time, H3 32%. At seed 4242, LTX *pan right* panned 42% (the only LTX phrase of seven that obeyed); LTX *pan left* pushed 86%; H3 *pan left* and [Pan left] pushed 39% and 41%. A post pan of 0.12 measured 0.119; 0.25 at zoom 1.16 returned 0.16 (the travel cap).
- **Learned:** stop asking; pan in post, inside enough zoom.

### 2026-09-05 · §53, §54 · the pan entry on an empty place · grade B
- **Did:** built once, then three seeds.
- **Got:** 14% pan right; people appeared in the empty shot on 1 of 3 seeds, and the pick took another.
- **Learned:** render several; let the measurement choose.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| "pan left" pushes in | the engine ignores the phrase | post move | §52 |
| the pan falls short | the zoom's travel cap | more zoom | §51 |
| people appear in an empty pan | the engine's prior | seeds; the empty-shot fault | §53-§54 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §50-§54.

## Open questions

- A pan in the shot-script pipeline (none of the 2026-09-30 films needed one).
