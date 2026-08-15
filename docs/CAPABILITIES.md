# What the 5090 can actually do

All timings below were **measured on your box on 2026-07-29**, not estimated.
Method: submit via the ComfyUI HTTP API, wall-clock from submit to history-complete,
models already resident in VRAM (see "Cold vs warm" for the first-run penalty).

## The hardware

| | |
|---|---|
| GPU | RTX 5090 — 32 GB GDDR7, Blackwell, 480 W |
| Observed under load | **479.5 W, 100 % util, 63 °C** — thermally fine, no throttling seen |
| Usable VRAM | ~30.5 GB (server started with `--reserve-vram 1.5`) |
| Host | 16 threads, 60 GB RAM, 1.7 TB free NVMe |

32 GB is the number that matters. It means a 19 GB fp8 DiT plus an 8.7 GB text encoder
plus VAE fit **simultaneously**, so there's no encoder/DiT swap thrash between steps.
Wan 2.2's two-expert setup (13.3 GB high-noise + 13.3 GB low-noise) also co-resides.
On a 24 GB card both of those cases spill to system RAM and roughly double.

## Measured throughput

### Qwen-Image 2512 + Lightning 4-step LoRA (cfg 1.0)

| Resolution | Time | Notes |
|---|---|---|
| 1024×1024 | 7.5 s | first call after model swap — includes warm-up |
| 1328×1328 | **4.5 s** | steady state |
| 1664×928 (16:9) | **4.5 s** | steady state |
| 2048×1152 | 6.0 s | above native training res; still coherent |
| 1328×1328 × batch 4 | 15.0 s | **3.75 s/image** — batching wins ~20 % |

### Qwen-Image 2512 full quality (20 steps, cfg 2.5, no LoRA)

| Resolution | Time |
|---|---|
| 1664×928 | 30.0 s |
| 1328×1328 | 36.0 s |

So: **~7× the cost for the last 10–15 % of quality.** Draft with the 4-step LoRA, final
with 20 steps. The 4-step output is genuinely good — the lighthouse image in
`output/claude-generated/qwen_turbo_00001_.png` is 4 steps, 9 s cold.

### Qwen-Image-Edit 2509 (20 steps, cfg 4.0)

| Op | Time |
|---|---|
| 1664×928 instruction edit | 48.0 s |

This is slow **only because you have no Lightning LoRA for the edit model**. Installing
Qwen-Image-Edit 2511 + its 4-step LoRA takes this to roughly 6 s. Highest-value upgrade
on the list after audio.

### Wan 2.2 I2V 14B + lightx2v 4-step (2-stage high/low expert, cfg 1.0)

| Output | Time | Real-time ratio | s per output-second |
|---|---|---|---|
| 832×480, 81 f (5.1 s @16fps) | **36.0 s** | 7× | 7.1 |
| 1280×720, 81 f (5.1 s) | **129.1 s** | 25× | 25.5 |
| 1280×720, 121 f (7.6 s) | **253.4 s** | 33× | 33.5 |
| 1920×1088, 81 f (5.1 s) | **555.5 s** | 109× | 109.7 |

Two things fall out of this table:

1. **Cost scales worse than pixel count.** 720p is 2.3× the pixels of 480p but 3.6× the
   time. 1080p is 2.25× the pixels of 720p but **4.3×** the time. Attention over the
   spatio-temporal token grid is quadratic; you feel it hard above 720p.
2. **Longer clips cost more per frame, not less.** 121 f is 1.5× the frames of 81 f but
   1.96× the time. Two 81 f clips cut together are cheaper *and* faster than one 121 f clip.

Practical read: **480p is your iteration resolution** (36 s a shot — you can explore
freely), **720p is your delivery resolution** (~2 min a shot). **1080p is a hero-shot-only
resolution** — 9¼ minutes for 5 seconds. Generate at 720p and upscale with SeedVR2
instead; it will be faster and probably look better.

A 10-shot 720p sequence is ~22 minutes of GPU time — a coffee break, not an overnight.

### LTX-2.3 22B + distilled LoRA, 8 steps — video **and audio** in one pass

| Output | Time | Real-time ratio |
|---|---|---|
| 768×512, 97 f (4.0 s @24fps) + audio | **13.5 s** | 3.3× |
| 1280×704, 97 f (4.0 s) + audio | **16.5 s** | 4.1× |
| 768×512, 193 f (8.0 s) + audio | **13.7 s** | 1.7× |

**This is the headline result of the whole session.** Compare like for like at 720p:

| | Wan 2.2 I2V | LTX-2.3 |
|---|---|---|
| 720p, ~4–5 s of video | 129 s | **16.5 s** |
| Audio | none | **generated in the same pass** |
| Speedup | — | **~8×** |

