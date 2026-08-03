# Built-in templates worth your time

Your install ships **`comfyui-workflow-templates` 0.11.17 — 488 templates**, of which
**268 run locally** and 220 are paid cloud API nodes (Seedream, Nano Banana, Kling, Runway,
Veo, Grok, Topaz…). Open them in the UI: **Workflow → Browse Templates**.

> *Corrected 2026-07-29: this line previously read "336 templates, 231 local", which did not
> match the per-category table below it. The table was right; recounted totals are 488 / 268.*

**Many of these templates need a LoRA, not just a base model.** 54 distinct LoRA files are
referenced across the 268 local templates and you have 5 — so a template can fail even when
you own the checkpoint. [LORAS.md](LORAS.md) has the audit, and
`python3 scripts/_lora_audit.py` regenerates it.

Counts by category (local / total):

| Category | Local | Total |
|---|---|---|
| Image | 91 | 150 |
| Video | 56 | 147 |
| Use Cases | 48 | 48 |
| Utility | 33 | 54 |
| Audio | 13 | 25 |
| 3D Model | 8 | 33 |
| Getting Started | 10 | 10 |
| LLM | 4 | 16 |
| Node Basics | 5 | 5 |

Below: the ones actually worth opening, newest-first. ✅ = runs today on your weights.
⬇ = needs a download (see [MODEL-SHOPPING-LIST.md](MODEL-SHOPPING-LIST.md)).

---

## Image

| Template | | Why |
|---|---|---|
| `image_qwen_Image_2512` | ✅ | Your workhorse. Best open text rendering, period. |
| `image_qwen_image_2512_with_2steps_lora` | ✅ | Turbo variant. Note it's tuned for a 2-step LoRA; you have the 4-step. |
| `image_qwen_image_instantx_controlnet` | ✅ | You own this ControlNet. Canny/depth/pose → Qwen. |
| `image_qwen_Image_2512_controlnet` | ⬇ | The newer *Fun Union* ControlNet — better than InstantX for depth. |
| `image_qwen_image_layered` | ⬇ | **Decomposes an image into stacked layers** — closest thing to generating a PSD. Underrated. |
| `image_z_image_turbo` | ⬇ | ~1–2 s per image on a 5090. The ideation model. |
| `image_flux2` / `image_flux2_klein_text_to_image` | ⬇ | Flux.2 Dev (heavy) and Klein 4B (light). Different aesthetic from Qwen. |
| `image_krea2_turbo_t2i` | ⬇ | Krea-2 — the current favourite for photoreal without the "AI look". |
| `image_chroma_text_to_image` | ⬇ | Chroma1-HD. Unfiltered, very strong on painterly/illustrative work. |
| `image_anima_base_v1`, `image_newbieimage_exp0_1-t2i` | ⬇ | Anime/illustration specialists. |
| `image_hidream_o1_dev`, `image_ovis_text_to_image`, `image_longcat_text_to_image`, `image_lens_t2i`, `image_pixeldit_t2i` | ⬇ | Newer entrants, all 2026-era. Try Lens and Ovis first. |
| `image_qwen_image_edit_2511` | ⬇ | Newest Qwen edit + a real 4-step Lightning LoRA. Direct upgrade over your 2509. |
| `image_boogu_image_0_1_edit`, `image_joyai_image_edit`, `image_chrono_edit_14B` | ⬇ | Alternative edit models. ChronoEdit is interesting — temporal/"what happens next" edits. |

## Video

| Template | | Why |
|---|---|---|
| `video_wan2_2_14B_i2v` | ✅ | What you're running. |
| `video_wan2_2_14B_t2v` | ⬇ | Text→video. Reuses your umt5 encoder + wan2.1 VAE, so only ~30 GB of new DiT. |
| `video_ltx2_3_i2v` / `_t2v` | ✅ | **LTX-2.3 22B** — the newest local video model in the set. Installed later on 2026-07-29. See `17_ltx23_t2v_upscaled.json` for the two-stage version, which is how this template actually works. |
| `video_ltx2_3_ia2v` | ✅ | **Image + Audio → Video.** Native lip/motion sync to a supplied audio track. Nothing else local does this. Untested here — worth being your next experiment. |
| `video_ltx2_3_flf2v` | ✅ | First-frame + last-frame → video. Best tool for controlled shot transitions. Untested here. |
| `video_ltx2_3_ic_lora` | ✅ | IC-LoRA union control — pose/depth/edge control *for video*. **LoRA installed 2026-07-29**, and Depth Anything 3 + MoGe-2 are the control sources. ⚠ The template hardcodes `ltx-2.3-22b-distilled-fp8`, which is **not** installed — repoint to `ltx-2.3-22b-dev-fp8` + distilled LoRA @ 0.5 (workflows 11/12/17 show the pattern). Rewire, not download. |
| `video_ltx2_3_id_lora` | ✅ | Character identity lock across shots. **ID-LoRA installed**; all five required models present. `talkvid` = trained on talking video, so it locks identity for *dialogue* coverage. Needs `[VISUAL]:/[SPEECH]:/[SOUNDS]:` prompt sections. Same distilled-checkpoint repoint applies. |
| `video_ltx2_3_style_transition` | ✅ | Morph between two visual styles over a clip. Base checkpoint only. Untested here. |
| `video_wan21_scail2_character_replacement` | ⬇ | Swap a character into existing footage. SAM 3.1 is now wired up (`13_sam3_segment.json`), but the SCAIL2 weights are still missing. |
| `video_bernini_r_video_editing` | ⬇ | Instruction-driven video editing ("make it night"). |

