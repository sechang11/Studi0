# Macro of an object (`frame-macro-object`)

| family | status | last tested | best result |
|---|---|---|---|
| framing | works-with-caveats | 2026-09-30 | cyber-alchemist 113; smallest-gear 030, 070, grade A- |

**Also called:** macro, extreme close-up of an object, detail shot, insert of a mechanism, product macro
**Not the same as:**
- [`frame-ecu-eye`](ecu-eye.md) - a macro of an eye; identity rides on it
- [`frame-insert-hands`](insert-hands.md) - hands doing something; here the object is the subject
- [`frame-insert-detail`](insert-detail.md) - a small true detail of the place, not a hero object

## Recipe (v1, 2026-09-30)

Both compositors (Qwen was the closer one for the gauntlet, Flux 2 for others); for a mechanism that must move in a precise way, H3.

1. `fight.py --anchors --compositor best`; pick the closer framing by eye.
2. `"engine": "both"` when the mechanism moves: LTX made the watch's gears rise out of it; H3 turned them in place.
3. Prompt: the one thing that moves and how ("the tiny golden gear settles onto its spindle, the gears engage").

## Checks before picking

- Parts move in place (nothing floats out of the mechanism).

## Progression

### 2026-08-03 · CINEMATOGRAPHY §3 · macros in CHRONO · grade A-
- **Did:** three macros (the watch).
- **Got:** all three landed; they were the best continuity in the film.
- **Learned:** one insert per act.

### 2026-09-30 · smallest-gear 030, 070 · the open pocket watch; the gear catches · grade A-
- **Did:** both engines.
- **Got:** LTX lifted the gears up out of the watch in 070; H3 seed 11 turned them in place (in the cut, as is 030 on H3).
- **Learned:** a mechanism's motion goes to H3.

### 2026-09-30 · cyber-alchemist 113 · the gauntlet holding the vial · grade B+
- **Did:** both compositors; Qwen seed 11 framed closer than Flux 2 here. H3 seed 11 in the cut.
- **Got:** the gears at the knuckles, the stitching and the wires held as the fingers flexed.
- **Learned:** for macros, look at both compositors' frames.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| parts rise out of the mechanism | LTX accumulates the motion | H3 | smallest-gear 070 LTX |

## Evidence

- `studio/samples/fight/smallest-gear/h3_070_s11.mp4`; `studio/samples/fight/cyber-alchemist/h3_113_s11.mp4`.

## Open questions

- None open.
