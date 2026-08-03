# Everything Claude generated — 2026-07-29

All of it lives in **`~/ComfyUI/output/claude-generated/`** (`Z:\ComfyUI\output\claude-generated\`).
Nothing was written to `output/saltmark/`, to the `output/` root, or to any of your other
folders — every `filename_prefix` in every workflow starts with `claude-generated/`.

First pass: folders `01-` … `11-`. Second pass: folders `12-` … `15-`, about **21 MB**.

> **Second pass** (folders `12-` to `15-`, workflows 13–19) is documented in
> [NEW-CAPABILITIES.md](NEW-CAPABILITIES.md). It downloaded nothing — it wired up four models
> that were already installed and unused, and fixed one that was in a folder ComfyUI does not
> read. See [the second-pass section](#second-pass--folders-12-15) below.
>
> Total GPU cost of the second pass: **under 3 minutes**.

Also created (outside the output dir):

- `~/shared/comfy-studio/` — this whole kit (docs, workflows, scripts)
- `~/ComfyUI/input/claude_start_frame.png`, `pipeline_*.png`, `film_*.png`, `film_clip.mp4` — staged inputs
- `~/ComfyUI/custom_nodes/ComfyUI-Chatterbox/` — the TTS pack
- new weights under `~/ComfyUI/models/` (see [README](README.md#what-was-installed-on-2026-07-29))

---

## The short film

`film-the-last-signal/`

| File | What |
|---|---|
| `the-last-signal_720p_fullmix.mp4` | **the finished film** — 45.6 s, 1280×720, score + wind/surf ambience |
| `the-last-signal_720p.mp4` | same cut, silent |
| `keyframes/*.png` | the 9 Qwen-Image stills, 1664×928 |
| `clips/*.mp4` | the 9 Wan 2.2 clips, 81 frames each |
| `_work/` | normalised segments + title cards used by the ffmpeg edit |

Shot list: [`films/the-last-signal.json`](films/the-last-signal.json). Rebuild with
`python3 scripts/film.py films/the-last-signal.json`.

## Audio

| File | Model | Time |
|---|---|---|
| `score_00001.mp3` | ACE-Step 1.5 Turbo — 60 s orchestral instrumental, D minor, 64 bpm | **7.6 s** |
| `sfx_00001.mp3` | Stable Audio 3 — 30 s wind / dry grass / distant surf | **3.0 s** |
| `sfx_wind50_00001.mp3` | Stable Audio 3 — 50 s of the same, sized to the film | **1.7 s** |
| `narration_00001.mp3` | Chatterbox TTS — 4.8 s of local narration, no API | 55.7 s (incl. one-off model download) |

## Images

| File | What |
|---|---|
| `qwen_turbo_00001_.png` | the lighthouse — 4 steps, 1664×928, 9 s |
| `qwen_turbo_00002–00009_.png` | benchmark sweep: 1024², 1328², 1664×928, 2048×1152, and a batch of 4 |
| `qwen_quality_00001_.png` | the "NORTHWIND SUPPLY CO." sign — 20 steps, text rendering test |
| `qwen_quality_00002–00003_.png` | 20-step benchmark renders |
| `qwen_edit_00001_.png` | the lighthouse re-seasoned to deep winter — Qwen-Image-Edit 2509 |
| `qwen_controlnet_00001_.png` | brutalist tower built on the lighthouse's canny edges — ControlNet Union, 10.5 s |
| `qwen_controlnet_edgemap_00001_.png` | the edge map that drove it |
| `upscaled_4x_00001_.png` | 1664×928 → **6656×3712** (24.7 MP) via RealESRGAN, 4.5 s |

## Video

| File | What |
|---|---|
| `wan22_i2v_00001_.mp4` | first I2V test, 1280×720, 81 f |
| `wan22_i2v_00002–00005_.mp4` | benchmark sweep: 480p/81f, 720p/81f, 720p/121f, 1080p/81f |
| `interp32_00001_.mp4` | the beacon shot at **32 fps** — FILM interpolation, 81→161 frames, 7.5 s |
| `ltx23_av_00001_.mp4` | **LTX-2.3 text→video with generated audio** — rain on a metal roof, 768×512, 13.5 s |
| `ltx23_av_00002_.mp4` | same at 1280×704 — **16.5 s** (Wan needs 129 s for comparable output, with no audio) |
| `ltx23_av_00003_.mp4` | same at 193 frames / **8 s** of video — 13.7 s, i.e. barely more than the 4 s clip |

---

## Second pass — folders 12-15

| Folder | Files | What |
|---|---|---|
| `12-segmentation-matting/` | 6 | **SAM 3.1** cut a watch out from the text prompt `"the wristwatch"` alone; **BiRefNet** cut a figure out with no prompt at all. Each has a `*_proof_on_magenta` render, because a wrong alpha channel is invisible in a normal image viewer. |
| `13-llm-prompt-studio/` | 4 images + 4 `.txt` | **Qwen3.5-2B writes the prompt locally**, Qwen-Image renders it, one graph, ~6 s end to end. Every image has a sidecar with the exact prompt and both seeds. |
| `14-ltx-two-stage-upscale/` | 1 | **LTX-2.3 run the way it was designed** — half-res sample, 2× latent upsample, partial re-denoise. 1280×704, 97 frames, generated stereo audio, **21 s**. |
| `15-product-composite/` | 2 | BiRefNet matte + generated backdrop + composite: a product ad where the product stays pixel-identical. |

Each folder has its own `README.md` describing every file — including what is **wrong** with
two of them (`idea_00003_` has an astronaut eating noodles through a sealed visor; the product
composite has no contact shadow) and why they were kept anyway.

Also created or changed outside the output dir:

- `NEW-CAPABILITIES.md` — the second-pass writeup, including the mask-inversion trap and the
  `COMFY_DYNAMICCOMBO_V3` API format, which are the two things that cost the most time
- `workflows/13_…json` … `19_…json` — seven new workflows, each with its own `_notes`
- `scripts/idea.py` — one line in, art-directed image out
- `~/ComfyUI/models/checkpoints/sam3.1_multiplex_fp16.safetensors` — a **symlink** to the copy
  already in `models/detection/`, which is where it was downloaded and where
  `CheckpointLoaderSimple` could not see it. No second copy of the 1.7 GB file.
- `~/ComfyUI/input/claude_seg_product.png`, `claude_seg_portrait.png` — staged inputs
- corrections to `README.md` and `TEMPLATES.md`: the LTX-2.3 and ACE-Step/Stable-Audio rows
  were still marked ⬇ "needs a download" after those models had been installed

| Job | GPU time |
|---|---|
| BiRefNet matte + proof render | 25.5 s |
| SAM 3.1 text-prompted segment + proof render | 18.1 s |
| Qwen3.5-2B writes an image prompt | **3.0 s** |
| Idea → prompt → 1664×928 image | **6.0 s** warm |
| LTX-2.3 two-stage 1280×704 × 97 f with audio | **21.0 s** |
| Gemma-3-12B abliterated writes an LTX prompt | 10.6 s |
| Product matte + backdrop + composite | 31.7 s |
| **Whole second pass** | **under 3 minutes of GPU time** |

## Measured cost of the whole session

| Job | GPU time |
|---|---|
| 9 film keyframes | 45 s |
| 9 film clips @ 720p | 19 min 36 s |
| Film score (60 s of music) | 7.6 s |
| Narration | ~5 s (after model download) |
| Editing (ffmpeg, CPU) | ~20 s |
| **Finished 45.6 s scored short film** | **≈ 21 minutes** |
| Full benchmark suite (12 renders) | ~22 min |

## A mistake worth keeping

The first version of the upscale workflow chained a 4× GAN upscale onto 161 interpolated
frames: 5120×2880 × 161 frames in float32 ≈ **28 GB**, which OOM-killed the ComfyUI
server. `ImageUpscaleWithModel` processes the entire frame batch at once — it has no
internal chunking. Video upscaling has to be done in small frame batches, or with
SeedVR2 which is built for it. The split workflows
([`07_video_interpolate.json`](workflows/07_video_interpolate.json) and
[`09_image_upscale.json`](workflows/09_image_upscale.json)) reflect that.
