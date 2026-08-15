# Second pass — four installed models that were doing nothing

*Added 2026-07-29, later the same day as the original kit. Everything below runs on
weights that were **already on the box** — no downloads.*

The first pass built the image / video / audio / film pipeline. Auditing it against the
model directory turned up four files that were downloaded, verified, and then never
referenced by any workflow, plus one that was in the wrong folder and therefore
invisible to ComfyUI.

| Model | Size | Was | Now |
|---|---|---|---|
| `detection/sam3.1_multiplex_fp16.safetensors` | 1.7 GB | unused **and misplaced** | [`13_sam3_segment.json`](workflows/13_sam3_segment.json) |
| `background_removal/birefnet.safetensors` | 424 MB | unused | [`14_birefnet_matte.json`](workflows/14_birefnet_matte.json) |
| `latent_upscale_models/ltx-2.3-spatial-upscaler-x2-1.1.safetensors` | 950 MB | unused | [`17_ltx23_t2v_upscaled.json`](workflows/17_ltx23_t2v_upscaled.json) |
| `loras/gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors` | 628 MB | unused | [`18_ltx_prompt_enhancer.json`](workflows/18_ltx_prompt_enhancer.json) |

Also unused: `TextGenerate`, the node that turns any of the installed text encoders into
a local chat LLM. That is now [`15_llm_prompt_studio.json`](workflows/15_llm_prompt_studio.json),
[`16_llm_to_image.json`](workflows/16_llm_to_image.json) and
[`scripts/idea.py`](scripts/idea.py).

---

## 1. SAM 3.1 — text-prompted segmentation

`13_sam3_segment.json` · **12–18 s** · samples in `12-segmentation-matting/`

Type what you want cut out — `"the wristwatch"`, `"her jacket"`, `"the left hand"` — and
SAM finds it and returns a mask. No clicking, no box drawing.

**It was in the wrong folder.** It shipped into `models/detection/`, but the node that
loads it is `CheckpointLoaderSimple`, which only reads `models/checkpoints/`. So it was
invisible. Fixed with a symlink, no second copy:

```bash
ln -sf ../detection/sam3.1_multiplex_fp16.safetensors ~/ComfyUI/models/checkpoints/sam3.1_multiplex_fp16.safetensors
```

`CheckpointLoaderSimple` returns `MODEL, CLIP, VAE` and the **CLIP is SAM's own text
tower** — feed that to `CLIPTextEncode`, not a Qwen or Gemma encoder.

| Knob | Effect |
|---|---|
| `threshold` 0.5 | Confidence floor. Drop to ~0.25 for small or occluded objects, raise to 0.7 to reject lookalikes. |
| `refine_iterations` 2 | Extra SAM decoder passes for tighter edges. 0 is fastest, 4+ rarely pays. |
| `individual_masks` false | `false` = one union mask of all matches. `true` = a mask batch, one per object, for per-object compositing. |

This is the model `video_wan21_scail2_character_replacement` needs, and it also gives you
precise inpaint masks instead of hand-painted ones.

## 2. BiRefNet — automatic subject matting

`14_birefnet_matte.json` · **9–25 s** · samples in `12-segmentation-matting/`

No prompt at all. It finds the salient foreground and returns a clean alpha matte, with
noticeably better hair and edge detail than SAM on the ordinary
"cut the subject off the background" job.

Pick between them like this:

- **BiRefNet** when there is one obvious subject and you want the best edge.
- **SAM 3.1** when the frame has several objects and you need to choose *which*.

BiRefNet works internally around 1024 px. Feeding it a 4K image buys nothing — matte at
1–2 K, then upscale the RGBA result with workflow 09.

## 3. The mask-inversion trap

This cost two wrong renders, so it is worth stating plainly. Three nodes, three different
conventions:

| Node | Convention |
|---|---|
| `SAM3_Detect` → `MASK` | white = **the object** (foreground) |
| `RemoveBackground` → `MASK` | white = **the subject** (foreground — the tooltip says "foreground mask") |
| `JoinImageWithAlpha` | **inverts internally** — `alpha = 1.0 - mask` |
| `ImageCompositeMasked` | does **not** invert — shows `source` where mask = 1 |

So:

