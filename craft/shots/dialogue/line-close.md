# A line in close-up (`dia-line-close`)

| family | status | last tested | best result |
|---|---|---|---|
| dialogue | works-with-caveats | 2026-09-24 | LTX-2.3 talking head, words 100% (§97.1), grade B+ |

**Also called:** close-up line, talking head, a line in close-up
**Not the same as:**
- [`dia-line-on-camera`](line-on-camera.md) - a wider framing
- [`dia-reaction`](reaction.md) - the close-up that listens

## Recipe (v1, 2026-09-24)

A composed close-up (the face from the portrait view), the line in quotes, "listens, then speaks" - never "turns toward". For a held close-up that needs its own sound, H3 (LTX close-ups come back near silent).

## Checks before picking

- The face stays toward the camera; the words heard.

## Progression

### 2026-09-04 · §47 · "turns his head toward the sound", then a line · grade D
- **Did:** a close-up line after a turn.
- **Got:** the voice pack said the line to his collar.
- **Learned:** no "turns" in a close-up.

### 2026-09-20 · §96.5 · H3 against LTX on a held close-up · grade n/a
- **Did:** the same anchor on both.
- **Got:** H3 keeps frame 0 (SSIM 0.962 against 0.289) and returns -27 dB where LTX returns -56 dB.
- **Learned:** a held close-up that must sound goes to H3.

### 2026-09-24 · §97.1 · LTX-2.3 talking head with an ID-LoRA · grade B+
- **Did:** one start frame, one line, three arms.
- **Got:** words 100% in every arm; the ID-LoRA with reference audio carried the voice (0.816 against 0.58); the face held 0.64-0.66 in all arms.
- **Learned:** "The LoRA does not hold the face; the start frame does."

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the line spoken away from the camera | "turns toward" | "listens, then speaks" | §47 |
| near-silent close-up | LTX close-ups | H3 | §96.5 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §47, §96.5, §97.1; `studio/shot_catalog.json` (`line_close`).

## Open questions

- None open.