## Audio — *no longer a gap; this section was written before the audio models landed*

| Template | | Why |
|---|---|---|
| `audio_ace_step1_5_xl_turbo` | ✅ | **Start here.** Text → full song with vocals. 60 s of music in 7.6 s. Wired up as `06_acestep_music.json`. |
| `audio_ace_step_1_5_split_llm` | ✅ | LLM writes the lyrics, ACE-Step sings them. End-to-end song from one line of intent. You have both `qwen_0.6b_ace15` and `qwen_1.7b_ace15`. Untested here — the most interesting audio template you have not run. |
| `audio_ace_step_1_5_split` / `_split_4b` | ✅ | Same split architecture without the LLM stage. |
| `audio_stable_audio_3_medium` | ✅ | SFX and sound design (not songs). Wired up as `10_stableaudio_sfx.json`. Complements ACE-Step rather than competing. |
| `audio_ace_step_1_5_checkpoint` | ⬇ | Single-file AIO if you'd rather not manage separate files. Cosmetic — you already have the split weights. |
| `audio_ace_step_1_t2a_instrumentals` | ⬇ | ACE-Step **1**, not 1.5 — different weights. Use `audio_ace_step1_5_xl_turbo` with an instrumental prompt instead. |
| `audio_ace_step_1_m2m_editing` | ⬇ | Music→music: remix, extend, restyle an existing track. ACE-Step **1** weights. This capability has no 1.5 equivalent installed, so it is a genuine gap if you want remixing. |

## 3D

| Template | | Why |
|---|---|---|
| `3d_triposplat_image_to_gaussian_splat` | ⬇ | Newest: single image → Gaussian splat. |
| `3d_hunyuan3d-v2.1` | ⬇ | Single image → textured mesh. Best mesh quality locally. |
| `3d_moge_perspective_to_mesh` | ⬇ | Photo → geometry, no generation. Good for real-scene reconstruction. |
| `3d_moge_panorama_to_mesh` | ⬇ | 360 panorama → mesh. Combine with the Qwen 360 LoRA template below. |

## Utility — small models, disproportionate payoff

| Template | | Why |
|---|---|---|
| `utility-gan_upscaler` | ⬇ | 64 MB. 4× upscale for images and video. Grab it today. |
| `utility_video_frame_interpolation` | ⬇ | 70 MB. Turns your 16 fps Wan output into 32/64 fps. |
| `utility_birefnet_remove_background` | ⬇ | Clean alpha mattes. |
| `utility_image_segment_sam3` / `utility_video_segment_sam3` | ⬇ | Prompt-driven segmentation ("the red car"). |
| `utility_seedvr2_3b_int8_upscale_video` | ⬇ | Diffusion upscaler for **video**. The real fix for soft AI footage. |
| `utility_depth_anything3_*`, `utility_sdpose_*` | ⬇ | Generate the control maps your ControlNet is waiting for. |
| `utility_void_video_inpainting` | ⬇ | Remove objects from video. |
| `utility_pid_latent_upscale_dit` | ⬇ | Latent-space upscale — cheaper than a full second pass. |

## Use Cases — pre-built recipes (all 48 run locally)

These are the highest-leverage things in the whole template set: complete multi-stage
pipelines, not single-model demos.

**Relevant to your `saltmark` game project:**

- `templates_3d_match_game_art_style.app` — **Game Asset Style Transfer Sprite Generator.**
  Feed a style reference, get consistent sprites. This is exactly what your
  `output/saltmark/sprites` and `units` folders are doing by hand.
- `templates-character_sheet` — 360 full-body turnaround from one image.
- `templates-1_click_multiple_character_angles` — multi-angle consistency.
- `templates-1_click_multiple_scene_angles` — same for environments.
- `templates-color_illustration` — line art → coloured.
- `template_qwen_Image_2512_360_lora` — 360 panorama generation (skyboxes).
- `templates-3D_logo_texture_animation`, `templates-textured_logotype-v2.1` — UI/branding.

**Video production:**

- `templates-6-key-frames` — **Multi-Keyframe Video Stitching.** Generate keyframes, let
  the model interpolate between them. The practical way to make clips longer than 5 s.
- `template_image_speech_to_video` — UGC video with voice clone.
- `template_eric_exploded_view` — exploded-view product animation.
- `template_sferro21_product_ad.app` — cinematic product ad sequence.

**Photography / product:**

- `templates-product_scene_relight`, `template_character_portrait_relighting`,
  `templates-portrait_light_migration` — relighting is where Qwen-Edit genuinely excels.
- `templates-image_to_real` — illustration → photoreal.
- `templates_rob_realistic_2k_images_quick_variations` — variation sweeps.

## LLM (local prompt expansion)

`llm_qwen3_5_text_gen`, `llm_qwen3vl_text_gen`, `llm_gemma4_text_gen`.
2–8 GB. Turns "lighthouse in a storm" into a full cinematic prompt inside the graph, no
API key. Worth it once you're generating in volume — pair with `audio_ace_step_1_5_split_llm`.