```
foreground mask ──> InvertMask ──> JoinImageWithAlpha     # RGBA cutout
foreground mask ─────────────────> ImageCompositeMasked   # composite onto a backdrop
```

Skip the `InvertMask` and you save the **background** and throw the subject away. The
failure is near-invisible, because `JoinImageWithAlpha` only touches the alpha channel —
RGB stays fully intact, so any viewer that ignores alpha shows the complete original
image and everything looks correct.

That is why both workflows also save a **`*_proof_on_magenta`** render: the subject
composited over solid magenta, where a wrong mask is obvious at a glance. Do this whenever
you build a matte graph.

## 4. LTX-2.3 two-stage — the resolution path

`17_ltx23_t2v_upscaled.json` · **21 s** for 1280×704 × 97 frames **with audio** ·
sample in `14-ltx-two-stage-upscale/`

The original `11_ltx23_t2v_audio.json` samples straight at final resolution in one pass.
That is not how LTX-2.3 is meant to run. The official `video_ltx2_3_t2v` template is
**two stages**:

1. Sample the whole clip at **half resolution** (640×352), full sigma schedule.
2. `LTXVLatentUpsampler` doubles the **latent** with the dedicated spatial upscaler.
3. **Re-denoise the upsampled latent at partial strength** — sigmas `0.85, 0.7250, 0.4219, 0.0`.
4. `VAEDecodeTiled` to pixels.

**Step 3 is the whole trick.** The schedule starts at **0.85, not 1.0** — stage 2 refines
structure that already exists rather than generating from noise. Two ways to get this
wrong:

- Decode straight off the upsampler → soft, mushy result. A latent upsample alone is not a
  detail generator.
- Start stage 2 at sigma 1.0 → you discard stage 1 entirely and get a different, worse clip.

Three more things that bite:

- LTX-2.3 is an **audio-video joint** model. The latent carries both. You must
  `LTXVSeparateAVLatent` before upsampling (the upscaler only handles the video half),
  then `LTXVConcatAVLatent` the stage-1 audio latent back on before stage 2. Feed the AV
  latent to the upsampler and it fails on channel count.
- Use `VAEDecodeTiled`, not `VAEDecode`. At 1280×704×97 a plain decode spikes VRAM hard.
  `tile_size=768`, `overlap=64`, and `temporal_size=4096` to effectively **disable**
  temporal tiling — temporal tiles cause visible seams on motion.
- Dimensions must be multiples of 32 at **both** stages. 640×352 → 1280×704 works
  (352 = 11×32). 768×432 does not (432/32 = 13.5).

Both stages share one `CFGGuider` and one sampler. Only the noise seed and the sigma
schedule differ.

## 5. The abliterated Gemma LoRA — an LTX prompt writer

`18_ltx_prompt_enhancer.json` · **10.6 s** · text output, read it from `/history`

This is what the 628 MB abliterated LoRA is for, and it is **not** an image LoRA — it
changes nothing about the picture. It is applied to the **text encoder** so that encoder
will write prompts instead of refusing. Gemma-3-12B is *already resident* as LTX's text
encoder, so chained onto an LTX render this costs no extra VRAM.

`TextGenerateLTX2Prompt` has LTX's house style in its system prompt. Given
`"a brass diving helmet on wet stone at the tide line"` it returned:

> Style: cinematic-realistic with soft lighting. A brass diving helmet rests on wet stone
> at the tide line… Gentle waves lap against the stones—a rhythmic whoosh—and the sound of
> water trickling across the stone surface is heard. The overall soundscape includes a
> gentle breeze and distant cries of seagulls overhead.

Note it wrote **the soundscape**. LTX-2.3 generates audio in the same pass, so its prompt
format covers sound — which an image-prompt LLM never produces. Use
`TextGenerateLTX2Prompt` for video and plain `TextGenerate` for stills; crossing them
gives you a static shot, because an image prompt never mentions motion.

`LoraLoader` needs both a `model` and a `clip`. Only the CLIP output is used here — the
MODEL input exists purely to satisfy the signature, and `strength_clip` is the strength
that matters.

## 6. Local LLM prompt writing

`15_llm_prompt_studio.json`, `16_llm_to_image.json`, `scripts/idea.py` ·
samples in `13-llm-prompt-studio/`