And LTX barely notices longer clips — 193 frames cost the same as 97 (13.7 s vs 13.5 s),
where Wan's cost grew *faster* than linearly. If you want length, LTX is not close to
competitive, it's a different category.

Caveats, honestly:

- Requested 1280×**720** came back as 1280×**704** — LTX snaps height to its own grid.
- `length` must be 8n+1 (97, 193), not Wan's 4n+1.
- Audio comes out quiet (mean −35 dBFS). Normalise it: `ffmpeg -i in.mp4 -af loudnorm -c:v copy out.mp4`.
- The 22 GB fp8 checkpoint plus the 9.4 GB Gemma-3-12B encoder exceed 32 GB, so ComfyUI
  offloads between stages. It's still this fast anyway.
- Wan still wins on **image-to-video fidelity** — if you have an exact keyframe you want
  animated faithfully, Wan holds it better. LTX is the better text-to-video engine.

### Cold vs warm

First call after a model family swap costs the load: **~90 s extra for Wan** (26.6 GB of
weights off NVMe), ~25 s for Qwen. Chain same-model jobs together; don't alternate
image/video jobs if you care about throughput.

## What you can make **today**, with zero downloads

| Capability | How | Cost |
|---|---|---|
| Text → image, up to 2K | `workflows/01` (fast) or `02` (quality) | 4.5–36 s |
| **Text rendered correctly inside images** | Qwen 2512, its standout skill | as above |
| Instruction editing: relight, reseason, replace objects, restyle | `workflows/03` | 48 s |
| Multi-reference editing (up to 3 input images) | `workflows/03`, add `image2`/`image3` | 48 s |
| Structural control (canny/depth/pose → image) | `workflows/05` + ControlNet Union | ~6 s |
| Image → video, 480p–1080p, up to ~7.6 s | `workflows/04` | 36 s – 5 min |
| **Text → video + audio together** | `workflows/11` (LTX-2.3) | **13–17 s** |
| **Text → music / full songs** | `workflows/06` (ACE-Step 1.5) | 7.6 s per 60 s |
| **Text → SFX / ambience** | `workflows/10` (Stable Audio 3) | 1.7–3 s |
| **Local narration + voice cloning** | `workflows/08` (Chatterbox) | ~5 s |
| 4× upscale, 1664×928 → 6656×3712 | `workflows/09` | 4.5 s |
| 16 → 32 fps interpolation | `workflows/07` | 7.5 s per clip |
| Prompt → image → video, one command | `scripts/pipeline.py` | ~2.5 min |
| Shot list → scored short film | `scripts/film.py` + `mixdown.sh` | ~21 min for 45 s |
| Batch/sweep anything | `-s` overrides + a shell loop | — |

## What you **cannot** make today

Not a hardware limit — a weights limit. Every one of these has working nodes installed.

Everything below is a **weights** gap, not a hardware one — the nodes are all installed.
(The audio, upscaling, interpolation, segmentation and LTX rows were closed on
2026-07-29; what remains is listed here.)

| Missing | Blocked by | Fix |
|---|---|---|
| Wan-quality text→video (as opposed to LTX) | no Wan 2.2 **T2V** weights | ~30 GB |
| Fast ideation model (~1 s per image) | no Z-Image Turbo | ~11 GB |
| Diffusion upscaling for video | no SeedVR2 | ~4 GB |
| Depth / pose maps to feed your ControlNet | no DA3 / SDPose | ~2 GB |
| 3D meshes or Gaussian splats | no Hunyuan3D / TripoSplat | ~7 GB |
| 4-step Qwen **editing** (you're stuck at 20 steps / 48 s) | no Edit-2511 + Lightning | ~21 GB |
| Style variety (anime, painterly, photoreal-not-Qwen) | single image model | 9–14 GB each |

## Headroom you're not using

1. **`--reserve-vram 1.5` is conservative.** You have a desktop session eating ~550 MB.
   If you run headless (or stop the GNOME session during batch jobs) you get another
   ~2 GB of usable VRAM, which is the difference between 1080p Wan fitting cleanly or not.
2. **fp8 is not your only option.** With 32 GB you can run **bf16** Qwen-Image (~40 GB —
   no, too big) but you *can* run bf16 for the smaller models (Z-Image 6 GB, Flux Klein
   4B) with zero quantisation loss.
3. **`weight_dtype: fp8_e4m3fn_fast`** on `UNETLoader` enables Blackwell's fp8 tensor
   cores. Worth A/B-ing on Qwen — typically 10–20 % faster with negligible quality delta.
4. **Batching.** 4-up at 1328² costs 3.75 s/image vs 4.5 s. On 32 GB you can push batch 8
   at 1024². Use it for variation sweeps.
5. **Nothing else is competing.** The box is otherwise idle. Queue depth is free —
   submit 50 jobs and walk away.
