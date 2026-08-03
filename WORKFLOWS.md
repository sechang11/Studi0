# The workflows in this kit

These are **API-format** JSON (flat `{"node_id": {"class_type", "inputs"}}`), not UI
format. That makes them scriptable. They are *not* drag-and-droppable into the ComfyUI
canvas — for canvas work use the built-in templates (see [TEMPLATES.md](TEMPLATES.md)),
and use these for batch, sweeps and automation.

Keys starting with `_` (like `_comment`) are stripped before submit, so the files can
document themselves.

> This page covers **01–12**. Workflows **13–19** (SAM 3.1 segmentation, BiRefNet matting,
> local LLM prompt writing, LTX-2.3 two-stage upscale, the abliterated Gemma prompt writer,
> and product compositing) are documented in
> **[NEW-CAPABILITIES.md](NEW-CAPABILITIES.md)** instead, which also covers two API details
> that are not obvious anywhere else: the mask-inversion convention and the
> `COMFY_DYNAMICCOMBO_V3` dotted-key format.

| File | Model | Typical cost |
|---|---|---|
| `01_qwen_t2i_turbo.json` | Qwen-Image 2512 + Lightning 4-step | 4.5 s @ 1664×928 |
| `02_qwen_t2i_quality.json` | Qwen-Image 2512, 20 steps | 30–36 s |
| `03_qwen_image_edit.json` | Qwen-Image-Edit 2509 | 48 s |
| `04_wan22_i2v_turbo.json` | Wan 2.2 I2V 14B + lightx2v | 36 s @480p, 129 s @720p |
| `05_qwen_controlnet.json` | Qwen 2512 + InstantX ControlNet Union | ~6 s |

## Driving them

```bash
cd ~/shared/comfy-studio && python3 scripts/comfy.py run workflows/01_qwen_t2i_turbo.json
```

Override any input with `-s <node>.inputs.<field>=<value>`:

```bash
python3 scripts/comfy.py run workflows/01_qwen_t2i_turbo.json -s 10.inputs.text="a brass orrery on a walnut desk" -s 12.inputs.width=1328 -s 12.inputs.height=1328 -s 13.inputs.seed=99
```

Other subcommands:

```bash
python3 scripts/comfy.py stats
```

```bash
python3 scripts/comfy.py models
```

```bash
python3 scripts/comfy.py nodes wan
```

## Node map (shared across 01/02/05)

| ID | Node | Knob that matters |
|---|---|---|
| 1 | `UNETLoader` | `weight_dtype` — try `fp8_e4m3fn_fast` on Blackwell |
| 2 | `CLIPLoader` | qwen2.5-vl-7b, `type: qwen_image` |
| 3 | `VAELoader` | qwen_image_vae |
| 4 | `LoraLoaderModelOnly` | Lightning 4-step, `strength_model` 1.0 |
| 5 | `ModelSamplingAuraFlow` | `shift` 3.1 — raise toward 4–5 for more global structure |
| 6 | `CFGNorm` | leave at 1.0 |
| 10 / 11 | `CLIPTextEncode` | positive / negative |
| 12 | `EmptySD3LatentImage` | width / height / batch_size |
| 13 | `KSampler` | seed, steps, cfg |
| 15 | `SaveImage` | `filename_prefix` |

**Rule: Lightning LoRA ⇒ `steps: 4, cfg: 1.0`.** Raising cfg above ~1.5 with a
distilled LoRA burns the image. If you want higher cfg, remove the LoRA (rewire node 5's
`model` to `["1", 0]`) and go to 20 steps.

Qwen native resolutions — stay on these unless you have a reason:

```
1:1  1328x1328   16:9 1664x928   9:16 928x1664
4:3  1472x1104   3:4  1104x1472
3:2  1584x1056   2:3  1056x1584
```

## Wan 2.2 I2V (04) — the two-expert structure

Wan 2.2 is a mixture-of-experts across the noise schedule. Two full 13.3 GB models:

- **high-noise expert** handles steps 0→2 (composition, large motion)
- **low-noise expert** handles steps 2→4 (detail, texture)

Hence two `UNETLoader`s, two LoRAs, and two `KSamplerAdvanced` nodes:

| ID | Node | Setting |
|---|---|---|
| 14 | `KSamplerAdvanced` (high) | `add_noise: enable`, `start_at_step 0`, `end_at_step 2`, `return_with_leftover_noise: enable` |
| 15 | `KSamplerAdvanced` (low) | `add_noise: disable`, `start_at_step 2`, `end_at_step 4`, `return_with_leftover_noise: disable` |

If you change `steps`, change it on **both** and keep the split at the midpoint.

Other knobs:

- Node 7/8 `ModelSamplingSD3.shift` = 8.0. Drop to 5.0 for calmer, more literal motion;
  raise toward 10 for more dramatic movement (and more risk of morphing).
- Node 13 `length` must be **4n+1** (81 = 5.06 s at 16 fps, 121 = 7.6 s). Non-conforming
  values get silently rounded and can cause a stutter on the last frames.
- VAE is `wan_2.1_vae.safetensors` — **not** wan2.2. The 14 B I2V models use the 2.1 VAE;
  `wan2.2_vae` belongs to the 5 B TI2V model you don't have. Getting this wrong produces
  colour-shifted mush.

## The one-command pipeline

```bash
cd ~/shared/comfy-studio && python3 scripts/pipeline.py "a derelict space station drifting over a gas giant" --motion "slow orbital drift, debris tumbling, light sweeping across the hull"
```

Prompt → keyframe → 5 s 720p clip, into `output/claude-generated/<slug>/`. Flags:
`--ar`, `--seconds`, `--res 480|720|1080`, `--seed`, `--still`, `--steps`.

Use `--res 480` while you're finding the shot, then re-run with the same `--seed` at
`--res 720` for the take.

## Batch patterns

**Seed sweep** — same prompt, 8 variations:

```bash
for s in $(seq 1 8); do python3 scripts/comfy.py run workflows/01_qwen_t2i_turbo.json -s 13.inputs.seed=$s -s 15.inputs.filename_prefix="claude-generated/sweep/v"; done
```

**Prompt list from a file** — one prompt per line:

```bash
while IFS= read -r p; do python3 scripts/comfy.py run workflows/01_qwen_t2i_turbo.json -s 10.inputs.text="$p"; done < prompts.txt
```

**Shot list → clips** — this is how you build a sequence:

```bash
while IFS='|' read -r shot motion; do python3 scripts/pipeline.py "$shot" --motion "$motion" --res 480; done < shots.txt
```

with `shots.txt` lines like `wide establishing of the harbour at dawn|slow crane up, gulls crossing frame`.

## Extending

**Once you install the utility bundle**, append to any image workflow:

```json
"30": { "class_type": "UpscaleModelLoader", "inputs": { "model_name": "RealESRGAN_x4plus.safetensors" } },
"31": { "class_type": "ImageUpscaleWithModel", "inputs": { "upscale_model": ["30",0], "image": ["14",0] } },
"32": { "class_type": "SaveImage", "inputs": { "images": ["31",0], "filename_prefix": "claude-generated/upscaled" } }
```

and to any video workflow, between `VAEDecode` (16) and `CreateVideo` (17):

```json
"40": { "class_type": "FrameInterpolationModelLoader", "inputs": { "model_name": "film_net_fp16.safetensors" } },
"41": { "class_type": "FrameInterpolate", "inputs": { "model": ["40",0], "images": ["16",0], "multiplier": 2 } }
```

then point node 17 at `["41", 0]` and set `fps: 32`. Same clip, twice as smooth.
