# LoRAs — what you have, what they do, what to get, how to train your own

*Verified against the live box 2026-07-29. Every filename below was extracted from the
built-in templates with `scripts/_lora_audit.py`, so the names are real, not guessed.*

---

## The headline

> **Superseded during the same session — read this first.** When this was written you had five
> LoRAs, all technical, and **zero** style LoRAs. Two things changed within hours:
> a concurrent session downloaded **`qwen_image_2512_storybook_anime_lora`** (0.27 GB) and
> **`qwen_image_modern_anime_lora`** (0.55 GB), both style LoRAs on the Qwen 2512 base you own;
> and the second download session added `Qwen-Image-Edit-2511-Lightning-4steps`,
> `ltx-2.3-22b-ic-lora-union-control-ref0.5`, `ltx-2.3-id-lora-talkvid-3k` and
> `Flux2TurboComfyv2`. **Current count: 11.** The paragraph below was accurate when written and is
> now historical — the *argument* still holds (technical LoRAs dominate, and two anime style LoRAs
> is not an art-direction toolkit), but "zero style LoRAs" is no longer literally true.
>
> Re-audit any time with `python3 scripts/_lora_audit.py`.

**You have five LoRAs and not one of them changes how anything looks.** All five are
*technical* — accelerators, a distillation, and a text-encoder patch. You own zero style
LoRAs, zero character LoRAs, zero concept LoRAs.

That matters because LoRAs are the main mechanism for art direction in open image models.
Prompting gets you a *genre*; a LoRA gets you a *specific look*, repeatably, across a
hundred images. Right now every render you make comes out looking like base Qwen-Image.

| Installed | Size | Type | What it actually does |
|---|---|---|---|
| `Qwen-Image-2512-Lightning-4steps-V1.0-fp32` | 1.7 GB | **accelerator** | Lets Qwen-Image render in 4 steps instead of 20. Pure speed. |
| `wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise` | 1.2 GB | **accelerator** | Same idea for Wan 2.2 I2V, high-noise expert. |
| `wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise` | 1.2 GB | **accelerator** | Wan 2.2 I2V, low-noise expert. |
| `ltx_2.3_22b_distilled_1.1_lora_dynamic_fro09_avg_rank_111_bf16` | 2.7 GB | **distillation** | Lets LTX-2.3 run its short sigma schedules. |
| `gemma-3-12b-it-abliterated_lora_rank64` | 628 MB | **text-encoder patch** | Removes refusal behaviour from Gemma so it will *write prompts*. Changes nothing about the image. |

And the single biggest cheap win available to you:

