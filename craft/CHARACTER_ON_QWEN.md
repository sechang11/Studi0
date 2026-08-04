# Holding a character on the qwen engine

VIRO has a trained character LoRA and it is useless here. It was trained on animagine-xl-4.0,
and a LoRA is a delta on specific weights - this project already proved from the ComfyUI log
that every one of its SDXL keys is rejected wholesale the moment a QwenImage model is loaded.
So on the qwen engine there is no trained identity mechanism at all.

This document is what is left, measured. Two runs, both rendered and then looked at:

| run | subject | images | where |
|---|---|---|---|
| 2026-08-03 | VIRO only | 45 | `studio/samples/qwen_character/` |
| 2026-08-04 | HALE, PLAIN, + LoRA probes | 90 | `studio/samples/qwen_character/{hale,plain,_probe}/` |

Start with `_sheets/X_*.jpg` - the cross-subject grids, one row per person, same mechanism
in every row. Then `<subject>/_sheets/ANSWER.jpg`.

> **The 2026-08-03 conclusion was "a reference sheet, plus the multiple-angles LoRA, plus
> Relight." That still stands.** The second run added a second and third subject and found
> that the *mechanisms* generalise but two of the *explanations* were wrong. Corrections are
> in their own section at the bottom rather than quietly edited into the text.

---

## Method

Three subjects, chosen so marker count is the variable:

| id | who | markers | why |
|---|---|---|---|
| VIRO | young man | **high** - long curly ponytail, gold ear stud, numbered teal jersey | the original |
| HALE | woman, mid-40s | **high, different kind** - round tortoiseshell glasses, grey crop, white streak, jade stud | is the lock about VIRO's hair, or about references? |
| PLAIN | man, early 40s | **deliberately none** - short brown hair, brown eyes, clean-shaven, grey sweatshirt | the direct test of the 08-03 caveat |

`PLAIN` is a control and must never become a cast member. The moment somebody "improves" it
by adding a scar the experiment is gone.

Four places the sheets have never seen (night street, kitchen, beach, library). Framing is
written into every prompt (`waist-up photograph`) and the garment is stated in every prompt,
so that when a face changes it is the FACE that changed - not the framing, and not the outfit
doing the recognising for you. Seed is fixed per place **and identical across subjects**, so
a HALE cell and a PLAIN cell of the same place differ only in the person.

Identity is judged on the **face-crop** sheets, never the full frame. At full frame a matching
teal jersey reads as a matching character, and it is not one.

Four arms, one variable per rung:

| arm | reference | phrasing |
|-----|-----------|----------|
| A  | none | description only |
| B1 | `sheet_viro.png`, the sheet films use today (an illustration) | literal "image 1" |
| B2 | a fresh photographic sheet | literal "image 1" + "keep their face exactly" |
| B3 | the same photographic sheet | what `short.py` actually emits |

---

## Ranking, strongest to weakest, with costs

1. **Reference sheet + multiple-angles views, on Qwen-Image-Edit 2511.** The strongest thing
   available. Costs one sheet render plus one turnaround (~1 min for 6 views), then ~7.5s per
   keyframe. Verified on all three subjects. This is also the only mechanism that solves the
   pose problem in item 2.

2. **Reference sheet, single image.** What films do now. ~7.5s/keyframe. Holds "the same
   actor", not "the same photograph". **Two costs, both real:** the sheet's style becomes the
   film's style, and the sheet's *pose* becomes the film's pose (see B, below).

3. **Relight, as a post-stage on an already-locked keyframe.** Does not hold identity, it
   preserves one that is already there - so it composes with 1 and 2 rather than competing.
   ~13s per variant on the 2509 checkpoint. Verified on all three subjects.

4. **Style LoRA, but only over a reference.** ~7.5s, strength 1.5 on the edit model.
   Restyles the scene and holds the character. Never use it without a reference.

5. **Prose alone.** Free, and it does not hold a face. It casts a *type*. How badly it drifts
   depends on the description in a counterintuitive way - see A.

6. **A style LoRA with no reference, on a named character.** Actively harmful, and confirmed
   harmful on three subjects now. It looks like it is working, which is what makes it bad.

---

## A. Prose alone casts a type, and marker count does not help the way you would guess

`X_A_control.jpg`, and each subject's `identity_ladder_faces.jpg` top row.

All three subjects drift. None of the three rows is one person. But the drift is **not**
worst for the low-marker subject, which is the opposite of what the 08-03 doc predicted:

