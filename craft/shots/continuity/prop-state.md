# A prop changing state (`cont-prop-state`)

| family | status | last tested | best result |
|---|---|---|---|
| continuity | works-with-caveats | 2026-09-30 | cyber-alchemist 207, 306, grade A- |

**Also called:** helmet on, helmet off, gadget deploys, jetpack unfolds, holding the vial, prop continuity
**Not the same as:**
- [`cont-costume-back`](costume-back.md) - the costume's own back
- [`fx-thruster-flames`](../fx/thruster-flames.md) - the effect the prop makes
- [`cont-wardrobe`](wardrobe.md) - the costume itself

## Recipe (v1, 2026-09-30)

Give the prop its own reference; write its state in every shot's start frame; let the change happen inside one take.

1. The prop drawn alone on grey (`fight.py --cast --only helmet`), redrawn until it can do what the film needs (the first helmet's small screen visor could not show her face; the redraw has a large clear visor).
2. The prop in the references of every shot it appears in.
3. The state change in one take (207: "She lowers the brass helmet over her head and it seals with a hiss").
4. After the change, every later start frame states it ("wearing the brass helmet").

## Checks before picking

- The prop is where the state says (on the head, on the back, in the hand).
- Two similar props are not merged (helmet and jetpack, both brass).

## Progression

### 2026-08-03 · CINEMATOGRAPHY §2.3, §2.7, §6 · props across CHRONO · grade C
- **Did:** a katana named in a character block; a powered-down robot; a vehicle across shots.
- **Got:** the sword duplicated; the robot came back a different android until "slumped, unlit, dark"; the vehicle came back a car, then a Gundam, then a jet.
- **Learned:** describe a prop's state positively; keep one picture of it.

### 2026-09-04 · §31 · a held prop as a compositor layer · grade D
- **Did:** the red umbrella as a prop on the ground, with prose saying he held it.
- **Got:** the umbrella vanished under the push-in and he held a book.
- **Learned:** a prop that must be HELD goes in the character's pack: "hands are identity".

### 2026-09-07 · §57.2, §69-§70 · a crown · grade B
- **Did:** training crops where the contact point is the subject (the brow); the crown as its own LoRA.
- **Got:** the crops put the crown on the brow on every seed; the crown's own LoRA learned a silhouette or went magenta.
- **Learned:** handle with and without as two costume variants.

### 2026-09-30 · cyber-alchemist 207, 306, 310-312 · helmet on, jetpack deployed, helmet under her arm · grade A-
- **Did:** the recipe above.
- **Got:** the helmet goes on in 207 and stays on through the fall; the jetpack deploys in 306 (H3); she holds the helmet under her arm at the end. Qwen start frames for 306 drew the helmet on her back.
- **Learned:** redraw a prop until it can do its job; check the compositor did not merge props.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the prop cannot do its job (a face must show through the visor) | the first draw's design | redraw the prop | cyber-alchemist helmet |
| two props merged | similar materials | Flux 2 start frame; name both | cyber-alchemist 306 |

## Evidence

- `studio/samples/fight/cyber-alchemist/ref_helmet.png` (seed 7 of 4242/7/99), `_helmet_orig.png`.

## Open questions

- None open.
