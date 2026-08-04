# Holding a character on the qwen engine

VIRO has a trained character LoRA and it is useless here. It was trained on animagine-xl-4.0,
and a LoRA is a delta on specific weights - this project already proved from the ComfyUI log
that every one of its SDXL keys is rejected wholesale the moment a QwenImage model is loaded.
So on the qwen engine there is no trained identity mechanism at all.

This document is what is left, measured. Everything below was rendered on 2026-08-03 by
`studio/_tools/qwen_character.py` and then looked at. 45 images, in
`studio/samples/qwen_character/`, contact sheets in `_sheets/`. Start with `ANSWER.jpg`.

> The prior claim was "a reference sheet, plus the multiple-angles LoRA, plus Relight."
> That claim is **substantially correct**, and one part of it is much more important than
> anyone had said: the reference sheet is not just an identity aid, it is the only thing
> that stops a style LoRA from replacing the character with someone else.

---

## Method

Four places the sheet has never seen (night street, kitchen, beach, library). Framing is
written into every prompt (`waist-up photograph`) and the garment is stated in every prompt,
so that when a face changes it is the FACE that changed - not the framing, and not the outfit
doing the recognising for you. Seed is fixed per place, so the same place in different arms
samples identical noise and the mechanism under test is the only difference.

Identity is judged on the **face-crop** sheets, never the full frame. At full frame a matching
teal jersey reads as a matching character, and it is not one.

Four arms, one variable per rung:

| arm | reference | phrasing |
|-----|-----------|----------|
| A  | none | description only |
| B1 | `sheet_viro.png`, the sheet films use today (an illustration) | literal "image 1" |
| B2 | a fresh photographic sheet | literal "image 1" |
| B3 | the same photographic sheet | what `short.py` actually emits |

`A -> B2` is the value of a reference. `B1 -> B2` is the cost of the sheet being a different
style from the target. `B2 -> B3` is the cost of the prompt phrasing.

---

## A. Prose alone does not hold a face

`identity_ladder_faces.jpg`, top row. Four cells, one description, one seed per place.

They are **four different men**. Night-street is round-faced and heavily stubbled;
kitchen is long, thin and sparse-bearded; beach has a wide jaw and a full dark moustache;
library is narrow with a longer nose. What they share is the description - long dark curly
hair, an ear stud, brown eyes - and nothing else. The jersey drifts too: a Nike swoosh in two
cells, an invented club crest in another.

This is casting, not identity. Every cell satisfies the brief and no two are the same person.
Seven of the thirteen films in this repo render qwen keyframes with no `sheets` block at all,
which means this row is what the majority of this project's qwen output actually looks like.

## B. A reference sheet does hold a face - and imports its style wholesale

**B2 (photographic sheet) is the working configuration.** Four places, one man. Same brow
shape, same straight nose, same stubble pattern, same face width, ear stud present. Against
the source sheet it is recognisably the same person.

Honest calibration: it is **the same actor photographed on different days**, not the same
photograph. The beach cell has slightly fuller cheeks, the kitchen cell a slightly longer
face. That is a real and useful lock, and it is not the pixel-level lock a trained LoRA gives
on the anime side. The resolver already tells users this is weaker than IPAdapter, and that
warning should stay.

**B1 is the finding nobody had rendered.** Every cell of B1 came out as a **comic-book
illustration** - flat cel shading, ink outlines - despite the prompt asking for a
`waist-up photograph`. The reference sheet did not merely suggest a style, it overrode an
explicit instruction in the prompt.

The cause is documented in this repo and had never been connected to its consequence:
`scripts/make_sheets.py` renders every sheet through `13_qwen_t2i_styled.json`, and that node
7 used to carry the storybook LoRA at 0.8. So `sheet_viro.png` is itself a drawing, and every
film referencing it has been silently pulling its keyframes toward that drawing's style.

> **A qwen reference sheet carries STYLE as strongly as it carries IDENTITY.** Whatever the
> sheet is drawn in, the film is drawn in. Changing a film's style without re-rendering its
> sheets is incoherent, and re-rendering the sheets changes the faces.

Worth noting against B1's own row: it is the **most internally consistent row on the whole
grid**. The illustrated sheet locks the face harder than the photographic one does, because a
drawn face has fewer degrees of freedom than a photographed one. If a film is stylised
anyway, an illustrated sheet is an asset, not a bug. It only misfires when the target is
photographic.