- **HALE** (high markers): four women of the same casting type. The glasses, grey crop and
  jade stud are present in all four - and the *face* underneath still changes. Beach is
  visibly older and heavier; kitchen is longer and thinner.
- **VIRO** (high markers): four young men with long curly hair and stubble. Same type,
  genuinely different faces - beach has a wide jaw and moustache, library is narrow.
- **PLAIN** (no markers): **the most self-consistent of the three rows.** Night-street,
  kitchen and library are close to the same man; only beach clearly departs.

The likely reason, stated as a hypothesis and not a measurement: a description that specifies
distinctive *accessories* pins the accessories and leaves the face free, while a description
so generic that it names nothing lands on the model's modal forty-year-old man, and the mode
is stable across seeds. Distinctiveness in the prompt buys you a recognisable *silhouette*,
not a recognisable *face*.

**This is four samples per subject and one judge (me, by eye).** It is enough to retire the
old caveat's specific prediction; it is not enough to assert the reverse as a rule.

## B. A reference sheet holds a face on every subject - and imports style AND pose

`X_B2_photo_sheet.jpg`. **B2 is the working configuration and it generalises.** HALE across
kitchen/beach/library is one woman: same face width, same brow, same glasses, jade stud on the
correct ear. PLAIN across the same three is one man. Against their source sheets both are
recognisably the same person.

**The 08-03 caveat is answered: a zero-marker face locks as well as a high-marker one.** The
reference is doing the work, not the adjectives.

Honest calibration, unchanged from 08-03: it is **the same actor photographed on different
days**, not the same photograph. The resolver's warning that this is weaker than IPAdapter
should stay.

**What the first run missed: the sheet imports POSE as forcefully as it imports style.**
This is visible on all three subjects and is clearest on HALE. Her A row is four
three-quarter views with varied head angles. Her B2 row is **four dead-frontal, symmetric,
neutral cells in the sheet's exact pose**. VIRO's B2 row is frontal in 4 of 4 the same way.

For a film that means your locked character faces camera in every shot. That is a real
cinematography cost, and it is the reason item 1 of the ranking beats item 2: the
multiple-angles LoRA gives you a *set* of reference poses to spend per shot.

### B1. An illustrated sheet locks hardest, and drags its style over an explicit instruction

VIRO's B1 row is four **comic-book illustrations** - flat cel shading, ink outlines - despite
every prompt asking for a `waist-up photograph`. The reference overrode an explicit
instruction in the prompt.

> **A qwen reference sheet carries STYLE as strongly as it carries IDENTITY.** Whatever the
> sheet is drawn in, the film is drawn in. Changing a film's style without re-rendering its
> sheets is incoherent, and re-rendering the sheets changes the faces.

Worth noting against its own row: B1 is the **most internally consistent row on the whole
grid**. A drawn face has fewer degrees of freedom than a photographed one. If a film is
stylised anyway, an illustrated sheet is an asset. It only misfires when the target is
photographic. `studio/_tools/qwen_sheet.py --style <lora>` exists to render a sheet in the
film's own style for exactly this reason.

### B3. short.py's phrasing is not worse - and for pose it is BETTER

`workflows/23_qwen_edit_2511_fusion.json` `_notes` say references must be called "image 1"
literally. `scripts/short.py` does not do this.

On identity I still cannot see a difference; B3 is as consistent as B2. But on **pose** B3 is
visibly freer: VIRO's B3 row keeps three-quarter and angled heads where B2 went frontal in
4 of 4. The literal *"keep their face, hair and features exactly as they are in image 1"*
phrasing is what buys the pose copying, not the reference image alone.

**Revised advice: short.py's phrasing is fine, and changing it to the literal form would cost
pose variety for no measured identity gain.** Leave it alone.

## C. The multiple-angles LoRA is the strongest mechanism, and it generalises

`X_C_angles.jpg`. Six views from a single photographic sheet: front, three-quarter, side
profile, back, looking up, low angle.

Both new subjects hold cleanly. HALE keeps her glasses through the profile and the
looking-up view, the jade stud stays on the correct ear, and the flat grey sheet background
survives. PLAIN holds across all six. The garment held on every view for both.

This remains the route to a qwen-native character LoRA: 16-40 consistent views is exactly the
training set that is otherwise impossible to produce by hand.

## D. Relight works, identity survives it, and its one artefact reproduces

