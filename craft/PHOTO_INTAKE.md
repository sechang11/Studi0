# PHOTOGRAPHS TO SEND ME

Hand this to the person whose photographs you are about to use. It is the intake
checklist for the photo-to-character pipeline: what to shoot, how many, what to avoid,
and what each failure looks like when it arrives. It takes ten minutes with a phone and
no equipment, and it is the only part of the pipeline a non-technical person has to do.

Everything numbered here was measured on the synthetic stand-in — a person who does not
exist, built precisely so this pipeline could be calibrated before anyone's real
photographs were involved. The evidence is in `studio/samples/photo2anime/`.

Labels, the same three `PRINTING.md` and `CHARACTER_TO_PRINT.md` use:

- **MEASURED** — measured on this box, on our own output, with the measurement quoted.
- **RULE OF THUMB** — general practice. Not measured here.
- **HARD** — a property of a model or a file format, not a preference.

---

## 0. THE SHORT VERSION

```
HOW MANY   8 photos.  4 if all you want is one printable figurine.
           16 buys reliability, not likeness. Nothing is gained past 8.

VARY       outfit  >  angle  >  distance  >  light      (in that order of importance)
           2+ outfits. front / both 3-4 / profile / one from behind.
           1+ full body. 1+ head-and-shoulders filling the frame.

NEVER      sunglasses, hats, masks, face filters, beauty smoothing, heavy retouching,
           other people in frame, hard shadow across the face, motion blur.

PLUS ONE   for a 3D print: one A-pose frame. Arms out clear of the body, hands in
           loose fists, feet flat, plain wall, flat light, whole body in frame.

SEND       originals. Full resolution, uncropped, unedited. Not screenshots.
```

Eight ordinary photographs taken in ten minutes beat eight careful ones taken in the same
spot wearing the same thing. That is the single most important line in this document and
it is measured, not asserted. See section 2.

---

## 1. HOW MANY

**MEASURED**, five character LoRAs trained with everything else held constant (1000 steps,
rank 16, lr 5e-4, one seed, 832x1216) and judged by looking at 154 renders of a fixed
battery. `studio/samples/photo2anime/count/RESULTS.json`, sheets in `count/contact/`.

| photos | what you get | use it for |
|---|---|---|
| **4** varied | indistinguishable from 8 and 16 on a good close frame — glasses, face, style all intact | one hero image; a figurine source |
| **8** varied | the safe answer. survives eight different prompts and two seeds without dropping the marks | a character you will render again and again |
| **16** | no better likeness. only *less likely to drop a marker* on an awkward prompt | when re-rolls are expensive |
| **>16** | nothing measurable | — |

So: **4 for a print, 8 for a film character.** The knee in the curve is at 4 and the
plateau starts at 8.

Caveat, stated because it changes the advice if your budget changes: the training budget
was fixed at 1000 steps for every arm, so the 4-photo set saw each image 250 times and the
16-photo set 62 times. "4 equals 16" is a statement about a fixed ten-minute training run,
not about photographs in the abstract.

---

## 2. SPREAD BEATS COUNT

**MEASURED**, and it is the finding worth reading twice.

Two training sets, both of exactly 8 photographs, same steps, same everything:

- **VARIED** — three outfits, five angles, three distances, three lighting conditions.
  `count/contact/strength_n8.jpg`
- **NARROW** — eight near-identical frames: one outfit, one spot, one light, all
  head-and-shoulders. This set had **more close-up face pixels than any other arm.**
  `count/contact/strength_n8narrow.jpg`

The varied set puts her round gold glasses and her adult, ordinary, thirty-something face
on screen with the drawing style intact. The narrow set produced a generic young anime girl
with **no glasses at all** at three different strengths, and only produced the glasses at
the fourth — by which point the style had collapsed back into photography and the face
still was not hers.

Eight photographs of the same moment are one photograph. The model cannot tell which parts
of the picture are *the person* and which parts are *that afternoon* unless you show it the
person on more than one afternoon.

---

## 3. WHAT TO VARY, IN ORDER

**MEASURED** — this ordering is the ordering of how much each one cost when it was missing.

**1. OUTFIT — at least two, ideally three.** A set wearing one thing teaches the model that
the thing *is* the person, and then you cannot dress the character. Two outfits is the
tested fix.

