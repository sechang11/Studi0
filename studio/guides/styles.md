# Styles

`/styles`

## What this page is for

Browsing the 130 style cards and finding out, before you spend GPU time, what each one
actually did when somebody rendered it. A style card is not a preset. It is a claim plus
the evidence for or against it.

Style is the outermost layer of the stack and the field that picks the engine:
**85 cards route to anime, 45 to qwen**.

## What to do first

Set the engine filter to **anime — the illustration engine** and read five cards with
status `ready`. Then set it to **qwen — the photographic engine** and read five more.
You will learn the split faster from ten cards than from any explanation.

Then search for the word `injects` and read what those cards say about themselves.

## The three things that will confuse you

**1. "anime" is the general illustration engine.**

It is named after the checkpoint (`animagine-xl-4.0`), not the genre. It renders
watercolour, ukiyo-e, oil paint, gouache, pencil. If you want anything drawn rather than
photographed, you want this engine, whatever the subject.

**2. The `compose` field is the single most useful thing on the card.**

Four values, and they mean very different things:

| value | count | what it means |
|---|---|---|
| `safe` | 86 | Re-renders the same scene in a new idiom. Stacks cleanly with everything. |
| `replaces` | 16 | Re-renders the scene **and overrides the setting**. It will fight your place card. |
| `injects` | 20 | The noun in the style's name gets drawn as an object in frame, usually into the subject's hands. |
| `inert` | 8 | Measured as indistinguishable from no style at all. Picking it buys nothing. |

`injects` is the noun rule in the wild. The `graffiti` card's verdict reads, in full:
*"Put a spray can in her hand. The card rated this the highest noun risk in the batch and
it was right."*

**3. `status` is about evidence, not quality.**

`ready` means somebody rendered it and looked. `weak` means it partly worked and the card
says how — `pointillism`, for example, produces discrete dots that read as falling snow
rather than optical mixing. `unavailable` means it does not work, and the card says why.
94 ready, 24 weak, 12 unavailable.

## Two things on this page that are wrong right now

- **19 sample images are rendered on the other engine** from the one the card routes to
  (the count is `serve.py`'s own, over 131 files including the control). The page says so
  where it knows. Read the engine field, not the picture.
- **One card contradicts itself.** `stop_motion_felt` is served with two badges that say
  opposite things. This is open task #28, still unfixed. If a card's badges disagree,
  trust the verdict text, which is the part somebody wrote after looking.

## What good output looks like here

The style changed the **medium** and left the **subject** alone.

- Good: the same woman on the same street, now in gouache.
- Bad, `injects`: the same woman, now holding the object the style is named after.
- Bad, `replaces`: a different street entirely.
- Bad, `inert`: you cannot tell it apart from the control render.

If you cannot tell a styled render from the control at a glance, the style did nothing.
That is a real outcome and eight cards in the library admit to it.
