# The whole map — what AI can generate, and where you stand on each

*Verified against the live box 2026-07-29. Your install ships **488 workflow templates**,
of which **268 run locally** and 220 are paid cloud API nodes.*

This is the "what is even possible" document. Read it when you want to know whether an idea
is feasible, not how to execute it — each row points at the workflow or template that does.

Legend: **✅ works today** · **⬇ one download away** · **☁ cloud API only** · **✗ not really solved yet**

---

## The one-screen version

| Modality | Where you stand |
|---|---|
| **Still images** | ✅ Excellent. Best-in-class text rendering, editing, control, upscaling. |
| **Video** | ✅ Strong. Two models, audio generated in-pass, 21 s for 4 s of 720p. Missing: video *control* and identity lock. |
| **Music & audio** | ✅ Strong. Songs with vocals, instrumentals, SFX, narration. Missing: remix/editing. |
| **Speech** | ✅ Works. Local TTS + voice cloning. |
| **3D** | ✗ **Nothing installed.** The one whole modality you cannot do at all. 8 local templates waiting. |
| **Text / LLM** | ✅ Works and underused. Prompt writing, captioning, vision Q&A, all local. |
| **Control & CV** | ✅ Segmentation, matting, edges. ⬇ Depth and pose are the gap. |

---

## 1. Still images — 91 local templates

### Generation

| Capability | Status | Where |
|---|---|---|
| Text → image | ✅ | `01_qwen_t2i_turbo` (4.5 s), `02_qwen_t2i_quality` (30 s) |
| **Text rendering inside the image** | ✅ | Qwen-Image 2512 is the best open model at this. Signs, packaging, posters, UI mockups. |
| Idea → prompt → image, LLM in the loop | ✅ | `16_llm_to_image`, `scripts/idea.py` (6 s) |
| Style range from prompting alone | ✅ | `16-style-range/` — 12 media, one subject |
| Ultra-fast ideation (~1 s/image) | ⬇ | Z-Image Turbo, ~11 GB |
| A second aesthetic (non-Qwen look) | ⬇ | Flux.2, Krea-2, Chroma1-HD, Lumina, HiDream — each a different house style |
| Anime / illustration specialists | ⬇ | Anima, NewbieImage, NetaYume Lumina |

### Editing and control

| Capability | Status | Where |
|---|---|---|
| Instruction editing ("make it winter") | ✅ | `03_qwen_image_edit` (48 s — see LoRA note below) |
| Structural control (canny/edge → image) | ✅ | `05_qwen_controlnet` (10.5 s) |
| Depth / pose control | ✅ | **Installed 2026-07-29.** `depth_anything_3_mono_large` + `moge_2_vitl_normal_fp16` in `geometry_estimation/`, `sdpose_wholebody_fp16` in `checkpoints/`. Nodes `LoadDA3Model`/`DA3Inference`/`DA3Render`/`MoGeInference`/`SDPoseKeypointExtractor` all live. Missing piece is a kit *workflow*, not weights. |
| Inpainting (replace a region) | ✅ | Qwen ControlNet inpainting + SAM 3.1 for the mask |
| Outpainting (extend the frame) | ⬇ | `flux_fill_outpaint_example` needs Flux Fill |
| **Text-prompted segmentation** | ✅ | `13_sam3_segment` — say "the bottle", get a mask |
| **Background removal / alpha matte** | ✅ | `14_birefnet_matte` |
| Relighting | ⬇ | `Qwen-Image-Edit-2509-Relight` LoRA — base model already installed |
| Copy lighting from a reference | ⬇ | `Qwen-Image-Edit-2509-Light-Migration` LoRA |
| **Decompose into layers (≈ a PSD)** | ⬇ | `image_qwen_image_layered`. Genuinely underrated — closest thing to generating an editable file. |
| Multi-angle / character turnaround | ⬇ | `Qwen-Edit-2509-Multiple-angles` LoRA |
| 360° object turnaround | ⬇ | `qwen-360-diffusion-2512` LoRA |
| Product on a new background | ✅ | `19_product_composite` (31.7 s) |

