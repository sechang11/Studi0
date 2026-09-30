# A character's own reflection (`pov-reflection`)

| family | status | last tested | best result |
|---|---|---|---|
| pov | fails | 2026-09-30 | quantum-courier 210-211, grade D |

**Also called:** reflection shot, mirror shot, seeing herself in the glass, reflection in the window, her reflection
**Not the same as:**
- [`fx-reflective-surface`](../fx/reflective-surface.md) - the environment mirrored in a surface; that works
- [`pov-contact-to-lens`](contact-to-lens.md) - touching the glass rather than seeing oneself in it

## Recipe (v0, 2026-09-30)

None that works. What failed: asking the compositor for "the clear reflection of the full body in the dark glass". Next to try: composite the reflection yourself (her figure, mirrored, dimmed and blended into a glass plate), then animate that start frame.

## Checks before picking

- Is it a reflection? Look for the glass: a frame, a sheen, the room seen through it, her image flipped left-to-right (her LEFT-sleeve circuit must appear on the right).

## Progression

### 2026-09-07 · §82 · glass words in a kiss prompt · grade D
- **Did:** "Where her lips are seen as if kissing a see-through glass window".
- **Got:** a framed pane with her reflection, and on two seeds a second her kissing the first - an unwanted reflection and a double.
- **Learned:** glass words are strong and uncontrolled; there they went to the negative.

### 2026-09-30 · quantum-courier 210-211 · her reflection in a glass wall · grade D
- **Did:** 210's start frame: "a FIRST-PERSON POINT-OF-VIEW SHOT looking up at the massive floor-to-ceiling glass window ... in the dark glass, the clear reflection of the full body of the woman"; 211's: "a CLOSE-UP of the reflection of the face ... in the dark glass window". Qwen-Image-2.1 compositor, LTX.
- **Got:** 210 shows her standing in the corridor; 211 is a plain close-up of her face. Nothing reads as a reflection. It failed at the start frame, before the video engine.
- **Learned:** the compositor draws the person, not their reflection. A reflection has to be built.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| she is drawn present instead of reflected | the compositor ignores "reflection of" | composite the reflection (next attempt) | quantum-courier 210-211 |

## Evidence

- `studio/samples/fight/quantum-courier/anchor_210.png`, `anchor_211.png`, `shot_210_s11.mp4`, `shot_211_s202.mp4`.

## Open questions

- Everything: the composite recipe has not been tried.
