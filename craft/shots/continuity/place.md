# The place stays the place (`cont-place`)

| family | status | last tested | best result |
|---|---|---|---|
| continuity | works-with-caveats | 2026-09-30 | all five films, grade A- |

**Also called:** set continuity, room consistency, location consistency, same room, geography
**Not the same as:**
- [`cont-move-across-cuts`](move-across-cuts.md) - one move split over generations; here the set across different shots
- [`frame-establishing-empty`](../framing/establishing-empty.md) - the shot that shows the place first
- [`pipe-3d-set`](../pipeline/3d-set.md) - the place held by geometry instead of a picture, so what the plate never showed exists too
- [`cont-screen-direction`](screen-direction.md) - who stands on which side of the screen

## Recipe (v2, 2026-09-30)

One plate per place, drawn empty, in the references of every shot in it; a second angle of the same place is turned from the plate (angles LoRA), never drawn again from words. A scene that looks all round its place is built as a 3D set.

1. The plate: `fight.py --cast` draws the film's place empty (1280x720); a second place is a cast entry `"place": true` (`studio/_tools/sheet_refs.py`).
2. Another angle of the same place: `"place_view": [place, "angle_aerial"]` etc. (angles LoRA) - the same room turned.
3. Every shot lists its place; the Qwen compositor puts places first (the canvas follows image 1).
4. A move that goes where the plate never showed (behind the camera) invents the rest: name what should be there.
5. When the scene's shots look where the plate never did (a reverse, an orbit, a crane), build the place as a set instead: [`pipe-3d-set`](../pipeline/3d-set.md) (v2: the plaza test).

## Checks before picking

- The layout of the room agrees between shots (where the bench is, where the window is).

## Progression

### 2026-08-03 · CINEMATOGRAPHY §6 · a place by description · grade C
- **Did:** the castle described in each keyframe.
- **Got:** it drifted; the keep came back as Hogwarts.
- **Learned:** one plate, handed in.

### 2026-08-30 · §21 · the pristine plate · grade A
- **Did:** the builder's compositor pasting the figure onto the untouched plate.
- **Got:** plate fidelity 0.000-0.007, against 0.187 for a qwen full edit.
- **Learned:** the pristine plate is never touched by a model.

### 2026-09-04 · §29, §35, §38 · words that leave the anchor · grade C
- **Did:** "harbour" words (boats, moorings, quay) over a plate that is a stone bridge.
- **Got:** by the 4th second LTX had built a marina. The anchor check and a scene-drift check followed (drift limit 65%).
- **Learned:** "words that name things the anchor lacks are instructions to leave the anchor".

### 2026-09-06 · §60, §61 · a live plate drifts; a pin holds the room · grade B+
- **Did:** a character over a live plate; a first+last pin; end-pin variants.
- **Got:** live-plate drift 17.6 → 56.1 over 140 frames; the pin held the staircase, arches and torches; an end pin composited differed from the room by 4.6, a qwen "closer" by 62.9.
- **Learned:** an end frame must differ in exactly the thing that moves.

### 2026-09-24 · §98.1 · the plate as a reference · grade A
- **Did:** the place plate given to Flux 2 ref3.
- **Got:** border band 13-22 against the plate, 73 against another place.
- **Learned:** "The plate handed in as a reference returns THE room, not a room."

### 2026-09-30 · all five challenge films · plates and made references · grade A-
- **Did:** the recipe above.
- **Got:** places hold across shots. The orbit, which saw behind the master's camera, invented shelves and barrels (after naming them) instead of the master's room.
- **Learned:** name what the unseen part of the place contains.

### 2026-09-30 · SHEETS · turning a place · grade A-
- **Did:** another angle of a place asked in plain English, then in the angles LoRA's own words.
- **Got:** plain English left the place unturned; the LoRA's words turned it (about 6 s a view).
- **Learned:** `<sks>` words, not prose.

### 2026-09-30 · plaza test · eight shots in one 3D set against one plate and words · grade B+
- **Did:** the same eight shots of one square made two ways: every camera in one Blender set (start frames dressed from the set's renders, takes drawn on its depth), and this recipe (one plate, words, the plate turned by the angles LoRA for the reverse and the west side).
- **Got:** the set's map of the square fit the set's start frames at 0.44 against 0.19 chance, and today's way's at 0.36 against 0.30; colour spread from shot to shot 14.8 against 23.2. The set's film kept one tower, arch, cafe and fountain in all eight shots; today's way put a domed tower in 102, a different arch in 103 and the cafe on a white house in 106, and its turned plate invented the whole south side. Recipe v2: step 5.
- **Learned:** a picture holds the place only where it looked; a set holds it everywhere, including behind the camera.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a portrait-shaped start frame cropped to 16:9 | a figure reference first in the compositor's order | places first (fight.py patched) | quantum-courier |
| the room re-invented per key | each angles-LoRA key imagines the unseen room | previz for moves; name the unseen props | cyber-alchemist orbit keys |
| a reverse or a turned view shows a different place | the plate never saw that side | build the place as a set ([`pipe-3d-set`](../pipeline/3d-set.md)) | plaza 103, 106 (today's way) |

## Evidence

- `studio/_tools/fight.py` (`_qwen_anchor`: places first), `studio/_tools/sheet_refs.py`.

## Open questions

- A 360° place (a panorama plate) for orbits.
