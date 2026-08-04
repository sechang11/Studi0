# A caption is a subtraction, not a description

Every character LoRA in this project was trained with captions that read

    terra, front
    terra, three quarter
    terra, side left

and nothing else. That one decision caused two bugs that were written down as unrelated
facts about two different things, and it will cause the same two in every character
trained from here unless the rule below is followed.

## The mechanism

During training each image is paired with its caption. Whatever the caption **names** is
explained by that word and is learned as an independent thing you can ask for later, or
not ask for. Whatever is present in the images and named **nowhere** still has to be
accounted for by something — and the only token present in every caption is the trigger.
So the trigger absorbs it. Permanently. As part of what the character *is*.

> **Caption exactly what you want to be able to change later.
> Omit exactly what you want welded on.**

A caption is not a description of the picture. It is the list of things you are
*subtracting* from the trigger's meaning.

## The two bugs this caused

TERRA's 16 training views were all one outfit against one flat taupe wall. Neither was
captioned, so `terra` came to mean *the woman **and** the gold dress **and** the taupe
wall*.

| how it was originally recorded | what it actually was |
|---|---|
| "The LoRA memorised her clothes — a costume change fights the weights." | the uncaptioned **outfit**, absorbed into the trigger |
| "0.85 destroys the setting — a sunlit field went grey, a snow forest collapsed to **flat beige**." | the uncaptioned **backdrop**, absorbed into the trigger. Beige *is* the turnaround wall. Turning the LoRA up turns the memorised wall up. |

The second had been filed as a property of LoRA strength, which is why adjusting strength
was never going to fix it.

## The rule, as the tool now implements it

`turnaround.py` `caption()` writes:

    <trigger>, <view>, <the garments at damage level 0>, plain flat grey background

Named, therefore separable: **wardrobe, backdrop, view.**
Unnamed, therefore welded on: **face, hair, eyes, build.** Those are the character.

`train_character.py` now prints the captions before it trains and warns when they name
little beyond the trigger. The bug survived this long for one reason: captions were the
only input to training that nothing ever displayed.

## What it bought, measured

Three LoRAs, one seed, evidence in `studio/samples/cast/terra_costume_fix/`.
v1 uncaptioned · v2 recaptioned, one costume · v3 recaptioned across two costumes.

**Setting, at 0.85** (`setting_grid.jpg`) — a clean win. v1 replaces a snow forest with a
featureless taupe void and shrinks a meadow to an arch-shaped window in taupe. v3 holds a
real forest with depth and a real meadow with sky, same seed, same strength. **The
strength ceiling is raised**, which matters because strength is identity lock.

**Wardrobe** (`costume_ab.jpg`, `costume_mixed_ab.jpg`) — a real but partial win, and it
came with a correction to the original diagnosis. Captions alone (v2) moved it a little;
adding a second costume to the dataset (v3) moved it more. Monotone: v1 < v2 < v3.

## The correction: it was never only the weights

The baseline grid added the control the first pass omitted — **the same shot with no LoRA
at all** — and it split the blame:

| | imperial plate lands? |
|---|---|
| danbooru name, no LoRA | **yes**, full black armour |
| danbooru name + LoRA | **no**, the patterned dress persists |
| name stripped + LoRA | **yes** |
| name stripped, no LoRA | **yes** |

For a **known** character the danbooru tag carries the canonical outfit in the base
checkpoint, and the LoRA carried it too. **Either one alone is survivable; the two
together saturate.** Retraining fixes the LoRA's half. The tag's half is a prompt problem
and cannot be trained away — so **on a costume shot for a known character, strip the
danbooru name.** The LoRA carries her without it; that was already measured.

For an *invented* character there is no tag half, so captions alone should be enough.

## And one failure that was neither

TERRA's `field` costume failed in **all four rows, including both no-LoRA controls**. Its
own level-0 text reads `heavy brown travelling coat over the gold dress`. The model
renders nouns, so it renders the gold dress and drops the coat: the costume names the very
garment it exists to replace. No retrain will ever touch that.

**A costume must describe what is worn, not what it is worn over.** Check a costume
against a no-LoRA control before blaming the weights.

## Retrofitting an existing character

No re-render needed for step 1 — the images are fine, only the `.txt` files were wrong.

    python3 studio/_tools/turnaround.py TERRA --captions-only   # no GPU
    python3 studio/_tools/train_character.py TERRA --no-card    # ~10 min
    # LOOK at it, then adopt onto the card by hand

For a second costume in the set (worth it for known characters):

    python3 studio/_tools/turnaround.py TERRA --costume court   # ~2 min
    python3 studio/_tools/train_character.py TERRA --no-card

`--no-card` exists because adopting a LoRA onto a card makes it live for every other tool
immediately, and a retrain has to be looked at first. **VIRO, NIKA, PIP, BRACK and RASK
are all still on uncaptioned single-costume LoRAs and all carry both bugs.**

### Two traps in the measuring, both of which produced a convincing wrong answer here

- `epic.ensure_local()` returns early when the destination file exists. A probe that names
  its scratch files after the cell re-tiles the **previous** run's images, and the grid
  comes back byte-identical — which reads as "the change did nothing". Give every run its
  own scratch directory.
- Hardcoded row labels on a comparison grid. A panel rendered from v3 went out labelled
  "v2", and an evidence file that misnames itself argues for the wrong thing forever.
  Labels should default to the actual filenames.