The files in `models/text_encoders/` are real instruct LLMs, not just embedders.
`CLIPLoader` + `TextGenerate` turns any of them into a local chat model — no API, no key,
no rate limit. Qwen3.5-2B writes a full image prompt in **3.0 s**.

`16_llm_to_image.json` chains it straight into Qwen-Image in one graph: **6 s** from a
six-word idea to a finished 1664×928 render. The trick is that node 12's `text` is fed by
a **link** instead of a typed string — any widget input can be driven by a link in API
format, so the LLM's STRING output lands directly in `CLIPTextEncode` with no copy-paste.

```bash
python3 scripts/idea.py "a deep-sea welder repairing a drowned cathedral bell"
python3 scripts/idea.py "a fox librarian closing up" -n 4
python3 scripts/idea.py "brutalist bus shelter in heavy snow" --dry-run   # prompt only
```

The prompt the LLM actually wrote is saved as a `.txt` sidecar next to each image, so good
accidents are reproducible. `-n` re-rolls the **LLM** seed as well as the image seed —
that rewrites the composition, which is a far bigger creative lever than reshuffling noise
on a fixed prompt.

Two gotchas:

- `CLIPLoader` `type` must be `stable_diffusion` for the LLM path. It looks wrong; it is
  what the built-in `llm_*` templates use. The type only selects the tokeniser wrapper.
- `sampling_mode` is a `COMFY_DYNAMICCOMBO_V3`, and the API format for those is not
  documented anywhere obvious. Set `sampling_mode` to `"on"`, then pass the six
  sub-inputs as **dotted sibling keys**:

  ```json
  "sampling_mode": "on",
  "sampling_mode.temperature": 0.85,
  "sampling_mode.top_k": 64,
  "sampling_mode.top_p": 0.95,
  "sampling_mode.min_p": 0.05,
  "sampling_mode.repetition_penalty": 1.05,
  "sampling_mode.seed": 20260729
  ```

  Plain `"temperature"` is rejected with `Required input is missing: sampling_mode.temperature`.
  Use `"off"` for greedy decoding and omit all six.

Keep negative prompts hand-written. Letting an LLM write them makes it enumerate things it
then describes, which drags them into the image.

## 7. Product compositing

`19_product_composite.json` · **31.7 s** · samples in `15-product-composite/`

BiRefNet mattes the product, Qwen-Image generates a fresh backdrop, `ImageCompositeMasked`
drops one onto the other. This is the `product_placement` / `templates-product_scene_relight`
use-case family running entirely on installed weights. Swap one prompt for a new campaign.

Why composite instead of just asking Qwen-Image-Edit to change the background: compositing
keeps the product **pixel-identical**. For a client's actual watch or a real package it must
not be redrawn. Use workflow 03 when you *want* the subject reinterpreted.

**The craft is one sentence:** compositing does not relight the product, so ask for a
backdrop whose light direction matches the subject's. The sample prompt specifies
"a single hard key light from the upper left" because the watch is lit from the upper left.
Get that wrong and the fake reads instantly.

For a contact shadow, run the composite back through workflow 03 at low denoise with
"add a soft contact shadow beneath the watch" — compositing alone leaves the subject
floating.

---

## Measured cost

| Job | Time |
|---|---|
| BiRefNet matte + proof render | 25.5 s |
| SAM 3.1 text-prompted segment + proof render | 18.1 s |
| Qwen3.5-2B writes an image prompt | **3.0 s** |
| Idea → prompt → 1664×928 image, one graph | **6.0 s** warm / 10.5 s cold |
| LTX-2.3 two-stage 1280×704 × 97 f **with audio** | **21.0 s** |
| Gemma-3-12B abliterated writes an LTX prompt | 10.6 s |
| Product matte + backdrop + composite | 31.7 s |

## Corrections to the first pass

- `TEMPLATES.md` marks the whole `video_ltx2_3_*` family and `image_qwen_image_layered`
  as ⬇ "needs a download". LTX-2.3 **was installed** later that same session, so every
  `video_ltx2_3_*` template except the ID/IC-LoRA ones now runs. The ⬇ markers on those
  rows are stale.
- `README.md` claims a sample folder per generation type with a `README.md` index in each.
  The folders exist; only the top-level `README.md` was written. Folders 12–15 from this
  pass each have one.