## B3. The "image 1" phrasing rule did not reproduce

`workflows/23_qwen_edit_2511_fusion.json` `_notes` say references must be called "image 1"
literally, and that vaguer wording "degrades the association noticeably". `scripts/short.py`
does not follow this - it emits the character prose with "from the reference image" hand-written
into the film's character string.

**I could not see the difference.** B3 is as consistent as B2, arguably marginally more so.

I am not calling the note wrong. There is a confound: B3 restates the full character
description as well as pointing at the reference, so it has two identity signals where B2 has
one. The honest statement is that at four samples per arm, on this character, **short.py's
phrasing is not visibly costing anything**, and this is not the place to spend effort.

## C. The multiple-angles LoRA works, and works better on photographs

`C_angles.jpg`, `C_angles_faces.jpg`. Six views from the single photographic sheet: front,
three-quarter, side profile, back, looking up, low angle. All six are clearly the same man -
same brows, same nose, same ear stud where the ear is visible - and all six hold the teal
jersey with orange trim and the number 7.

That last part matters. The existing VIRO turnaround in `studio/samples/cast/VIRO/` was run
from the **anime** sheet, and its costume drifted badly: `02_side_left.png` came back in a
dark green collared shirt instead of the teal jersey. On a photographic source the garment
held perfectly across all six views. The LoRA is a Qwen-Image-Edit 2511 LoRA and it is
happiest on the kind of image that model was trained on.

This is also the route to a qwen-native character LoRA: 16-40 consistent views is exactly the
training set that is otherwise impossible to produce by hand.

## D. Relight works and identity survives it

`D_relight_faces.jpg`. One fixed library keyframe, three lighting setups, on Qwen-Image-Edit
**2509** (not 2511 - Relight is a 2509 LoRA and this project has proved LoRAs are base-locked)
with the 2509 Lightning accelerator at 4 steps.

Golden hour gives warm raking light from the left with amber highlights. Hard top gives a
bright overhead key with a rim on the hair. Blue rim gives a cold blue edge on hair and
shoulders against a dark room. In all three the pose, the background bookshelves, the lamp,
the jersey and the number 7 are preserved, and the face is unmistakably the same man.

This is the "give them a certain look" half of the question, and it is the half that behaves.
Lighting is a physical fact about an image rather than an adjective, so it survives being
moved into a deterministic post-stage - exactly what this project's governing rule predicts.

One artefact, and it is the governing rule again: the hard-top cell **drew the lamp**. Asked
for overhead light, the model put a visible light fixture at the top of the frame. The model
renders nouns, not adjectives, and "overhead light" contains a noun.

## E/F/G. The result that actually answers the question

This is the part worth reading twice.

**F - style LoRA, no reference.** `illustration-1.0-qwen-image` on its own base, the 2512 t2i
model, applied to VIRO's prose. Three fresh seeds at strength 1.0 and three at 1.5, six cells.

**All six came back as a young woman.** The prompt says "a young man". The style landed
correctly - it is a genuine illustration - but the person was replaced. This is not a seed
fluke; six of six across two strengths, plus the original seed 5150 at both strengths, is
eight of eight.

The reason is legible in the file's own metadata: `illustration-1.0-qwen-image.safetensors`
is internally named **`qwen_anime_style_v1`** and was trained 59,000 steps on that. It drags
the subject toward its training distribution, and that distribution is young anime women. A
style LoRA is not a neutral filter - it is a pull on everything, including who the person is.

**G - the same style LoRA, same seeds, same strengths, plus the reference sheet.** On the
2511 edit model with the photographic sheet as reference.

**All six came back as the same man**, recognisably VIRO, with the illustration style applied
at 1.5. Same brows, same nose, same stubble, same hair.

> **F and G are the answer.** A style LoRA alone re-invents the person. A style LoRA over a
> reference sheet restyles them. The reference sheet is not a nice-to-have on the qwen
> engine - it is the thing that makes a style LoRA safe to use on a character at all.

Two practical numbers from E2/G:

- **On the edit model the style LoRA does almost nothing at strength 1.0.** At 1.0 the output
  is still a photograph. 1.5 is where the style lands. On its own t2i base, 1.0 is already
  fully committed. Same file, same strength, different base, very different amount of effect -
  budget for it.
- At 1.5 over a photographic sheet, the **scene** stylises harder than the **face** does:
  line-art bookshelves around a still fairly realistic head. If a fully drawn face is wanted,
  an illustrated reference sheet (the B1 configuration) gets there and a style LoRA over a
  photographic sheet does not.