**2. ANGLE — five of them.** Straight on. Three-quarter left. Three-quarter right. Full
profile. One from behind or over the shoulder. The back view is not wasted: it is the only
photograph that says what the back of the head looks like, and it is what a turnaround and
a 3D mesh need.

**3. DISTANCE — at least one of each.** One full body, head to feet. One head-and-shoulders
that *fills the frame*. **A face is a pixel problem.** Fine markers — glasses, a mole, an
earring — were only ever reliably reproduced from close frames. On medium and full-body
training frames no arm in the experiment produced the glasses at all.

**4. LIGHT — three kinds.** Daylight from a window. Flat indoor room light. Outdoors on an
overcast day. Do not chase good light; chase *different* light. If every photo is lit the
same way, the model learns the lighting as part of the face.

---

## 4. THE SHOT LIST — TEN MINUTES, A PHONE, A FRIEND

Ask someone to hold the phone. Selfies at arm's length distort the nose and jaw and every
one of them is the same distance and the same angle, which breaks section 3 twice.

```
OUTFIT A  (whatever you are wearing)
  1  head and shoulders, straight on, filling the frame, by a window
  2  three-quarter left, waist up
  3  three-quarter right, waist up
  4  full body, head to feet, plain wall behind you

OUTFIT B  (change your top; a jacket on or off counts)
  5  head and shoulders, straight on, indoor room light
  6  full profile, side on, waist up
  7  from behind or over the shoulder, showing the back of the head
  8  full body, outdoors, overcast, or in open shade

THAT IS THE EIGHT. If you only shoot four, shoot 1, 3, 4 and 5 —
one close, one angled, one full body, one in a different outfit and light.
```

Neutral expression on most of them. One or two smiling is fine and useful; eight smiling is
a set where the model learns the smile as the face.

---

## 5. THE EXTRA FRAME, IF YOU WANT A 3D PRINT

**MEASURED**, on the mesh: `studio/samples/photo2anime/mesh/sheets/`.

One more photograph, and it is worth more than the other eight put together, because the
figurine is built from a single view.

```
POSE       standing, facing the camera square on
ARMS       out and away from the body, roughly 30-45 degrees, a clear gap of
           background visible between each arm and the torso
HANDS      loose closed fists at the end of straight arms.
           NOT open fingers. NOT hands on hips. NOT hands near the face.
FEET       flat, slightly apart, both fully in frame
FRAME      whole body, head to feet, a little air above and below
BACKGROUND one plain flat wall, a colour that is not your skin and not your clothes
LIGHT      flat and even. NO hard shadow falling on you or on the wall behind you
CAMERA     phone at chest height, held level, stepped back — not tilted up or down
SIZE       the original file. 1600 px or more on the long edge.
```

Why each of those, in one line each:

- **arms clear of the torso** — arms touching the body get fused into it as one lump and
  cannot be separated afterwards. **HARD.**
- **closed fists** — a bad hand in the photograph is a bad hand in the mesh. Closed fists
  came through correct at every angle in both arms of the experiment; that was a property
  of the source pose, not something the pipeline fixed.
- **no cast shadow** — the matting step reads a shadow on the wall as part of you.
- **flat light** — but understand what it costs, see below.
- **hair down as one mass, or tied back.** Either is fine. What you must not do is have it
  half-up in separated strands and locks.

---

## 6. WHAT WILL NOT SURVIVE, AND YOU SHOULD KNOW BEFORE YOU SHOOT

Honesty section. All **MEASURED**.

- **A small mole, a freckle, a scar: no.** In a 72-cell reference sweep the stand-in's
  cheek mole never appeared once, at any strength, in any style.
- **The face on a 150 mm print is not a portrait.** The best of the two meshes is *more
  recognisably her*; it is not *recognisable as her*. Facial relief in a photograph is
  carried by shading — about a millimetre of real depth — and the mesher smooths it away
  as noise. A photograph meshed directly produced a face with almost no nose projection at
  all and the glasses as one thick slab across the middle of it.
- **"Just one photo and a reference-image dial" does not work.** Feeding a single
  photograph in as a style reference transfers the *marks* — dark hair, round glasses, the
  mustard colour — and never the person. It also drags the photo's own wall and lighting
  into the picture and overwrites the clothes you asked for. It is a costume, not a
  person. That is why this document asks for eight photographs and not one.
- **A trained-from-photos character fights a non-photographic style at close range.** On a
  tight watercolour portrait every trained arm reverted to a near-photographic face, on
  both seeds, while the untrained control stayed watercolour. At full-body distance the
  style survived. If you want a painterly close-up of this character, expect to fight for
  it.

