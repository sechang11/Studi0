# Bringing in a character the model might already know

Every cast member so far — VIRO, NIKA, PIP, BRACK, RASK, MANAGER — was invented here.
Nothing in the checkpoint had ever seen them, so each one costs a reference sheet, a
sixteen-view turnaround and a LoRA training run: roughly twenty minutes of GPU.

A character from an existing game, film or series is a different problem, because
animagine-xl-4.0 is an SDXL finetuned on the danbooru corpus, where well-known characters
are tagged by name as `character name (series name)`. If that tag has mass, the character
comes back from the tag alone — no sheet, no turnaround, no LoRA — and *more* consistently
than a trained LoRA, because she is in the base weights rather than patched on top.

So the first question is never "how do we build her". It is **"does the checkpoint already
have her?"**

## The test, and the cell people forget

    python3 studio/_tools/known_char_probe.py "terra branford" \
        --series "final fantasy vi" \
        --desc "1girl, long wavy green hair, red hair ribbon, red cape, yellow dress, fantasy"

Four cells at one seed:

1. the danbooru form — `character (series)`
2. the bare name
3. name **plus** a description
4. **the description alone, with no name at all**

Cell 4 is the one that matters and the one a careless test omits. If the control looks like
the named cells, the name did nothing and the adjectives are carrying it. This is the
project's governing rule — *the model renders nouns, not adjectives* — applied to character
names: **a name only counts as known if it beats its own description.**

## What Terra actually returned

Measured 2026-08-04 on animagine-xl-4.0, seed 9090.

| cell | result |
|---|---|
| `terra branford (final fantasy vi)` | green-blonde wavy hair, red cape, patterned bodice, an orb in both hands. In the neighbourhood. |
| `terra branford` alone | **blonde in a white hood.** Not her. |
| name + description | closest to the FF6 design — green hair, red cape, yellow dress |
| **description only (control)** | **green hair, red cape, yellow dress, red ribbon — nearly as close** |

**Verdict: partially known, not reliably known.** The bare name fails outright. The
danbooru form gets into the right palette and silhouette and reliably adds the orb, which
is a noun the tag genuinely carries. But the description alone does most of the work, so
the tag is thin.

Practical consequence: **you cannot cast her from a name.** The path is the same as any
original character — but the name gives you a much better starting portrait to build the
reference sheet from, which is worth real time.

## Provenance, and why the card records it

Character cards now carry `provenance`:

- `original` — invented here. The full build is mandatory.
- `known_strong` — the tag beats its own description. Castable from tags; a LoRA is
  optional and may even be worse than the base weights.
- `known_partial` — like Terra. The name helps; it does not carry the character. Build the
  full pipeline, using the name to seed the sheet.
- `known_absent` — the name does nothing at all. Treat as `original`.

Recording it stops the same probe being run twice, and stops someone assuming a famous name
will "just work" — which is exactly the assumption that produced a blonde in a white hood.

## Before you publish

A character out of a published game is someone's intellectual property. Making the work is
ordinary — fan art is a very old practice and the whole danbooru corpus this model learned
from is built on it. **Distributing** a finished film built on that character is a
different question from rendering it, and it is the author's call to make knowingly rather
than by accident.

So the card records provenance and the source series, and that is all it does. This is not
the same as the four blocked voice packs in `studio/voices/` — those clone **real people**,
which is a likeness question rather than a copyright one, and they stay blocked.