---

## Ranking, strongest to weakest, with costs

1. **Reference sheet + multiple-angles views, on Qwen-Image-Edit 2511.** The strongest thing
   available today. Costs one sheet render plus one turnaround (~1 min for 6 views), then
   ~7.5s per keyframe. The machinery is complete and the views exist; what is still not wired
   is `short.py` spending `image1/image2/image3` on three views of ONE person - today it
   spends them on three DIFFERENT characters. No new workflow node is needed for that.

2. **Reference sheet, single image.** What films do now. ~7.5s per keyframe, one sheet render
   up front. Holds "the same actor", not "the same photograph". **The sheet must be rendered
   in the film's target style**, because the sheet's style becomes the film's style.

3. **Relight, as a post-stage on an already-locked keyframe.** Does not hold identity, it
   preserves one that is already there - so it composes with 1 or 2 rather than competing.
   ~13s per variant on the 2509 checkpoint. The only reliable way to change the lighting half
   of "look" without re-rolling the person.

4. **Style LoRA, but only over a reference.** ~7.5s, strength 1.5 on the edit model. Restyles
   the scene and holds the character. Never use it without a reference.

5. **Prose alone.** Free, and it does not hold a face. It casts a type. Acceptable for
   background figures and for one-shot images; not acceptable for a character who recurs.

6. **A style LoRA with no reference, on a named character.** Actively harmful. It replaced a
   man with a woman in eight of eight renders. This is worse than nothing, because it looks
   like it is working - the style is correct and the output is attractive.

**Not measured, still the best available option in principle:** a qwen-native trained
character LoRA. Nothing on this box has ever trained one. `TrainLoraNode` has no architecture
restriction and Qwen-Image is built from ComfyUI ops, so adapters would attach; the open
question is whether a 20 GB fp8 DiT trains inside 32 GB with `training_dtype="none"` +
`bypass_mode`. Stage C now produces the training set that would feed it.

---

## Repo notes this run settled

- **The always-on style LoRA bug is fixed.** Node 7 of `13_qwen_t2i_styled.json` ships at
  strength 0.0, and `short.py:318 style_lora_slot()` explicitly zeroes it when a film sets no
  `style_lora`. Rendered confirmation: the photographic sheet came out photographic. Several
  docs still describe this as live; they are stale.
- **Sheets rendered before that fix are still contaminated.** `sheet_viro.png` is an
  illustration and arm B1 shows exactly what that does to a film. Any sheet older than the fix
  should be re-rendered.
- **`epic.py:_find_font()` returns "" on this box.** It probes only DejaVu paths and Fedora
  ships Carlito/Adwaita. Anything drawing text through that constant is silently unlabelled.
  Not touched - flagging only.
- **The negative-prompt bug still stands** (`short.py` passes no negative on either keyframe
  workflow, so a style's `negative_add` is assembled and discarded). Left alone deliberately.

## What this does not establish

- **One character, one engine pairing.** Everything here is VIRO on Qwen-Image-Edit 2511 /
  2512 / 2509. A face with fewer distinctive markers than long curly hair plus an ear stud may
  drift more.
- **Four places per arm.** Enough to see A fail unmistakably; not enough to put a number on
  how often B2 drifts.
- **No video.** Every image is a still keyframe. Whether a reference-locked keyframe survives
  being animated through LTX is untested here.
- **The B2/B3 phrasing comparison is confounded**, as described above. It shows short.py is not
  obviously losing anything; it does not disprove workflow 23's note.
- **Relight's 2509 base-lock is still inferred from the filename**, not read from metadata. It
  produced correct results on the 2509 checkpoint, which is consistent with the inference but
  does not prove it; I did not try it on 2511.
- Only `illustration-1.0-qwen-image` was tested as a style LoRA. Whether the other two qwen
  style LoRAs also flip the subject is unknown.

## Reproducing

    python3 studio/_tools/qwen_character.py                 # all stages, ~6 min
    python3 studio/_tools/qwen_character.py --stage B2 C
    python3 studio/_tools/qwen_character.py --sheets        # rebuild contact sheets only

Stage order is grouped by checkpoint (2512 t2i, then 2511 edit, then 2509 edit) rather than
alphabetically. Each is a ~20 GB fp8 model on a 32 GB card, so an order that interleaves them
pays a full model load per image instead of per group.
