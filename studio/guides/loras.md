# LoRAs

`/loras`

## What this page is for

22 trained weight files, each checked against what is actually in `models/loras` before
the page will call it available. A LoRA changes the model itself rather than the prompt,
which is why it can do things no prompt can.

Five kinds:

| kind | count | what it does |
|---|---|---|
| `speedup` | 8 | Fewer sampling steps for the same picture. Costs quality, saves minutes. |
| `edit` | 6 | Adds an editing capability — relight, multiple angles, transitions. |
| `character` | 4 | Locks one person's face. NIKA, PIP, VIRO, TERRA. |
| `style` | 3 | Changes the medium at the weights. |
| `utility` | 1 | Plumbing. |

## What to do first

Open **Illustration 1.0 (Qwen-Image)** and read its verdict. It is the card that explains
why this layer exists at all:

> At strength 1.0 the same watercolour prose at the same seed produced genuine painted
> illustration where the identical run without it produced a photograph. [...] Qwen
> CANNOT be steered off photography by prompt at any cfg — 20 steps, cfg 4.0, Lightning
> LoRA off, "painting, illustration" in the negative, and it still returned a photograph.

That is the whole argument: **the LoRA does what the prompt cannot.**

## The three things that will confuse you

**1. A LoRA is base-model locked, and the lock is silent.**

Every card carries `base_model` and `engine`. A qwen LoRA on an anime render, or an SDXL
character LoRA on a qwen render, does not error. It loads, costs the same GPU time, and
changes nothing. Use the **every base model** filter and match it to the engine your
style chose.

**2. Strength is a range, not a dial you turn up when unhappy.**

Each card carries `strength` (the recommendation) and `strength_range` (where it was
measured). Illustration 1.0 is 1.0, measured 0.6–1.5. TERRA's character LoRA is 0.5.

The temptation is to raise strength when a face comes out wrong. **This is the single
most common wasted hour in this project.** Raising a character LoRA's strength does
almost nothing to face quality, because a bad face is a resolution problem: at 832x1216
full-body the face occupies about 90 pixels. Frame closer first.

**3. The filename and the training identity can disagree.**

The Illustration 1.0 card notes it about itself. `base_model` on these cards is read out
of the safetensors header (`ss_base_model_version`), and the header names the *family*,
not the revision. Where the header is ambiguous, the card says which pixels settled it.
Read the note, not the filename.

## What good output looks like here

The honest test is a **same-seed pair**: one render with the LoRA, one without, nothing
else changed. If you cannot see the difference, the LoRA is not attached, is on the wrong
base model, or is at a strength below where it was measured.

Then a **strength ladder** — the same seed at 0.5, 1.0, 1.5. What you want to see:

- a clear change between the rungs, and
- a rung where it stops improving and starts distorting.

Pick the rung below that one. A ladder with no visible change between rungs means the
LoRA is doing nothing, whatever its card says.
