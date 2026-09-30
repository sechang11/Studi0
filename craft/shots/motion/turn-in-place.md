# Turning in place (`move-turn-in-place`)

| family | status | last tested | best result |
|---|---|---|---|
| motion | proven | 2026-09-05 | builder pinned turn, same person 0.68 → 0.68 (catalog `turn_in_place`), grade A- |

**Also called:** turn, turns around, turns to face, turns her head, body turn, spin in place
**Not the same as:**
- [`cam-orbit-360`](../camera/orbit-360.md) - the camera circles and the room behind her changes; here she turns and the room stays
- [`move-look-up`](look-up.md) - only the eyes and chin move
- [`move-crouch`](crouch.md) - the body lowers instead of turning

## Recipe (v2, 2026-09-04)

A pin: H3 first-last between the start frame and an end frame of the same figure turned, on the same pristine plate, over 3-4 s. By words alone she never turns. In a close-up, say "glances" or "looks", never "turns".

1. End frame: the turned figure placed on the start figure's ground line, same x, scaled so the head is as wide (the builder's compositor does it).
2. H3 first-last; the pin prompt also states the place's own description (it keeps H3 from inventing things).
3. Below the change floor (about 0.002-0.009 per second of picture change) do not pin: render on LTX with the motion in words.

## Checks before picking

- The feet stay put; nothing new appears in the background (gulls, a smudge, a second person).

## Progression

### 2026-08-15 · PROMPTING · "turns around" from behind · grade D
- **Did:** a turn asked when only the back is visible.
- **Got:** warping.
- **Learned:** start from a view that shows the face.

### 2026-08-30 · §23 · a turn by words; then pinned · grade B
- **Did:** the turn in prose on LTX; then a pin over 8 s and over 3.75 s.
- **Got:** by prose she never turned. Pinned over 8 s (0.0054/s) the model invented a second subject and fire on the water; over 3.75 s (0.0115/s) it was good.
- **Learned:** pin turns, and keep the pin short.

### 2026-09-04 · §29-§36, §43 · the end figure held in place; the place stated · grade A-
- **Did:** the end figure held on the ground line; the place's description added to the pin prompt.
- **Got:** Doran turned from side-on to camera in place; with the place stated, the invented gulls and smudge were gone (one sample). The director judged pinned turns from whole figures "yes".
- **Learned:** "give the prior something true to hold, because it will not hold an absence".

### 2026-09-04 · §47 · "turns toward the sound" in a close-up · grade D
- **Did:** a close-up turn on LTX.
- **Got:** at 1 s he turned; the remaining 4 s show the back of his head.
- **Learned:** in a close-up, "glances", never "turns".

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| she never turns | a turn asked in words | pin it | §23 |
| a second figure or fire invented | a long pin | 3-4 s | §23 |
| the back of the head for most of a close-up | "turns toward" | "glances" | §47 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §23, §29, §34, §36, §43, §47; `studio/shot_catalog.json` (`turn_in_place`).

## Open questions

- A turn in the shot-script pipeline (fight.py has no pin stage; `flf_shots.py` could do it).
