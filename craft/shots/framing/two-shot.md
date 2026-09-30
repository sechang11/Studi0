# Two-shot (`frame-two-shot`)

| family | status | last tested | best result |
|---|---|---|---|
| framing | proven | 2026-09-30 | smallest-gear 020, 090, grade A- |

**Also called:** two-shot, medium two-shot, two characters in frame, side by side, two shot medium
**Not the same as:**
- [`frame-hands-two-people`](hands-two-people.md) - only their hands
- [`frame-over-the-shoulder`](over-the-shoulder.md) - one of the two is a back and a shoulder in the foreground
- [`cont-cast-count`](../continuity/cast-count.md) - how many named people one frame can hold
- [`frame-shot-reverse`](shot-reverse.md) - the two cut against each other

## Recipe (v1, 2026-09-30)

Qwen-Image-2.1 with [person A, person B, place], placing them in words ("sitting side by side"); LTX; one shared action.

## Checks before picking

- Two people, not three; each keeps his or her face.

## Progression

### 2026-08-03 · CINEMATOGRAPHY §1.4, §5 #2 · props and motion between two characters · grade C
- **Did:** two characters in one keyframe, one wearing a pendant.
- **Got:** the pendant migrated to the other character; each extra mover roughly doubled the morph risk.
- **Learned:** one sentence per character, the name repeated, a spatial anchor for each; one mover.

### 2026-09-04 · §31, §35, §46 · two people composed · grade B+
- **Did:** the second character as a relit compositor layer.
- **Got:** both identities held for 6 s; asked to "stand and talk", they walked toward the camera.
- **Learned:** compose both; expect LTX to walk them.

### 2026-09-29 · §0.3, §96.10 · the default compositor · grade n/a
- **Did:** Qwen-Image-2.1 against Flux 2 ref3 on face-scored shots.
- **Got:** Qwen won 19 of 20 (+0.108), three times faster.
- **Learned:** Qwen-Image-2.1 is the default; Flux 2 for framing-critical shots.

### 2026-09-30 · smallest-gear 020, 090 · the old man and the girl at the bench · grade A-
- **Did:** the recipe above, LTX.
- **Got:** both held; the faces were scored by eye (the scorer is blind to puppet faces).
- **Learned:** Qwen places two people well.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| (none recorded in these films) | | | |

## Evidence

- `studio/samples/fight/smallest-gear/shot_020_s11.mp4`, `shot_090_s11.mp4`.

## Open questions

- None open.
