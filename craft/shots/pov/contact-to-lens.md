# Touching or kissing the lens (`pov-contact-to-lens`)

| family | status | last tested | best result |
|---|---|---|---|
| pov | works-with-caveats | 2026-09-07 | constructed with `press_lips.py` (§83), grade B |

**Also called:** kiss the lens, hand on the lens, pressed against the glass, face against the camera, POV kiss
**Not the same as:**
- [`pov-reflection`](reflection.md) - seeing oneself in glass

## Recipe (v1, 2026-09-07)

Describe only the contact, never the glass (glass words bring panes and a second person). The model's "kiss" is a pucker; construct the pressed lips in post.

## Checks before picking

- One person; no pane; the contact reads.

## Progression

### 2026-09-07 · §82, §83 · a kiss against the lens · grade B
- **Did:** "as if kissing a see-through glass window"; then the contact alone; then three passes at the kiss.
- **Got:** the glass words gave a framed pane with her reflection and, on two seeds, a second her. The framing came right from the contact alone, but the kiss stayed a pucker. `press_lips.py` spreads the lips (about 4:3), blanches and softens them.
- **Learned:** when a model's prior beats three prompts, stop asking and construct it.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a pane and a second her | glass words | describe only the contact | §82 |
| a pucker, not a press | the model's prior | construct it | §83 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §82-§83.

## Open questions

- None open.