---

## 7. THE FAILURE GALLERY — WHAT EACH MISTAKE LOOKS LIKE WHEN IT ARRIVES

| you sent | what comes back | evidence |
|---|---|---|
| 8 photos, same day, same outfit, same spot | a generic young anime girl. glasses missing entirely at usable strengths; the one strength that shows them has lost the style and still is not her | `count/contact/strength_n8narrow.jpg` |
| one outfit only | the outfit becomes part of the identity; asking for other clothes gets you the same jacket back | Terra, prior wave |
| blurry, dark, motion-blurred, half-cropped photos | the *marks* survive — glasses, hair, colour — and the *person* does not. the face comes back young and idealised instead of the age and build you actually are | `count/contact/strength_n8bad.jpg` |
| no close-up in the set | no glasses, no earrings, no small features, at any strength | `count/contact/` medium and full-body cells |
| all full-body, no full-frame face | a plausible stranger with your hair and your coat | as above |
| a group photo, or someone else in frame | the model learns a blend, or the wrong person | RULE OF THUMB |
| sunglasses, a hat, a mask, a face filter | whatever is covering the face is learned as the face | RULE OF THUMB |
| a beauty filter or skin smoothing | the idealised face wins. this is the same failure as bad photographs, arriving by a nicer route | RULE OF THUMB |
| screenshots, or images sent through a chat app that recompresses them | soft, blocky training data; the model learns the compression | HARD |
| for the print: open fingers, or hands at the hips | fused or malformed hands in the mesh, unrepairable | `mesh/sheets/FISTS.jpg` (the good case) |
| for the print: arms against the body | arms and torso merge into one mass | HARD |

---

## 8. SENDING THEM

- **Originals.** Full resolution, straight off the camera roll. Not screenshots, not
  re-saved, not exported at "medium".
- **Uncropped and unedited.** No filters, no retouching, no colour grading. If the phone
  applies a portrait-mode background blur, send a non-portrait-mode version too.
- **1600 px or more on the long edge** for every frame. Modern phones are far past that;
  the only way to fall below it is to send something already resized.
- **Name them by what they are** if you can — `close_front_window`, `full_body_outdoor` —
  it makes the captions right, and the captions are what keeps your wardrobe separable
  from your face.
- **Keep the originals.** If the first pass is wrong, the fix is usually two more
  photographs of a kind that is missing, not a retrain on the same eight.

---

## 9. TEN-MINUTE CHECKLIST

```
[ ] 8 photos (or 4 minimum)
[ ] at least 2 different outfits
[ ] front, 3-4 left, 3-4 right, profile, one from behind
[ ] at least 1 full body, head to feet
[ ] at least 1 head-and-shoulders filling the frame
[ ] at least 2 different lighting conditions
[ ] nothing covering the face in any of them
[ ] no other people in frame
[ ] nothing filtered, retouched or screenshot
[ ] (for a print) 1 A-pose: arms out, fists closed, plain wall, flat light, full body
```

---

## WHERE THE NUMBERS CAME FROM

- Photo count, spread, and the failure gallery — `studio/samples/photo2anime/count/`,
  `RESULTS.json` and `contact/`. Tool: `studio/_tools/photo_count_probe.py`.
- The reference-image dial, and why one photo is not enough —
  `studio/samples/photo2anime/sweep/`, `VERDICT.json` and `sheets/`. Tool:
  `studio/_tools/photo_to_anime.py`.
- What survives to a mesh, and the A-pose requirements —
  `studio/samples/photo2anime/mesh/`, `VERDICT.json` and `sheets/`. Tool:
  `studio/_tools/photo2anime_mesh.py`. The finished figure is
  `studio/samples/photo2anime/print/STANDIN_150mm.stl` — 150 mm, watertight, one body,
  93.82 cm3, re-verified from disk with trimesh.
- The subject of every one of those experiments is a synthetic stand-in built by
  `studio/_tools/standin_person.py`. **No photograph of any real person was fetched, used
  or referenced anywhere in this work, and no public figure appears in any prompt.** That
  was the whole point of building her: the pipeline is calibrated before your photographs
  are involved.
- The recipe on the far side of this checklist is `craft/CHARACTER_TO_PRINT.md`; the print
  spec is `craft/PRINTING.md`.
