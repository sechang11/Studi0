# Two people's hands together (`frame-hands-two-people`)

| family | status | last tested | best result |
|---|---|---|---|
| framing | proven | 2026-09-30 | smallest-gear 050, grade A- |

**Also called:** four hands, hand over hand, guiding hand, two people's hands, teaching hands
**Not the same as:**
- [`frame-insert-hands`](insert-hands.md) - one person's hands
- [`frame-two-shot`](two-shot.md) - the two people, faces and all
- [`cont-fingers`](../continuity/fingers.md) - what the fingers do

## Recipe (v1, 2026-09-30)

Flux 2 with "no faces anywhere in the frame, looking straight down" (Qwen gave a two-shot twice); H3 for the guiding move.

1. Start frame: Flux 2 ref3 [person A, person B, place]: "an EXTREME MACRO CLOSE-UP that shows only hands, tools and the watch, no faces anywhere in the frame, looking straight down over the open pocket watch".
2. H3.
3. Prompt: "Her hand trembles slightly; his steady fingers close gently around hers and guide the tweezers down, slowly".

## Checks before picking

- Each hand belongs to the right person (sleeve colour, age of the skin).
- The guiding hand actually moves over the other.

## Progression

### 2026-08-03 · CINEMATOGRAPHY §5 #6 · four hands on an egg (790) · grade D
- **Did:** four hands interacting in an image-to-video shot.
- **Got:** "the hardest thing in i2v".
- **Learned:** rewrite as pressure or glow, or build it close and on H3.

### 2026-09-30 · smallest-gear 050 · the old man guides the girl's tweezers · grade A-
- **Did:** Qwen twice (two-shots), then the Flux 2 redraw above; LTX and H3.
- **Got:** H3 seed 202 is the take where his hand really moves over to guide hers.
- **Learned:** say what must NOT be in the frame (faces), and use Flux 2 for a macro.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a two-shot with faces | Qwen composes the people | Flux 2; "no faces anywhere in the frame" | smallest-gear 050 |

## Evidence

- `studio/samples/fight/smallest-gear/h3_050_s202.mp4`.

## Open questions

- None open.
