# Comfy Studio — RTX 5090 generation guide

Everything here targets **k4shix** (`192.168.1.46`, Fedora 44, RTX 5090 32 GB).
Written and verified by Claude on 2026-07-29 against the live box.

| | |
|---|---|
| ComfyUI | 0.28.0, frontend 1.47.10, templates 0.11.17 |
| Python / Torch | 3.14.6 / 2.13.0+cu130 |
| GPU | RTX 5090, 32 GB GDDR7, 480 W cap, driver 610.43.03 (CUDA 13.3) |
| CPU / RAM | 16 threads / 60 GB + 7 GB swap |
| Disk | 1.9 TB NVMe, **1.7 TB free** |
| Server | `main.py --listen 0.0.0.0 --port 8188 --reserve-vram 1.5` |
| Web UI | http://192.168.1.46:8188 (reachable from your Windows box) |
| Custom nodes | ComfyUI-Manager only — everything else is stock |

## Where things live

| Path (Linux) | Path (Windows) | What |
|---|---|---|
| `~/shared/comfy-studio/` | `Z:\shared\comfy-studio\` | this kit |
| `~/ComfyUI/models/` | `Z:\ComfyUI\models\` | weights |
| `~/ComfyUI/output/claude-generated/` | `Z:\ComfyUI\output\claude-generated\` | **everything Claude generated** |
| `~/ComfyUI/output/saltmark/` | `Z:\ComfyUI\output\saltmark\` | your existing project — untouched |

> All content I generated goes in `output/claude-generated/` and nowhere else.

## Start here

**Open the gallery: `Z:\ComfyUI\output\claude-generated\gallery.html`**

One self-contained page, every sample as a thumbnail, grouped by capability, with the exact
prompt under each. Click anything for full size. This is the browse-and-get-ideas view;
everything below is reference. Rebuild it after generating more:

```bash
cd ~/shared/comfy-studio && ~/ComfyUI/venv/bin/python scripts/gallery.py
```

## Read next

00. **[AI-CONTENT-MAP.md](AI-CONTENT-MAP.md)** — **the whole picture.** Every content type AI
    can generate, and whether you can do it today, with one download, or not at all. Start
    here when you want to know if an idea is feasible.
0a. **[FILM-CRAFT-AUDIT.md](FILM-CRAFT-AUDIT.md)** — **craft → capability → model.** Six
    specialists audited one film discipline each against the live box: story, cinematography,
    editing, sound, character/continuity, colour. For each: what executes today, what is blocked
    and by exactly what, ranked next actions. The headline — **five models are installed and
    unreachable from the kit**, and the top action in five of six disciplines costs 0 GB.
    Read alongside [FILMMAKING.md](FILMMAKING.md), which teaches the pipeline this audits.
0b. **[LORAS.md](LORAS.md)** — the art-direction layer. What your five LoRAs actually are
    (all technical — you have **no** style LoRAs), how strength and stacking work, a verified
    shopping list, and how to train your own on this box.
0. **[NEW-CAPABILITIES.md](NEW-CAPABILITIES.md)** — *second pass, same day.* Four installed
   models that were doing nothing, now wired up: SAM 3.1 segmentation, BiRefNet matting, the
   LTX-2.3 two-stage latent upscaler, and the abliterated Gemma prompt writer. Also the
   mask-inversion trap and the ComfyUI API gotchas that cost the most time.
1. **[CAPABILITIES.md](CAPABILITIES.md)** — what the 5090 can actually do, with measured timings.
2. **[MODEL-SHOPPING-LIST.md](MODEL-SHOPPING-LIST.md)** — the gaps, and exactly what to download to close them.
3. **[TEMPLATES.md](TEMPLATES.md)** — the newest built-in templates worth your time.
4. **[WORKFLOWS.md](WORKFLOWS.md)** — the workflows in `workflows/`, and how to drive them.
5. **[PROMPTING.md](PROMPTING.md)** — model-specific prompting that actually moves the needle.
6. **[FILMMAKING.md](FILMMAKING.md)** — stringing shots into an actual short film.
7. **[AUDIO.md](AUDIO.md)** — music, sound effects, and voice.

## Workflows

| File | Model | Cost |
|---|---|---|
| `01_qwen_t2i_turbo.json` | Qwen-Image 2512 + Lightning | 4.5 s @ 1664×928 |
| `02_qwen_t2i_quality.json` | Qwen-Image 2512, 20 steps | 30–36 s |
| `03_qwen_image_edit.json` | Qwen-Image-Edit 2509 | 48 s |
| `04_wan22_i2v_turbo.json` | Wan 2.2 I2V 14B | 36 s @480p / 129 s @720p |
| `05_qwen_controlnet.json` | Qwen + ControlNet Union | 10.5 s |
| `06_acestep_music.json` | ACE-Step 1.5 — music/songs | 7.6 s per 60 s |
| `07_video_interpolate.json` | FILM 16→32 fps | 7.5 s per clip |
| `08_chatterbox_tts.json` | Chatterbox — narration | ~5 s |
| `09_image_upscale.json` | RealESRGAN 4× | 4.5 s |
| `10_stableaudio_sfx.json` | Stable Audio 3 — SFX/ambience | 1.7–3 s |
| `11_ltx23_t2v_audio.json` | **LTX-2.3 — text → video + audio** | **13–17 s** |
| `12_ltx23_i2v_audio.json` | LTX-2.3 — image → video + audio | ~15 s |
| `13_sam3_segment.json` | **SAM 3.1 — text-prompted segmentation** | 12–18 s |
| `14_birefnet_matte.json` | **BiRefNet — automatic subject matting** | 9–25 s |
| `15_llm_prompt_studio.json` | Qwen3.5-2B writes an image prompt, locally | **3 s** |
| `16_llm_to_image.json` | **idea → prompt → image in one graph** | **6 s** |
| `17_ltx23_t2v_upscaled.json` | **LTX-2.3 two-stage, 1280×704 + audio** | **21 s** |
| `18_ltx_prompt_enhancer.json` | Gemma-3-12B abliterated writes an LTX prompt | 10.6 s |
| `19_product_composite.json` | **matte + generated backdrop → product ad** | 31.7 s |
| `20_ltx_audio_to_video.json` | **audio-driven video** — motion generated to match a real track | 23 s |
| `21_llm_lyrics_to_song.json` | **one line → 60 s sung song**, LLM writes the lyrics | 12 s |

Workflows 13–19 are explained in **[NEW-CAPABILITIES.md](NEW-CAPABILITIES.md)**. Every JSON
carries its own `_comment` and `_notes` — read those before editing one, especially the
mask-convention note in 13/14 and the sigma-schedule note in 17.

## Scripts

| Script | Does |
|---|---|
| `scripts/comfy.py` | run any API workflow, patch inputs, list models/nodes/stats |
| `scripts/idea.py` | **one line in, art-directed image out** — the LLM writes the prompt |
| `scripts/sweep.py` | **vary one input across a list** — style sheets, knob-learning |
| `scripts/gallery.py` | rebuild the browsable `gallery.html` contact sheet |
| `scripts/pipeline.py` | one prompt → keyframe → animated clip |
| `scripts/film.py` | shot list → keyframes → clips → edited film with titles |
| `scripts/mixdown.sh` | mux a score / SFX layers onto a finished cut |
| `scripts/fetch-models.sh` | download model tiers (`utility`, `audio`, `sfx`, `ltx`, `t2v`, …) |
| `scripts/install-tts.sh` | install a local TTS pack without breaking the venv |
| `scripts/restart-comfy.sh` | safely restart the server after installing models |
| `scripts/bench.sh` | re-run the benchmark |

⚠ **Never** run `pkill -f 'main.py --listen'` inside an `ssh host "…"` command — the
pattern matches the ssh command's own shell and kills your session. Use
`scripts/restart-comfy.sh`.

## 60-second start

From the Linux box (or over SSH from Windows):

```bash
ssh k4shix@192.168.1.46
```

```bash
cd ~/shared/comfy-studio && python3 scripts/comfy.py stats
```

Generate an image (~9 s at 1664×928):

```bash
cd ~/shared/comfy-studio && python3 scripts/comfy.py run workflows/01_qwen_t2i_turbo.json -s 10.inputs.text="your prompt here"
```

Any node input can be overridden with `-s <node_id>.inputs.<field>=<value>`. Node IDs are
the top-level keys in the workflow JSON — open the file, they are commented.

Animate the result (~2 min for 5 s at 720p):

```bash
cd ~/shared/comfy-studio && cp ~/ComfyUI/output/claude-generated/qwen_turbo_00001_.png ~/ComfyUI/input/claude_start_frame.png && python3 scripts/comfy.py run workflows/04_wan22_i2v_turbo.json
```

## What was installed on 2026-07-29

The box started with three model families (Qwen-Image, Qwen-Image-Edit, Wan 2.2 I2V).
Added since:

| Added | Gives you |
|---|---|
| RealESRGAN x4 | 4× upscaling, images and video |
| FILM frame interpolation | 16 fps → 32/64 fps |
| BiRefNet | background removal / alpha mattes |
| SAM 3.1 | prompt-driven segmentation, image + video |
| **ACE-Step 1.5 Turbo** | **text → music and songs** (60 s of score in 7.6 s) |
| **Stable Audio 3 Medium** | **SFX, ambience, sound design** |
| **LTX-2.3 22B** | **video with natively synced audio**, FLF2V, IC-LoRA control |
| **Chatterbox TTS** (custom node) | **local narration + voice cloning**, no API |

### Second download session, later on 2026-07-29 — "newest, not merely newer"

Chosen after checking what actually leads each category in July 2026, not from memory.
All 10 files verified byte-exact on arrival. **Downloaded and verified, but not yet
exercised** — see the note at the end of this section.

| Added | Size | Why this one |
|---|---|---|
| **Qwen-Image-Edit 2511** + its 4-step Lightning LoRA | 20 GB | **Supersedes your 2509.** Less image drift, better character consistency, baked-in LoRAs, much better multi-person. Earlier in the session I recommended the *2509* Lightning LoRA — that would have bought speed on an older base. Corrected. |
| Depth Anything 3 + MoGe-2 normals + SDPose | 3.7 GB | Depth, surface normals and whole-body pose. Best value per GB on the box — unlocks controlled composition for images *and* video. |
| LTX-2.3 IC-LoRA union control + ID-LoRA | 1.7 GB | Depth/edge/pose control **for video**, and character identity locked across shots. Deliberately the `ltx-2.3-22b-*` files, **not** the `ltx-2-19b-*` ones — those are for the older LTX-2 19B base and will not load. |
| Hunyuan3D 2.1 | 6.9 GB | **Meshes with PBR**, Unity/Blender-ready. TripoSplat scores higher in preference tests (Elo 1137 vs 996) but outputs Gaussian splats — no mesh, no UVs. Meshes were the deliberate choice. |
| SeedVR2 3B + VAE | 3.7 GB | Diffusion upscaler. Beats the RealESRGAN GAN on faces and text because it *invents* plausible detail rather than sharpening. |

**Completed later the same evening (~166 GB more):**

| Added | Size | Why this one |
|---|---|---|
| **FLUX.2 dev fp8** + Mistral-3-Small encoder + VAE + Turbo LoRA | 53 GB | Second aesthetic — currently leads open-weight photorealism and prompt adherence. ⚠ **Cannot co-reside with Qwen** on 32 GB: batch by model, never interleave shots. |
| **HunyuanVideo 1.5** 720p T2V + I2V + 1080p SR + VAE + byt5 + sigclip + upsampler | 50 GB | Physics and motion specialist, alongside LTX-2.3 (audio + control) and Wan 2.2 (photoreal humans). The 3 GB of support files matter — without the VAE and byt5 the 46.5 GB of DiTs are dead weight. |
| **TripoSplat** + VAE decoder + DINOv3 | 2.8 GB | Image → **Gaussian splats**. Won human-preference tests over Hunyuan3D 2.1 (Elo 1137 vs 996). Splats for looks, meshes for pipeline — both now present. Cheapest new modality on the box. |
| **ACE-Step 1 (3.5B)** | 7.2 GB | **Music remix / extend / restyle.** Music-to-music exists *only* in v1; your 1.5 cannot do it at any setting. |
| **FLUX.1 Fill + OneReward** + t5xxl + clip_l + ae + removal LoRA | 21 GB | **Outpainting** and **object removal**. OneReward fp8 rather than plain `flux1-fill-dev` — newer method, half the size, better at removal. |
| **Wan 2.1 VACE 14B** + CausVid LoRA | 33 GB | **Three** video capabilities from one model: v2v restyle, video inpainting, video outpainting. 14B fp16 over the 4 GB 1.3B — the small one works but is a clear quality step down. |

All 26 files verified byte-exact and confirmed **visible to ComfyUI without a restart** (loaders
re-scan their folders per `/object_info` request).

Total for the two download sessions: **~202 GB**, and ~83 GB deliberately *not* spent on
redundancy — see the skip list above.

Deliberately **skipped** to avoid redundancy: `mistral_3_small_flux2_bf16` (33 GB, the fp8
encoder is correct for 32 GB VRAM), `ltx-2.3-22b-distilled-fp8` (27.5 GB — you already have
`dev-fp8` plus the distilled LoRA, which is the same path), `hunyuan3d-dit-v2_fp16` (that is
Hunyuan3D **2.0**, superseded), and a duplicate FLUX.2 turbo LoRA. That is 83 GB not spent.

**Qwen-Image-Edit 2511 is now measured and proven:**

| | Model | Steps | cfg | Execution |
|---|---|---|---|---|
| `03_qwen_image_edit` | Qwen-Image-Edit **2509** | 20 | 4.0 | 48 s |
| `22_qwen_edit_2511` | **2511** + 4-step Lightning | 4 | 1.0 | **8.3 s** |
| `23_qwen_edit_2511_fusion` | **2511**, two-image fusion | 4 | 1.0 | **12.0 s** |

**5.8× faster on a better base.** Same input image and prompt in both edit rows, so the
comparison is honest. The fusion test composed two separately generated portraits into one
photograph with both faces staying distinct — 2511's headline claim, confirmed. Samples and the
three gotchas that break a 2509 graph: `output/claude-generated/20-qwen-edit-2511/README.md`.

> ⚠ Still untested: Depth Anything 3, SDPose, MoGe-2, the LTX IC-/ID-LoRAs, Hunyuan3D 2.1,
> SeedVR2, FLUX.2 and HunyuanVideo 1.5. Installed and size-verified, but no measured timings.

All 16 files from the first session verified byte-exact against their remote `Content-Length`.
Re-check anytime:

```bash
bash ~/shared/comfy-studio/scripts/fetch-models.sh verify
```

Anything reported `PARTIAL` is resumed by re-running `fetch-models.sh sound`.

### The one result that should change how you work

**LTX-2.3 is ~8× faster than Wan 2.2 at 720p and generates audio in the same pass.**

| | Wan 2.2 I2V | LTX-2.3 |
|---|---|---|
| 720p, ~4–5 s | 129 s | **16.5 s** |
| 8 s clip | ~250 s+ | **13.7 s** |
| Audio | none | **included** |

Use **LTX for text→video** and anything long. Keep **Wan for image→video** when you have
an exact keyframe that must be preserved faithfully. Details and caveats in
[CAPABILITIES.md](CAPABILITIES.md).

Still worth adding: Wan 2.2 **T2V** (~30 GB, text→video), Z-Image Turbo (~11 GB, ~1 s
ideation), SeedVR2 (~4 GB, diffusion upscaling), Depth Anything 3 + SDPose (~2 GB,
control maps). See [MODEL-SHOPPING-LIST.md](MODEL-SHOPPING-LIST.md).

**Before downloading anything, though:** the biggest remaining gap is **3D** — all 8 local
3D templates (Hunyuan3D 2.1, TripoSplat, MoGe) need weights and none are installed, so 3D
is the one whole content type the box cannot do at all today.

## Samples

`~/ComfyUI/output/claude-generated/` has one folder per generation type, each with a
spread of samples and a `README.md` index explaining what each file demonstrates:

```
01-text-to-image   02-image-editing   03-controlnet   04-upscaling
05-image-to-video  06-text-to-video-with-audio        07-frame-interpolation
08-music           09-sound-effects   10-voice        11-short-film
12-segmentation-matting    13-llm-prompt-studio
14-ltx-two-stage-upscale   15-product-composite
16-style-range             17-lora-mechanics
18-audio-to-video          19-llm-lyrics-song
20-qwen-edit-2511          21-3d-generation
22-flux2                   23-control-maps
24-outpaint-removal
```

**Folder 21 is the one to open first** — 3D was the one modality this box could not do at all, and
both a mesh and a Gaussian-splat turntable now render in 19.5 s each from a single image.

### Making a sample explain itself — `CAPABILITY.json`

A folder of PNGs does not carry its own claim. Looking at `flux2_beekeeper_00001_.png` you see a
photograph, not a capability — you cannot tell what was hard, what the input was, or what to look
at. **A sample only demonstrates something if you can see the contrast.**

So each folder declares its claim in a `CAPABILITY.json`, and `scripts/capcard.py` renders it into
`_capability_card.png`: labelled before/after panels under a header carrying the claim, the model,
the cost, and a *"look at this"* pointer. The leading underscore sorts it first in any listing, and
`gallery.py` shows it full-width at the top of the section.

```json
{
  "title":   "Outpainting — extend an image past its frame",
  "claim":   "1024² in, 2048×1024 out. Everything outside the original is invented.",
  "look_at": "The seam. There isn't one — follow the sleeve edge and the horizon.",
  "model":   "FLUX.1 Fill + OneReward fp8",
  "cost":    "27.0 s",
  "workflow":"28_flux_outpaint.json",
  "verdict": "works",
  "panels": [
    {"file": "../22-flux2/flux2_beekeeper_00001_.png", "label": "INPUT — 1024×1024"},
    {"file": "outpaint_wide_00001_.png", "label": "OUTPUT — both thirds invented"}
  ]
}
```

**Three panel types**, because different capabilities need different proof:

| Panel | Declare | For |
|---|---|---|
| whole image | `{"file": "x.png"}` | before/after where the whole frame is the point |
| **1:1 crop** | `{"file": "x.png", "crop": [cx, cy, frac]}` | **upscaling.** Crops the same *world region* from every panel, so a 4× upscale yields 4× the pixels. Shown at equal height, that becomes visible detail rather than a bigger picture — the only honest way to show an upscaler, and completely invisible at fit-to-screen. |
| **video strip** | `{"file": "x.mp4", "frames": 6}` | **motion.** Tiles evenly-spaced frames. Smoothness can't be shown in a still, so the claim should say so — the strip proves frames are distinct content, not duplicates. |

`crop` takes fractions of the image (`[0.5, 0.42, 0.16]` = centre-ish, 16% wide), so the same
values work on a source and its 4× upscale.

Folders with no visual output (`08-music`, `09-sound-effects`, `10-voice`, `19-llm-lyrics-song`)
declare a `CAPABILITY.json` with **no `panels`** — no card is drawn, but the gallery still renders
the claim, the `look_at` and the verdict above the audio players.

Three design decisions worth keeping:

- **Panels are equal *height*, not equal boxes.** A wider output must actually look wider, or the
  layout silently contradicts the claim. Letterboxing a 2:1 result into a square next to a 1:1 input
  makes the outpaint appear *smaller* than its source.
- **`verdict` makes failures legible.** `failed` renders a red badge, so a documented failure reads
  as a deliberate finding rather than a bad sample. Folder 24 uses it.
- **`file` accepts `../other-folder/x.png`**, so an input can live where it was generated instead of
  being duplicated.

```bash
~/ComfyUI/venv/bin/python scripts/capcard.py --list          # which folders still lack one
~/ComfyUI/venv/bin/python scripts/capcard.py 24-outpaint-removal
```

### The card is an info sheet, not just a proof

Beyond the claim and panels, each declaration carries the things you cannot see in a picture —
rendered as a six-block grid under the panels:

| Block | Holds |
|---|---|
| **THE MODEL** | name, **release date**, **VRAM wanted**, measured cost, workflow file |
| **REAL LIMITS ON THIS 5090** | the practical ceiling — max useful resolution, max clip seconds, frame quanta, the traps |
| **ALTERNATIVES** | what else does this job. `+` = installed, `-` = not installed |
| **STRONG AT** / **WEAK AT** | honest both ways |
| **NEXT STEPS** | for folders not yet explored |

Release dates and VRAM figures come from **ComfyUI's own template index**, not from memory —
`index.json` carries a `date` and a `size` (which is really the VRAM requirement) per template.
That is why several read above 32 GB: FLUX.2 wants 52.7, Qwen-Edit 2511 wants 47.8, VACE wants
53.8. Those models *offload* on this box rather than failing, and that offload is already inside
the measured timings.

Every card carries an **`updated`** stamp so you know when it was last checked, and a **`status`**
of `verified` / `installed-untested` / `not-explored`.

**Declared: 33 folders**, 20 with panels. Folders `27`–`34` are **plans, not results** — they carry
a blue `NOT YET EXPLORED` badge and a NEXT STEPS block, so an unexplored capability still tells you
what it is, what it would cost and what to do about it. That covers LoRA training, VACE, HunyuanVideo,
camera control, character identity, SeedVR2, Z-Image and FLF2V.

Edit declarations in [`scripts/_write_caps.py`](scripts/_write_caps.py), never in the output tree —
they are versioned with the kit and survive a folder being regenerated. Prose and panels are kept in
separate dicts there so you can edit one without touching the other.

```bash
python3 scripts/_write_caps.py                            # write declarations
~/ComfyUI/venv/bin/python scripts/capcard.py              # render every card
~/ComfyUI/venv/bin/python scripts/capcard.py --list       # coverage + last-updated audit
```

Rebuild the gallery after generating more. It defaults to 12 items per folder so the page stays
openable; raise it if you want everything:

```bash
cd ~/shared/comfy-studio && ~/ComfyUI/venv/bin/python scripts/gallery.py --max-per-folder 12
```

Every folder from 12 on has a `README.md` explaining each file — including what is *wrong*
with some of them and why they were kept. Two worth opening first:

- **`16-style-range/`** — one subject, twelve media, 59 s. The fastest way to decide how a
  project should look. Includes one instructive failure.
- **`17-lora-mechanics/`** — a LoRA strength sweep. Thirty seconds of browsing teaches the
  parameter people most often get wrong.

Regenerate 01–11 with `bash scripts/make-samples.sh`; 12–15 are single `comfy.py run` calls
listed in [NEW-CAPABILITIES.md](NEW-CAPABILITIES.md); 16–17 are `sweep.py` calls listed in
their own READMEs.

## Worked example

`films/the-last-signal.json` → a 45.6 s scored short film, 9 shots, 720p.
Rendered to `output/claude-generated/film-the-last-signal/`. Total cost: **~21 minutes
of GPU time** (45 s of keyframes, 19.6 min of video, 7.6 s of music, ~20 s of editing).