> **The 48 s edit is a missing LoRA, not a hardware limit.** You have Qwen-Image-Edit 2509
> but not its 4-step Lightning LoRA. One 1.7 GB download → ~10 s. See [LORAS.md](LORAS.md).

### Resolution

| Capability | Status | Where |
|---|---|---|
| GAN upscale 4× | ✅ | `09_image_upscale` — 1664×928 → 6656×3712 in 4.5 s |
| Diffusion upscale (invents detail) | ⬇ | SeedVR2, ~4 GB. Better than GAN on faces and text. |
| Latent upscale + refine | ✅ | The pattern in `17_ltx23_t2v_upscaled`, applies to stills too |

---

## 2. Video — 56 local templates

| Capability | Status | Where |
|---|---|---|
| Text → video | ✅ | `11_ltx23_t2v_audio` (13–17 s), `17_ltx23_t2v_upscaled` (21 s, 720p) |
| **Video with synced audio, one pass** | ✅ | LTX-2.3. Nothing else local does this. |
| Image → video | ✅ | `04_wan22_i2v_turbo` (Wan, faithful keyframe), `12_ltx23_i2v_audio` (LTX, fast) |
| First frame + last frame → video | ✅ | `video_ltx2_3_flf2v`, `video_wan2_2_14B_flf2v`. **Untested — best tool for controlled transitions.** |
| **Audio → video (lip / motion sync)** | ✅ | `20_ltx_audio_to_video` — 23 s for 4 s at 1280×704. Nothing else local does this. Motion correlated with audio, not phoneme-accurate lip-sync. |
| Frame interpolation (smooth motion) | ✅ | `07_video_interpolate` — 16→32 fps, 7.5 s |
| 2× spatial upscale, LTX-native | ✅ | `17_ltx23_t2v_upscaled` |
| Style transition across a clip | ✅ | `template_ltx2_3_style_transition` needs `ltx2.3-transition` LoRA ⬇ |
| **Depth / edge / pose control for video** | ✅ | **Installed.** `ltx-2.3-22b-ic-lora-union-control-ref0.5` + Depth Anything 3 / MoGe-2. ⚠ The template hardcodes `ltx-2.3-22b-distilled-fp8` which you do *not* have — repoint it at `ltx-2.3-22b-dev-fp8` + the distilled LoRA @ 0.5, exactly as workflows 11/12/17 do. A rewire, not a download. No kit workflow yet. |
| **Character identity locked across shots** | ✅ | **Installed.** `ltx-2.3-id-lora-talkvid-3k` @ 1.0 stacked on distilled @ 0.5. Trained on *talking* video, so it is identity lock for dialogue coverage, not for arbitrary wide shots. Prompt needs `[VISUAL]: / [SPEECH]: / [SOUNDS]:` sections. No kit workflow yet. |
| Camera control (dolly, orbit) | ⬇ | Wan Fun Camera, or LTX camera-control LoRAs |
| Video → video restyle | ⬇ | Wan VACE |
| Character replacement in footage | ⬇ | SCAIL2 LoRA (SAM 3.1 half is done) |
| Video segmentation / tracking | ✅ | `SAM3_VideoTrack` — installed, no workflow yet |
| Video inpainting / object removal | ⬇ | `utility_void_video_inpainting` |
| Text → video (Wan) | ⬇ | Wan 2.2 T2V, ~30 GB — reuses your encoder and VAE |
| Long-form / infinite length | ⬇ | `LTXVContextWindows` node is installed; `video_wan2_1_infinitetalk` |

---

## 3. Music and audio — 13 local templates

