# Cast

`/cast` and `/character/<ID>`

## What this page is for

Characters you can put in more than one scene and have come back looking like the same
person. Seven exist: TERRA, NIKA, BRACK, PIP, RASK, VIRO, MANAGER.

Three things can hold a face, in increasing order of strength:

1. **Tags or prose alone** — a description. Weakest. The face drifts between renders.
2. **A reference sheet** — an image the model is shown. Stronger.
3. **A trained LoRA** — weights. Strongest.

The page filters by exactly that: *held by anything / trained weights — the strongest
lock / a reference sheet only*.

Every claim on a card is checked against the filesystem before the page renders it. The
cast page used to show a green tick for a string being non-empty, so a card naming a
deleted `.safetensors` looked exactly like a trained one.

## What to do first

Open **TERRA**'s dossier at `/character/TERRA`. She is the worked example — trained LoRA
at strength 0.5, a composite photo sheet, four costumes, and a dossier section for every
question the project has asked about her. Read the `identity_note`. It is the most
honest document in the app and it will teach you what these cards are for.

## The three things that will confuse you

**1. A reference sheet imports its style as hard as its identity — and pins the medium.**

This is true on both paths: the anime IPAdapter path and the qwen edit path. Feed in a
photographic sheet and you will get photographs, whatever else you ask for. Asking the
qwen edit path for a 3D render or an oil painting of that person returns the same
photograph.

The consequence is genuinely counter-intuitive: **a semi-real version of a character has
to be built on the illustration engine.** Name plus character LoRA plus a painterly or CG
style, with IPAdapter at 0.0. That is the opposite engine from where anyone would look.

**2. A character LoRA is base-model locked. It does nothing on qwen.**

TERRA's `character_terra_00001_v3.safetensors` was trained on the SDXL side. Attach it to
a qwen render and it costs the same GPU time and changes nothing. The LoRA library says
which base each file belongs to; believe it.

**3. A photographic reference sheet must be a composite.**

Measured, three ways:

- a **body-only** sheet gives a small, soft face;
- a **close-only** sheet fixes the face and **loses the costume**;
- a **composite** — a close face panel and a body panel in one image — keeps both.

If your character's clothes keep changing, the sheet is the reason.

## The thing that will make you think the app is broken

TERRA's tags say `red hair ribbon`. She does not have one. All 160 view renders on both
engines draw a large pink-and-gold ornament with a red gem and two upswept prongs that
read as horns. It is in the source sheet, both engines inherited it, and it is now
trained into the LoRA.

It is left unfixed **deliberately**: changing `tags` would move every render of her and
invalidate the LoRA trained against them. Fixing it properly needs a new sheet and a
retrain, not a tag edit.

Two more live in the same note: the bodice colour flips gold/red seed by seed, and the
two engines disagree about her hair colour.

## What good output looks like here

- The face is recognisable **at the framing you actually rendered**. If it is not, frame
  closer before you touch any weight. At 832x1216 full-body the face is about 90 pixels,
  decided by an 11x11 latent patch — there is nothing there to be recognisable with.
- The costume survives. If the identity holds and the clothes do not, the sheet is
  body-only or close-only rather than composite.
- In a moving clip, identity holds for about eight seconds, but **budget by the action**.
  On a head turn the face is frontal to 5s, in profile at 7s, and showing the back of the
  head at 8s. That is not identity failure; that is the shot you asked for.
