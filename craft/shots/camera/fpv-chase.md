# FPV chase behind a moving subject (`cam-fpv-chase`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | proven | 2026-09-30 | cyber-alchemist 301, grade A- |

**Also called:** FPV, drone chase, FPV drone tracking shot, follow cam dive, chase cam
**Not the same as:**
- [`pov-dive`](../pov/dive.md) - through her eyes; an FPV chase sees her from behind
- [`cam-track-alongside`](track-alongside.md) - the camera keeps beside her; an FPV chase stays behind and follows her path
- [`cam-follow-behind`](follow-behind.md) - following on the ground at running speed

## Recipe (v1, 2026-09-30)

H3 image-to-video from a start frame that already shows the dive from behind; Flux 2 composes that frame.

1. Start frame: Flux 2 ref3 (`workflows/75_flux2_ref3.json`) with [place, her back view from her sheet, the prop]. It drew the head-first dive; Qwen drew her upright, standing in the air.
2. H3 (`fight.py --h3`): "she plunges head first down the canyon and the camera dives right behind her at the same speed; neon streaks past".
3. Two seeds; pick the one where the street rushes up.

## Checks before picking

- The camera stays behind her and matches her speed (the street grows).
- No flip into a view from below (LTX seed 11 turned it into looking up at her).

## Progression

### 2026-09-30 · cyber-alchemist 301 · head-first dive, H3 and LTX · grade A-
- **Did:** a Flux 2 start frame of her diving; LTX and H3, two seeds each.
- **Got:** H3 seed 11 follows her down the canyon with motion blur and the street approaching. LTX seed 11 flipped to a view from below her; LTX seed 202 followed her back.
- **Learned:** H3 holds the chase; Flux 2 draws the dive.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the view flips to below her | LTX re-interprets the fall | H3; check the whole take | 301 LTX s11 |
| she stands upright in mid-air | Qwen compositor drew a pose, not a dive | Flux 2 for the start frame | 301 anchors |

## Evidence

- `studio/samples/fight/cyber-alchemist/h3_301_s11.mp4`; anchors board 3.

## Open questions

- A chase with a turn (the canyon bends): not tried.