| Capability | Status | Where |
|---|---|---|
| **Text → full song with vocals** | ✅ | `06_acestep_music` — 60 s of music in 7.6 s |
| Text → instrumental / score bed | ✅ | Same, prompt for instrumental |
| **LLM writes lyrics → model sings them** | ✅ | `21_llm_lyrics_to_song` — 60 s of sung music from one line, 12 s. *Correction: I first listed `audio_ace_step_1_5_split_llm` as free. It is not — it needs `qwen_4b_ace15`. Workflow 21 gets the same result by routing your existing Qwen3.5-2B into the lyrics field.* |
| SFX, foley, ambience | ✅ | `10_stableaudio_sfx` — 30 s of wind in 3 s |
| Sound design layering | ✅ | `scripts/mixdown.sh` |
| **Text → speech, local** | ✅ | `08_chatterbox_tts` |
| **Voice cloning** | ✅ | Chatterbox, from a reference sample |
| Music → music (remix, extend, restyle) | ⬇ | Only ACE-Step **1** does this; you have 1.5. A genuine gap. |
| Stem separation | ✗ | Not in ComfyUI. Use Demucs separately. |
| Audio → text (transcription) | ✅ | `TextGenerate` takes an `audio` input |

---

## 4. 3D — 8 local templates, **zero installed**

This is the single whole modality the box cannot do. Nothing here works today.

| Capability | Status | Needs |
|---|---|---|
| Image → textured mesh | ⬇ | Hunyuan3D 2.1 |
| Multi-view → mesh | ⬇ | Hunyuan3D multiview (+ turbo variant) |
| Image → Gaussian splat | ⬇ | TripoSplat |
| Photo → mesh (geometry only) | ⬇ | MoGe perspective |
| 360° panorama → mesh | ⬇ | MoGe panorama |
| Animated 3D / rigging | ✗ | Not solved in ComfyUI. Export and rig in Blender. |

If you want 3D, this is a deliberate download session — reckon 30–60 GB. Everything else in
this document you can already do or unlock for a few GB.

---

## 5. Text and LLM — 4 local templates, badly underused

| Capability | Status | Where |
|---|---|---|
| Prompt writing from a one-liner | ✅ | `15_llm_prompt_studio`, `scripts/idea.py` (3 s) |
| LTX-style video prompts incl. soundscape | ✅ | `18_ltx_prompt_enhancer` |
| Image captioning / describe a photo | ✅ | `TextGenerate` with an `image` input + a VL encoder |
| Video description | ✅ | `TextGenerate` takes a `video` frame batch |
| Vision Q&A | ✅ | Qwen2.5-VL-7B, installed |
| Uncensored prompt writing | ✅ | Abliterated Gemma LoRA |

The point: **you have four instruct LLMs sitting in `models/text_encoders/`** and they cost
nothing extra to use. Prompt-writing is the bottleneck in generation, not GPU time.

---

## 6. Control and computer vision

| Capability | Status | Where |
|---|---|---|
| Text-prompted segmentation | ✅ | SAM 3.1 |
| Salient-object matting | ✅ | BiRefNet |
| Canny / edge maps | ✅ | Built-in preprocessors |
| **Depth estimation** | ✅ | Depth Anything 3 + MoGe-2 normals, installed. `DA3Inference` / `MoGeInference` / `DA3Render`. |
| **Pose estimation** | ✅ | SDPose whole-body, installed. `SDPoseKeypointExtractor` / `SDPoseDrawKeypoints`, multi-person, image and video. |
| Object detection / bounding boxes | ✅ | `RTDETR_detect`, `SAM3_Detect` |
| Optical flow | ⬇ | Folder exists, empty |
| Video object tracking | ✅ | `SAM3_VideoTrack` |

> **Depth + pose (~2 GB total) is the best value download on this page.** It unlocks
> controlled composition for both images and video, and it is what most "make it look
> deliberate" workflows depend on.

---

## 7. What is cloud-only

220 templates are paid API nodes. Being honest about what you are *not* getting locally:

- **Nano Banana Pro / Gemini 3 Image** — studio-grade 4K, best-in-class instruction following
- **Seedream 5.0 / Seedance 2.0** — leading image edit and storyboard→video
- **Veo, Kling, Runway, Sora-class** — the top tier of video realism and duration
- **Topaz, Magnific, Recraft** — commercial upscalers
- **Grok / GPT image** endpoints

