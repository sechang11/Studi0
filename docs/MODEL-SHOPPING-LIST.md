# Model shopping list

> **Everything on this list is free.** These are open-weight models hosted on Hugging
> Face; you download them, you don't buy them. "Cost" here always means download size and
> disk, never money. No account, licence key or payment is needed for anything below —
> `scripts/fetch-models.sh` just pulls files over HTTPS.
>
> The only paid things in ComfyUI are the **cloud API nodes** (Seedream, Kling,
> ElevenLabs, Runway, Topaz, Nano Banana…), which call someone else's servers and need
> API credits. This kit uses none of them — everything runs on your 5090.

Every URL here was extracted from the **workflow templates shipped with your installed
ComfyUI 0.28.0** (`comfyui_workflow_templates` 0.11.17), so they match the node code on
the box. Nothing is guessed.

Download helper: `scripts/fetch-models.sh` — run a tier by name, e.g.

```bash
bash ~/shared/comfy-studio/scripts/fetch-models.sh tier1
```

Disk is not a constraint: **1.7 TB free**. Only your bandwidth and patience are.

---

> **Status 2026-07-29:** Tier 1's utility bundle and audio, plus Stable Audio 3 and
> LTX-2.3, are **installed and verified**. What's left worth downloading is at the bottom
> under [Still outstanding](#still-outstanding). The tier descriptions below are kept
> as reference for what each thing does.

## What you have now

| Family | Files | What it gives you |
|---|---|---|
| Qwen-Image 2512 (fp8) | 19 GB + Lightning 4-step LoRA | text→image, best-in-class text rendering |
| Qwen-Image-Edit 2509 (fp8) | 19 GB | instruction-driven image editing |
| Qwen InstantX ControlNet Union | 3.3 GB | canny/depth/pose control for Qwen |
| Wan 2.2 I2V 14B (fp8, high+low) | 26.6 GB + lightx2v 4-step LoRAs | image→video |
| Text encoders | qwen2.5-vl-7b, umt5-xxl | shared |
| VAEs | qwen_image, wan2.1, wan2.2 | shared |

**Total: ~90 GB. Three capabilities: T2I, image edit, I2V.**

## What you are missing

Audio. Text-to-video. 3D. Upscaling. Frame interpolation. Background removal.
Depth/pose/segmentation preprocessors. Any second image model for style diversity.

The nodes for all of it are already installed — 819 node types. Only weights are missing.

---

## Tier 1 — biggest capability-per-GB (~46 GB)

These four unlock entire content categories you currently cannot touch at all.

### Audio: ACE-Step 1.5 Turbo — text→music with vocals (~10 GB)

The headline gap. Full songs with lyrics, or instrumentals, in seconds on a 5090.

```
split_files/diffusion_models/acestep_v1.5_turbo.safetensors   -> models/diffusion_models/
split_files/text_encoders/qwen_1.7b_ace15.safetensors         -> models/text_encoders/
split_files/text_encoders/qwen_0.6b_ace15.safetensors         -> models/text_encoders/
split_files/vae/ace_1.5_vae.safetensors                       -> models/vae/
```
Base: `https://huggingface.co/Comfy-Org/ace_step_1.5_ComfyUI_files/resolve/main/`

Templates: **ACE-Step 1.5 Music Generation Workflow**, **ACE-Step 1.5 AI Lyric Song Generation**.
There is also a single-file AIO checkpoint if you prefer one blob:
`checkpoints/ace_step_1.5_turbo_aio.safetensors`.

### Video: Wan 2.2 **T2V** 14B — text→video, no start image needed (~30 GB)

You have I2V only. T2V is the other half, and it reuses your existing umt5 encoder and
wan_2.1 VAE, so it is just the two DiTs plus two small LoRAs.

```
diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors   14.3 GB
diffusion_models/wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors    14.3 GB
loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors
loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors
```
Base: `https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/`

### Utility bundle — upscale, interpolate, cut out (~1.5 GB, huge quality lift)

Cheap, small, and they improve *everything else you already make*.

| File | Size | Dest | Use |
|---|---|---|---|
| `RealESRGAN_x4plus.safetensors` | 64 MB | `models/upscale_models/` | 4× GAN upscale, images + video |
| `film_net_fp16.safetensors` | ~70 MB | `models/frame_interpolation/` | 16 fps → 32/64 fps, smooth slow-mo |
| `birefnet.safetensors` | ~900 MB | `models/background_removal/` | clean alpha cutouts |
| `sam3.1_multiplex_fp16.safetensors` | ~450 MB | `models/detection/` | prompt-driven segmentation, image + video |

- `https://huggingface.co/Comfy-Org/Real-ESRGAN_repackaged/resolve/main/RealESRGAN_x4plus.safetensors`
- `https://huggingface.co/Comfy-Org/frame_interpolation/resolve/main/frame_interpolation/film_net_fp16.safetensors`
- `https://huggingface.co/Comfy-Org/BiRefNet/resolve/main/background_removal/birefnet.safetensors`
- `https://huggingface.co/Comfy-Org/sam3.1/resolve/main/checkpoints/sam3.1_multiplex_fp16.safetensors`

### Qwen-Image-Edit **2511** + its Lightning LoRA (~21 GB, or 1.6 GB for just the LoRA)

You are on the older 2509 edit model with **no** Lightning LoRA, so every edit costs
20 steps (~48 s). Two options:

- **Cheap**: there is no 2509 Lightning LoRA in the current template set — the shipped
  one targets 2511. So to get 4-step editing you need the 2511 model too.
- **Full**: `qwen_image_edit_2511_fp8mixed.safetensors` (~20 GB) +
  `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` (~1.6 GB).
  Drops edits from 48 s to roughly 6 s and 2511 is a materially better edit model.

- `https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors`
- `https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning/resolve/main/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors`

---

## Tier 2 — speed and variety (~30 GB)

### Z-Image Turbo — a 6 GB image model that generates in ~1–2 s (~11 GB total)

Qwen 2512 is 19 GB and excellent but heavy. Z-Image Turbo is the ideation model:
fire off 40 concepts, pick one, re-render it in Qwen. It ships its own small
Qwen-3 4B text encoder and a Flux-style VAE.

```
split_files/diffusion_models/z_image_turbo_bf16.safetensors   -> models/diffusion_models/
split_files/text_encoders/qwen_3_4b.safetensors               -> models/text_encoders/
split_files/vae/ae.safetensors                                -> models/vae/  (rename: flux_ae.safetensors)
```
Base: `https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/`

Bonus: there is a **Z-Image-Turbo Fun Union ControlNet** template and a
**Z-Image-Turbo 2K upscaler** template, so this one model covers three workflows.

### Flux.2 Klein 4B — different aesthetic, shares Z-Image's text encoder (~9 GB)

If you grab Z-Image first, Klein only costs the DiT plus the Flux2 VAE, because it
reuses the same `qwen_3_4b.safetensors`.

```
split_files/diffusion_models/flux-2-klein-4b.safetensors   (Comfy-Org/flux2-klein)
split_files/vae/flux2-vae.safetensors                      (Comfy-Org/flux2-dev)
```

### SeedVR2 3B — diffusion upscaler for image *and video* (~4 GB)

Far better than GAN upscaling for restoring AI video. This is what turns your 720p
Wan clips into something that holds up at 1440p+.

- `https://huggingface.co/Comfy-Org/SeedVR2/resolve/main/diffusion_models/seedvr2_3b_int8_convrot.safetensors`
- `https://huggingface.co/Comfy-Org/SeedVR2/resolve/main/vae/seedvr2_ema_vae_fp16.safetensors`

### Depth Anything 3 + SDPose — control signal generators (~2 GB)

Feeds your existing Qwen ControlNet Union. Without these, ControlNet is limited to
canny edges you compute by hand.

- `https://huggingface.co/Comfy-Org/Depth-Anything-3/resolve/main/geometry_estimation/depth_anything_3_mono_large.safetensors`
- `https://huggingface.co/Comfy-Org/SDPose/resolve/main/checkpoints/sdpose_wholebody_fp16.safetensors`

---

## Tier 3 — specialist (~60 GB)

| Want | Get | Size | Notes |
|---|---|---|---|
| Native audio+video together | **LTX-2.3 22B fp8** + Gemma-3-12B encoder + spatial upscaler | ~45 GB | The only local model that generates synced audio *with* video. Heaviest thing here; fits in 32 GB but tight. |
| Image → 3D mesh | **Hunyuan3D 2.1** | ~7 GB | `Comfy-Org/hunyuan3D_2.1_repackaged/hunyuan_3d_v2.1.safetensors`. Pairs with `Load3D` / `VAEDecodeHunyuan3D`. |
| Swap a character into existing footage | **SCAIL-2** (Wan 2.1 14B) + clip_vision_h | ~18 GB | Needs SAM 3.1 from Tier 1. |
| Uncensored / artistic base model | **Chroma1-HD fp8mixed** + t5xxl_fp8 | ~14 GB | Different aesthetic space from Qwen entirely. |
| Prompt expansion on-box | **Qwen3.5 / Qwen3-VL text gen** | 2–8 GB | Local LLM node to turn one line into a full cinematic prompt. |

---

## Still outstanding

Ordered by what would actually change your day, given what's now installed.

| # | Get | Size | Why it matters *now* |
|---|---|---|---|
| 1 | **Z-Image Turbo** | ~11 GB | ~1–2 s per image. Qwen at 4.5 s is fine; Z-Image at 1.5 s changes ideation from "generate and wait" to "scrub through options". `bash scripts/fetch-models.sh zimage` |
| 2 | **Qwen-Image-Edit 2511 + Lightning** | ~21 GB | Your edits cost **48 s** because there is no Lightning LoRA for the 2509 model you have. This drops them to ~6 s and 2511 is a better edit model. `fetch-models.sh edit2511` |
| 3 | **SeedVR2 3B** | ~4 GB | Diffusion upscaling for video. Renders at 720p → delivers at 1440p, cheaper and better than native 1080p (which costs 4.3× for 2.25× the pixels). `fetch-models.sh seedvr` |
| 4 | **Depth Anything 3 + SDPose** | ~2 GB | You own a ControlNet Union but can only feed it hand-rolled canny edges. These generate the depth and pose maps it actually wants. `fetch-models.sh control` |
| 5 | **Wan 2.2 T2V** | ~30 GB | Lower priority than it looked: LTX-2.3 already does text→video, ~8× faster, with audio. Get this only if you specifically want Wan's motion character. `fetch-models.sh t2v` |
| 6 | **Hunyuan3D 2.1** | ~7 GB | Image → textured mesh. Genuinely useful for your `saltmark` game assets. `fetch-models.sh hunyuan3d` |

Items 1–4 total **~38 GB** and address every remaining friction point in the current
setup. Item 5 is now optional. Disk remains a non-issue: 1.7 TB free.