`X_D_relight.jpg`. One fixed library keyframe per subject, three lighting setups, on
Qwen-Image-Edit **2509** with the 2509 Lightning accelerator at 4 steps.

Golden hour, hard top and blue rim all land, and in all six cells the pose, the background
bookshelves, the glasses, the sweatshirt and the face are preserved. This is the "give them a
certain look" half of the question and it is the half that behaves.

**The artefact reproduces on both new subjects:** asked for hard overhead light, the model
**drew a light fixture** at the top of the frame. It did this for VIRO on 08-03 and for both
HALE and PLAIN on 08-04. The model renders nouns, not adjectives, and "overhead light"
contains a noun.

Second observation, new: Relight does not only add a key, it **re-exposes the whole scene**.
All three lightings are substantially darker and moodier than the source. Budget for that -
it is a grade, not a lamp.

## E/F/G. Style LoRAs: the important claim generalises, the memorable one does not

**F - style LoRA, no reference.** `illustration-1.0-qwen-image` on its 2512 t2i base, three
seeds at 1.0 and three at 1.5.

The 08-03 run found VIRO became a young woman in 8 of 8 and concluded the LoRA "drags the
subject toward young anime women". **That specific conclusion is wrong.** On the new subjects:

- **HALE** (46) came back as an **elderly woman**, roughly 75-85, deeply lined, white-haired.
  Age destroyed - in the opposite direction from "young".
- **PLAIN** (early 40s) came back as an **older man with different ethnic features** and
  longer dark hair.

So the correct statement is the more useful one:

> **A style LoRA with no reference replaces the person.** It pulls the subject to whatever
> attractor that prompt has under those weights. The direction is not predictable from the
> LoRA's name or from one character's result - only the *fact* of replacement is.

6 of 6 on each new subject, consistent within subject across seeds. Combined with 08-03 that
is 20 of 20 across three people.

**G - the same LoRA, same seeds, same strengths, plus the reference sheet.** **The rescue
generalises.** HALE comes back as HALE - mid-forties, her glasses, her crop, her jade stud -
correctly restyled. PLAIN comes back as PLAIN. 6 of 6 each.

> **F and G are the answer.** A style LoRA alone re-invents the person. A style LoRA over a
> reference sheet restyles them. The reference sheet is what makes a style LoRA safe to use
> on a character at all.

Practical numbers, unchanged: on the *edit* model the style LoRA does almost nothing at 1.0
and lands at 1.5; on its own t2i base 1.0 is already fully committed. Same file, same
strength, different base, very different amount of effect.

## H. Two of the three qwen style LoRAs need a TRIGGER PHRASE, and nothing emits one

This closes the 08-03 open question "whether the other two qwen style LoRAs also flip the
subject", and the answer turned out to be about something else entirely.

Stage H ran `qwen_image_2512_storybook_anime_lora` and `qwen_image_modern_anime_lora` with
and without a reference. **Every cell came back a photograph.** Because "the LoRA does not
flip the subject" and "the LoRA never did anything" look identical from the output, that
needed a probe rather than a conclusion.

**Probe 1, `_probe/probe.jpg`** - same prompt and seed at strength 0.0 / 1.0 / 2.0:

| lora | 0.0 vs 1.0 mean delta | verdict |
|---|---|---|
| illustration-1.0-qwen-image | 35.6/255 | applied, fully stylised at 1.0, subject destroyed at 2.0 |
| qwen_image_2512_storybook_anime_lora | 25.4/255 | applied - but **still a photograph at 2.0** |
| qwen_image_modern_anime_lora | 32.0/255 | applied - but **still a photograph at 2.0** |

So they load and perturb pixels (composition drifts, the lamp moves) and impart no style.

**Probe 2, `_probe/trigger.jpg`.** The storybook file carries `trigger_phrase: "storybook
anime illustration"` in its own safetensors metadata. Prepending it, at the same seed and
strength 1.0:

- **storybook + trigger: full anime illustration.** Completely transformed, both phrasings.
  And the subject moved with it - the 40-year-old became a man in his twenties.
- **modern + trigger** ("modern anime"): partially woken - painterly and rendered, not
  photographic, but not fully drawn either. It declares no trigger phrase in metadata, so
  this is a guess at its vocabulary.

> **A qwen style LoRA that declares a trigger phrase does NOTHING without it, at any strength
> up to 2.0.** Not "less", nothing. The style slot in this studio loads LoRAs by filename and
> never emits a trigger.