The realistic gap: cloud is ahead on *long, coherent, high-realism video* and on *following
complicated instructions exactly*. Local is ahead on iteration speed, cost, privacy, batch
volume, and total control. For a 45-second short film at 720p, local wins on every axis that
matters. For a 60-second photoreal ad with a talking human, cloud still wins.

---

## 8. Cross-modal pipelines — the actually interesting part

Single models are commodities; the combinations are where the leverage is. Everything in this
section runs today.

**Complete short film, no external assets** — `scripts/film.py`
`idea.py` → shot list → Qwen keyframes → Wan/LTX clips → ACE-Step score → Stable Audio
ambience → Chatterbox narration → ffmpeg edit. Already done: `11-short-film/`, 45.6 s, ~21 min.

**Product campaign from one photo** — workflows 14 → 19 → 09
BiRefNet matte → generated backdrop → composite → 4× upscale. Change one prompt per
campaign; the product stays pixel-identical.

**Style bible for a project** — `sweep.py` + `sweeps/styles.txt`
One subject × 12 media in 59 s. Pick the look before you commit to 200 renders.

**Music video** — `06` → `video_ltx2_3_ia2v`
Generate the track, then drive video *from the audio*. Untested and the most interesting
thing on this list.

**Character across many shots** — needs the ID-LoRA ⬇
Multi-angle sheet → identity lock → shots. The one narrative pipeline still blocked.

**Talking presenter** — `08` → `video_ltx2_3_ia2v`
Chatterbox narration → audio-driven video. Untested.

---

## 9. If you do nothing else

Ranked by value per gigabyte:

*Items 1–3 and 5 of the original list were bought on 2026-07-29 and are now installed. What
replaced them is not a download list at all — it is a build list, because the weights arrived
and nothing wires them up:*

1. **Build `24_ltx23_ic_control.json`** — control video → Depth Anything 3 / MoGe-2 → `LTXVAddGuide`
   + `GetICLoRAParameters` + IC-LoRA @ 1.0. **0 GB.** This is arbitrary camera control: a phone
   clip or a Blender flythrough becomes a dolly/orbit/crane LTX will follow.
2. **Build an ID-LoRA workflow.** **0 GB.** All five required models present. The single biggest
   gap in multi-shot narrative.
3. **Wire `ChatterboxTTS`'s `audio_prompt` input.** **0 GB.** It accepts a reference clip for
   zero-shot voice cloning and *nothing in the kit uses it* — dialogue is currently one voice
   pitch-shifted. Needs ~10 s of reference audio per character, not a model.
4. **Add a `loudnorm` pass to the mix.** **0 GB.** Measured output is −17.9 LUFS with 14.7 LU
   range; ffmpeg 8.1.2 has `loudnorm`, `sidechaincompress`, `alimiter` already.
5. **`qwen-image-edit-2511-multiple-angles-lora` (~1 GB)** — the cheapest *download* left. Turns
   one keyframe into a turnaround, i.e. it manufactures the character bible the items above need.
6. **Z-Image Turbo (~11 GB)** — 1-second ideation, if you want it.

Two of the three "costs nothing" items are now **done** — `20_ltx_audio_to_video` and
`21_llm_lyrics_to_song`. The one still untried on existing weights:

- `video_ltx2_3_flf2v` — first-frame + last-frame transitions

---

## See also

- **the gallery** — `Z:\ComfyUI\output\claude-generated\gallery.html`. Double-click it;
  every sample as a thumbnail, grouped, with prompts. Rebuild with
  `~/ComfyUI/venv/bin/python scripts/gallery.py`
- [LORAS.md](LORAS.md) — the LoRA layer, and training your own
- [TEMPLATES.md](TEMPLATES.md) — per-template notes
- [CAPABILITIES.md](CAPABILITIES.md) / [NEW-CAPABILITIES.md](NEW-CAPABILITIES.md) — measured timings
- [MODEL-SHOPPING-LIST.md](MODEL-SHOPPING-LIST.md) — download commands