> **You have Qwen-Image-Edit 2509 but none of its LoRAs — including its 4-step Lightning
> accelerator.** That is why `03_qwen_image_edit.json` takes **48 seconds** while
> `01_qwen_t2i_turbo.json` takes 4.5. One 1.7 GB download should cut editing to roughly
> 10 s. See [the shopping list](#the-shopping-list).

---

## What a LoRA is, in one paragraph

A LoRA (Low-Rank Adaptation) is a small set of correction matrices that get added to a
frozen base model's weights at load time. Instead of a 20 GB fine-tune, you ship 50–200 MB
of deltas. `rank` is how many dimensions of correction it carries — rank 8–32 for a style,
rank 64–128 for something structural. Because it is *added* to the base, a LoRA is welded
to the base model it was trained on: **a Qwen-Image LoRA does nothing on Flux, SDXL, or
Wan.** Not "worse" — nothing, or noise. Check the base model before you download, always.

## The seven kinds

Worth knowing because they behave differently and want different strengths.

| Kind | What it does | Typical strength | Notes |
|---|---|---|---|
| **Accelerator / distill** | Fewer sampling steps | **1.0, exactly** | Not a taste dial. Pairs with a mandatory `steps`/`cfg` change. |
| **Style** | A specific look — an illustrator, a film stock, a medium | 0.6–1.0 | The most common kind. Stack 2–3 at reduced strength. |
| **Character / identity** | A consistent person or creature | 0.7–1.0 | Needs a trigger word. The reason to train your own. |
| **Concept** | An object, outfit, mechanism, architecture | 0.6–1.0 | Also trigger-word driven. |
| **Detail / slider** | Amplifies or suppresses one axis (detail, age, weight) | −1.0 … +1.0 | Some accept negative strength. |
| **Control (IC-LoRA)** | Adds a *control modality* — depth, canny, pose | 0.5–1.0 | LTX-2.3's way of doing ControlNet. |
| **Text-encoder** | Changes how prompts are *read* | 1.0 | Your abliterated Gemma. `strength_clip` is the one that matters. |

## Mechanics in ComfyUI

Four nodes matter:

| Node | Use when |
|---|---|
| `LoraLoaderModelOnly` | **The default.** Patches the diffusion model only. Every accelerator, most styles. |
| `LoraLoader` | You also need to patch the text encoder. Returns `MODEL, CLIP`. Required for text-encoder LoRAs. |
| `LoraLoaderBypass` / `…BypassModelOnly` | A/B testing — flip a `bypass` boolean instead of rewiring. |
| `LoraModelLoader` | Takes a `LORA_MODEL` object rather than a filename. What you use straight out of training. |

**Stacking is just chaining.** Each loader takes a `MODEL` and returns a patched `MODEL`:

```
UNETLoader ─> LoraLoaderModelOnly (accelerator, 1.0)
           ─> LoraLoaderModelOnly (style A, 0.7)
           ─> LoraLoaderModelOnly (style B, 0.4)
           ─> ModelSamplingAuraFlow ─> KSampler
```

Rules that save time:

- **Accelerator first, always.** It is the largest, most structural patch.
- **Total style strength should land near 1.0.** Two styles at 1.0 each fight and give you
  mud. 0.7 + 0.4 is a blend; 1.0 + 1.0 is a mess.
- **Order matters less than total strength**, but keep it consistent so results are reproducible.
- `strength_clip` only exists on `LoraLoader`. For a style LoRA leave it equal to
  `strength_model`. For a text-encoder LoRA it is the *only* one doing anything.
- **Trigger words.** Character and concept LoRAs are trained against a specific token
  (`ohwx man`, `sks style`). Omit it and the LoRA barely engages. The publisher's model card
  is the only source for this — there is no way to read it off the file.

### What strength actually looks like

`17-lora-mechanics/` is the Lightning accelerator swept 0.0 → 1.3 at a fixed 4 steps,
cfg 1.0, seed 555. Browse it; it is a 30-second lesson:

| Strength | Result |
|---|---|
| **0.0** | Soft, grainy, muddy. The model needed 20 steps and only got 4. |
| **0.4** | Still undercooked, contrast flat. |
| **0.7** | Nearly there. Usable. |
| **1.0** | **Correct.** Crisp, full contrast. This is the design point. |
| **1.3** | Overcooked — harsh contrast, oversharpened edges, streaky rain artifacts, oversaturated. |

The lesson generalises: **1.3 is not "more style", it is damage.** Above ~1.1 most LoRAs
start fighting the base model instead of steering it. When a LoRA looks too weak at 1.0 the
answer is usually a better prompt or a trigger word, not 1.5.

---

## The shopping list

54 distinct LoRAs are referenced by the 268 local templates. You have 5. These are the ones
that matter **for base models you already own** — everything else on the list needs a base
model you do not have, so it is a second-order purchase.

Regenerate this audit any time with `python3 scripts/_lora_audit.py`.

### Tier 1 — fixes a real bottleneck today

| LoRA | Why |
|---|---|
| `Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16` | **Get this first.** Turns your 48 s edit into ~10 s. You already have the base model. |
| `Qwen-Image-Lightning-4steps-V1.0` | The ControlNet templates expect *this* file, not your 2512 variant. Unblocks `image_qwen_image_instantx_controlnet` and friends as written. |

### Tier 2 — new capabilities on models you own

| LoRA | Unlocks |
|---|---|
| `Qwen-Edit-2509-Multiple-angles` | **Character sheets / turnarounds** — one image to many consistent angles. `templates-1_click_multiple_scene_angles` |
| `Qwen-Image-Edit-2509-Relight` | Relight a photo without redrawing it. `image_qwen_image_edit_2509_relight` |
| `Qwen-Image-Edit-2509-Light-Migration` | Copy the lighting off a *reference* image onto yours. Directly fixes the composite problem in folder 15. |
| `Qwen-Image-Edit-2509-Anything2RealAlpha` | Stylised → photoreal conversion. |
| `ltx-2.3-22b-ic-lora-union-control-ref0.5` | **Depth / edge / pose control for VIDEO.** Nothing else you have does this. `video_ltx2_3_ic_lora` |
| `ltx-2.3-id-lora-talkvid-3k` | **Lock a character's identity across shots.** The missing piece for multi-shot narrative. `video_ltx2_3_id_lora` |
| `ltx2.3-transition` | Morph between two styles over a clip. `template_ltx2_3_style_transition` |
| `illustration-1.0-qwen-image` | A genuine style LoRA for your Qwen base. Your first one. |
| `qwen-360-diffusion-2512-int8-bf16-v2` | 360° object turnarounds. `template_qwen_Image_2512_360_lora` |

### Tier 3 — needs a base model you do not have

`Flux_2-Turbo-LoRA_comfyui`, `krea2_darkbrush`, `anima-turbo-lora-v0.2`,
`chronoedit_distill_lora`, `wan2.2_t2v_lightx2v_*` (needs Wan T2V),
`Wan21_CausVid_14B_T2V_lora_rank32` (needs VACE), `uso-flux1-dit-lora-v1`,
`pixel_art_style_z_image_turbo` (needs Z-Image). Buy the base first.

### Where to get them

- **The templates tell you.** Open a template in the UI and ComfyUI's missing-models dialog
  offers the exact file with a download button. This is by far the least error-prone route
  and it puts the file in the right folder.
- **Hugging Face** — `Comfy-Org/*` and `lightx2v/*` mirror most of the accelerators.
- **Civitai** — the bulk of community style and character LoRAs. Filter by base model; the
  site's filter is reliable and the base model is non-negotiable.

Everything goes in `~/ComfyUI/models/loras/` (= `Z:\ComfyUI\models\loras\`). Subfolders are
fine and show up as `subfolder/name.safetensors` in the dropdown — worth doing once you pass
a dozen files.

---

## Training your own — you can do this on this box, today

**`TrainLoraNode` is built into your ComfyUI 0.28.0.** No Kohya, no OneTrainer, no separate
environment. This is the part most people do not realise is available.

The graph — **corrected 2026-07-29**, verified against the live `/object_info`:

```
LoadImageTextDataSetFromFolder ─> (IMAGE, STRING) ─┐
UNETLoader ─────────────────────────> model ───────┼─> MakeTrainingDataset ─> (LATENT, CONDITIONING)
VAELoader / CLIPLoader ─────────────> vae, clip ───┘            │
                                                                 └─> TrainLoraNode ─> LoraSave
```

> ⚠ An earlier version of this section named `LoadImageSetFromFolderNode` and a manual
> `VAEEncode` + `CLIPTextEncode` pair. **`LoadImageSetFromFolderNode` does not exist.** The real
> loader is `LoadImageTextDataSetFromFolder` (returns `IMAGE, STRING`), and `MakeTrainingDataset`
> (`images`, `vae`, `clip`, optional `texts`) fuses the encode steps — so the actual graph is
> *simpler* than what was described, not more complex.

Also available, and worth knowing: `LoadImageDataSetFromFolder` (no captions),
`ShuffleImageTextDataset`, `SaveTrainingDataset` / `LoadTrainingDataset` (cache the encoded
dataset so you only pay the VAE pass once across many training runs), and —
undocumented anywhere else in this kit — **`LoadVideoTextDataSetFromFolder` /
`LoadVideoDataSetFromFolder`, i.e. video LoRA training is available on this box too.**

`TrainLoraNode` returns `LORA_MODEL`, `LOSS_MAP`, `INT`. Pipe `LORA_MODEL` into `LoraSave`
to write a `.safetensors`, or straight into `LoraModelLoader` to test it in the same run
before committing it to disk.

### The parameters that matter

| Parameter | Default | Guidance |
|---|---|---|
| `rank` | 8 | 8–16 style, 32 character, 64+ structural. Higher = more capacity, more overfitting, bigger file. |
| `steps` | 16 | Far too low. Reckon **~100 steps per training image**: 20 images → ~2000 steps. |
| `learning_rate` | 5e-4 | Reasonable for rank 8–16. Drop to 1e-4 for high rank. |
| `batch_size` | 1 | Keep at 1 on 32 GB and use `grad_accumulation_steps` instead. |
| `grad_accumulation_steps` | 1 | Set 4–8 for an effective batch of 4–8 without the VRAM. |
| `optimizer` | AdamW | Fine. AdamW8bit if you are tight on VRAM. |
| `algorithm` | LoRA | LoKr/LoHa variants exist; start with plain LoRA. |
| `existing_lora` | [None] | **Resume or continue training an existing LoRA.** Underrated. |
| `bucket_mode` | false | **Turn this ON for a character set.** Groups mixed aspect ratios into buckets so you can train on a mix of CU / medium / full-body without cropping everything square. |
| `bypass_mode` | false | Leave off. |

### Fitting a 20 B model's training into 32 GB

Three flags, in the order you should reach for them:

1. `gradient_checkpointing: true` — already the default. Recomputes activations instead of
   storing them. Large saving, ~30% slower.
2. `offloading: true` — pushes optimiser state to your 60 GB of system RAM. Slower again,
   but decisive.
3. `quantized_backward: true` — last resort. Quantises the backward pass; costs quality.

`checkpoint_depth` trades more recompute for less memory if 1 is not enough.

### A realistic first run

- **15–30 images.** More is not better; *consistent* is better. For a style, keep subject
  matter varied and treatment identical. For a character, vary pose/lighting/background and
  keep the face constant.
- **Caption every image**, describing everything *except* the thing you are teaching. If you
  caption the style, the model learns the style belongs to those words rather than to the
  trigger.
- **Pick a trigger token** that is not real English — `zkrn style` — and put it in every caption.
- Save intermediate ranks and **test at strength 0.6, 0.8 and 1.0** before deciding it works.
  A LoRA that only looks right at 1.0 is usually overfitted.

`LoraSave` also does something separate and useful: give it `model_diff` (two models
subtracted) and it **extracts** a LoRA from any full fine-tune you have lying around,
turning a 20 GB checkpoint into a 200 MB LoRA.

### Honest caveat

I have not run a training job on this box, so I have no measured timings for you — unlike
everything else in this kit, the training section is read from the node schema and general
practice rather than verified end to end. Expect to spend an evening on the first one.
A rank-16 style LoRA on ~20 images at ~2000 steps is the right size for a first attempt.

---

## See also

- `17-lora-mechanics/` — the strength sweep described above
- `16-style-range/` — how far *prompting alone* gets you, which is the honest baseline a
  style LoRA has to beat
- [AI-CONTENT-MAP.md](AI-CONTENT-MAP.md) — where LoRAs sit in the wider picture
- [TEMPLATES.md](TEMPLATES.md) — which templates each LoRA unblocks