`studio/compose.py:839` already warns about this in text. What was missing was the pixel
proof that the cost is total rather than partial. `studio/loras/qwen-storybook-anime.json`
already records the correct trigger phrase in its `trigger` field - the data is present and
unused. `studio/styles/storybook_illustration.json` routes to this LoRA, so that style is
currently a silent no-op.

**Not mine to fix** - `compose.py`, `short.py` and the style cards are owned elsewhere this
wave. Reported, not touched.

---

## Corrections to the 2026-08-03 write-up

1. **"A style LoRA drags the subject toward young anime women" - WRONG as stated.** It drags
   the subject *somewhere*, per-prompt. On HALE it was an elderly woman, on PLAIN an older man
   of different apparent ethnicity. The replacement generalises; the destination does not.
2. **"`sheet_viro.png` is an illustration because node 7 used to carry the storybook LoRA at
   0.8" - the mechanism cannot be right.** The storybook LoRA produces a photograph at 0.8,
   1.0 and 2.0 without its trigger phrase, and nothing in the render path emits one. Whatever
   made `sheet_viro.png` an illustration, it was not that LoRA acting silently. The
   *observation* stands - the sheet is a drawing and it does contaminate arm B1 - only the
   stated cause is retracted. **The cause is now unknown and worth finding.**
3. **"A face with fewer distinctive markers may drift more" - not supported.** With a
   reference sheet, PLAIN locks as well as VIRO. Without one, PLAIN drifted *less*, not more.
4. **"B3's phrasing is not visibly costing anything" - understated.** B3 is not merely
   harmless, it preserves pose variety that B2's "keep exactly" phrasing destroys.
5. **The reference sheet's pose import was not reported at all** and is a first-order
   constraint on how a locked character can be shot.

---

## What this still does not establish

- **Three subjects, all rendered by the same model family.** All photographic-target. No
  child, no non-European subject as a *designed* subject rather than an accident of the
  style LoRA, no full-body or multi-person frame.
- **Four places per arm, one judge, by eye.** No landmark metric, no embedding distance.
  Every "same person / different person" call in this document is my visual judgement on a
  face crop. A quantitative identity metric would be the single biggest upgrade to this
  method and does not exist here.
- **The A-row marker-count hypothesis is one observation on three people**, and the mechanism
  I propose for it (generic prompt lands on the modal face) is untested.
- **`modern-anime-2`'s trigger vocabulary is guessed.** It declares none in metadata. "modern
  anime" partially woke it; the real phrase may do more.
- **Relight's 2509 base-lock is still inferred from the filename**, not read from metadata.
- **No video.** Every image here is a still keyframe. Whether a reference-locked keyframe
  survives being animated through LTX is untested.
- **Still no qwen-native trained character LoRA.** Nothing on this box has trained one.
  `workflows/33_train_character_lora.json` hard-codes `CheckpointLoaderSimple{animagine}` and
  `train_character.py` has no `--base` flag, so the existing tool cannot make one. Stage C now
  produces the training set that would feed it on two subjects.

---

## Reproducing

    python3 studio/_tools/qwen_character.py                          # VIRO, all stages
    python3 studio/_tools/qwen_character.py --subject HALE PLAIN     # the generalisation run
    python3 studio/_tools/qwen_character.py --subject all --sheets   # contact sheets only

    python3 studio/_tools/qwen_sheet.py HALE                         # a photographic sheet
    python3 studio/_tools/qwen_sheet.py HALE --style <lora> --tag illus   # a stylised one

`qwen_character.py` is multi-subject: subjects come from its `SUBJECTS` table, and a real
`studio/characters/<ID>.json` overrides the built-in copy automatically if one exists. VIRO's
output stays in the flat `samples/qwen_character/` layout so the 08-03 measurements remain
reproducible; new subjects get a subdirectory.

Two things about how it schedules, both load-bearing on a shared box:

- **Stage order is grouped by checkpoint** (2512 t2i, then 2511 edit, then 2509 edit), and the
  whole group is submitted as ONE batch. Each checkpoint is ~20 GB fp8 on a 32 GB card, so
  submitting cell-by-cell onto a busy box lets an unrelated job run between every pair and the
  card reloads 20 GB each time.
- **Submission uses ComfyUI's `front` flag** (`server.py:1072`), which reorders the pending
  queue and **cancels nothing**. Other work still runs, just after ours. Pass `--no-front` to
  queue politely. The 08-04 run was 76 images in **9.0 minutes** with 68 unrelated video jobs
  already queued.
