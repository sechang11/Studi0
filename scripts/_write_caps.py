#!/usr/bin/env python3
"""Write CAPABILITY.json into every sample folder, explored or not.

Declarations live here rather than in the output tree so they are versioned with the
kit and survive a folder being regenerated. Re-running overwrites - edit here.

Release dates and VRAM figures are pulled from ComfyUI's own template index
(`comfyui_workflow_templates_json/templates/index.json`), not from memory. The `size`
field in that index is the VRAM requirement, which is why several exceed 32 GB - those
models offload between stages on this box rather than failing.

    python3 scripts/_write_caps.py
    ~/ComfyUI/venv/bin/python scripts/capcard.py
"""
import json
import os

R = os.path.expanduser("~/ComfyUI/output/claude-generated")
U = "2026-07-31"

CAPS = {

# ─────────────────────────── images ───────────────────────────
"01-text-to-image": {
 "title": "Text to image — the workhorse",
 "claim": "Qwen-Image 2512 with a 4-step Lightning LoRA. 1664×928 in 4.5 seconds, and the best in-image text rendering of any open model by a clear margin — signs, packaging, posters and UI mockups come out legible rather than as glyph soup.",
 "look_at": "typography_00001_ and qwen_quality_00001_ — the readable lettering is the thing to check, because it is where every other open model still fails. The turbo files are 4-step; the quality files are 20-step with no LoRA.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "Qwen-Image 2512 (fp8) + Lightning 4-step LoRA", "released": "2025-12-31",
 "vram": "29.6 GB", "cost": "4.5 s @ 1664×928 · 30–36 s at 20 steps",
 "workflow": "01_qwen_t2i_turbo.json · 02_qwen_t2i_quality.json",
 "limits": [
   "Sweet spot is 1–2 MP: 1664×928, 1328×1328, 1024×1024. Measured 4.5 s at 1664×928.",
   "The real ceiling is QUALITY, not VRAM. Past roughly 2 MP the composition starts duplicating — two horizons, repeated subjects. 2048×1152 is about the practical edge.",
   "So do not chase resolution in the sampler. Generate at 1–2 MP, then upscale 4× to 24.7 MP (folder 04). That is the whole workflow.",
   "Dimensions must be multiples of 16. shift≈3.1 suits wide frames, 4–5 suits square.",
   "Batch of 4 at 1024² fits comfortably in 32 GB."],
 "strong": ["In-image text — best open model available",
            "Prompt adherence on long descriptive clauses",
            "Speed: 4 steps at cfg 1.0 with the Lightning LoRA"],
 "weak": ["Photoreal skin and faces — FLUX.2 is visibly better",
          "Hands, as with every model",
          "Renders 'flat' by default; it takes a grade well and needs one"],
 "alternatives": ["+ FLUX.2 dev — installed, better photorealism, 5× slower (folder 22)",
                  "+ Z-Image Turbo — installed, ~1 s ideation, untested here",
                  "- Chroma1-HD — not installed; unfiltered, strong on painterly work",
                  "- Krea-2 — not installed; photoreal without the 'AI look'"]},

"22-flux2": {
 "title": "FLUX.2 dev — the second aesthetic",
 "claim": "Currently the leader among open-weight models on photorealism and prompt adherence. Its text encoder is Mistral-3-Small — an actual LLM — so it rewards complete natural sentences rather than keyword soup.",
 "look_at": "The density of small physical detail asked for and delivered: propolis staining in the nail beds, a white scar across one knuckle, bees sharp on the near comb blurring to motion at the edges.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "FLUX.2 dev fp8 + Turbo LoRA", "released": "2025-11-26",
 "vram": "52.7 GB", "cost": "24.6 s @ 1024², 8 steps",
 "workflow": "26_flux2_t2i.json",
 "limits": [
   "52.7 GB of VRAM wanted against 32 GB available — it WILL offload. That is the 24.6 s.",
   "CANNOT co-reside with Qwen. Batch by model; interleaving costs a full offload per image.",
   "1024² is the comfortable size. Larger is possible but the offload cost compounds badly.",
   "No negative prompt exists — it uses a BasicGuider. You can only state what you DO want."],
 "strong": ["Photorealism — the best open-weight option",
            "Following a long, complicated instruction exactly",
            "Natural-sentence prompts (LLM text encoder)"],
 "weak": ["In-image text — clearly behind Qwen",
          "Speed: 5× slower than Qwen turbo",
          "VRAM: the heaviest image model here"],
 "alternatives": ["+ Qwen-Image 2512 — installed, 5× faster, better text (folder 01)",
                  "+ Z-Image Turbo — installed, far faster, lower ceiling",
                  "- Krea-2, HiDream, Lumina — not installed"]},

"02-image-editing": {
 "title": "Instruction editing — change one thing, keep everything else",
 "claim": "Plain-English instructions applied to an existing image. The hard part is not the change, it is everything that must NOT change: composition, camera angle and the structure of the subject all have to survive.",
 "look_at": "Compare each against the original. The rock silhouette, tower position and framing are identical throughout — only season, light or medium moved. An edit that redraws the subject has failed even when it looks good.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "Qwen-Image-Edit 2509", "released": "2025-09-25",
 "vram": "29.6 GB", "cost": "48 s (2511 does the same job in 8.3 s — folder 20)",
 "workflow": "03_qwen_image_edit.json",
 "limits": [
   "One edit per pass. Two instructions in one prompt gives you neither reliably.",
   "Always state what to PRESERVE, explicitly. Omitting it is the main cause of drift.",
   "2509 needs 20 steps at cfg 4.0. 2511 + its Lightning LoRA needs 4 at cfg 1.0.",
   "Superseded — use folder 20's 2511 path for anything new."],
 "strong": ["Season, weather, time-of-day changes", "Relighting by description",
            "Medium and style changes that keep staging"],
 "weak": ["Multi-person scenes — 2509 blends faces (2511 fixes this)",
          "Small text edits inside the image", "Slow at 48 s"],
 "alternatives": ["+ Qwen-Image-Edit 2511 — installed, 5.8× faster, better (folder 20)",
                  "+ FLUX.1 Fill — installed, for outpaint/removal instead (folder 24)",
                  "- ChronoEdit — not installed; 'what happens next' temporal edits"]},

"20-qwen-edit-2511": {
 "title": "Two-image fusion — compose separately generated people into one photo",
 "claim": "These two people were generated in completely separate sessions, hours apart, from unrelated prompts. 2511 put them in one photograph in 12 seconds with both faces staying distinct — the exact thing 2509 fails at, where it averages them into one face.",
 "look_at": "Both faces, then the light. Each person is recognisably themselves, AND the workshop window light now falls across both rather than each keeping its original key. That makes this a casting tool, not a collage tool.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "Qwen-Image-Edit 2511 + 4-step Lightning LoRA", "released": "2025-12-23",
 "vram": "47.8 GB", "cost": "8.3 s single edit · 12.0 s two-image fusion",
 "workflow": "22_qwen_edit_2511.json · 23_qwen_edit_2511_fusion.json",
 "limits": [
   "Up to THREE reference images (image1/image2/image3 on TextEncodeQwenImageEditPlus).",
   "47.8 GB wanted vs 32 GB — offloads, and that is already in the 8.3 s figure.",
   "FluxKontextMultiReferenceLatentMethod is MANDATORY, even for one reference. Omit it and edits drift off source. Most common reason a 2509 graph breaks on 2511.",
   "Without the Lightning LoRA it wants 40 steps at cfg 3.0 — not the 20 that 2509 used.",
   "Refer to inputs literally as 'image 1' and 'image 2'; vaguer wording measurably weakens the association."],
 "strong": ["Multi-person consistency — its headline improvement",
            "Reduced image drift vs 2509", "Selected community LoRAs baked into the base",
            "5.8× faster than 2509 with its Lightning LoRA"],
 "weak": ["Still cannot invent a genuinely new camera angle of a subject",
          "Needs the multi-angle LoRA for turnarounds (installed, untested)"],
 "alternatives": ["+ 2509 — installed, superseded (folder 02)",
                  "+ multiple-angles LoRA — installed, untested; makes turnarounds",
                  "- IPAdapter / PuLID / InstantID — none installed; whole face-embedding family absent"]},

"03-controlnet": {
 "title": "ControlNet — dictate structure, generate everything else",
 "claim": "The edge map on the left was extracted from a lighthouse photograph, then used as a hard structural constraint to generate something entirely different — a brutalist tower — occupying exactly the same silhouette and composition.",
 "look_at": "Trace the rock outline and the horizon in both panels. They match to the pixel, yet material, era, subject and mood are all new. That is the difference between a filter and structural control.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "Qwen-Image 2512 + InstantX ControlNet Union", "released": "2025-12-31",
 "vram": "~33 GB", "cost": "10.5 s",
 "workflow": "05_qwen_controlnet.json",
 "limits": [
   "Union model: canny, depth and pose in one 3.5 GB file.",
   "Control strength 0.6–0.9 is the usable band; 1.0 fights the prompt, below 0.5 it drifts.",
   "Depth and pose control maps are now available locally — see folder 23."],
 "strong": ["Locking composition while changing everything else",
            "Reusing one layout across many variants", "Architectural and product framing"],
 "weak": ["Templates expect Qwen-Image-Lightning-4steps, a file you do not have",
          "InstantX is weaker on depth than the newer Fun Union ControlNet"],
 "alternatives": ["+ Depth Anything 3 / MoGe / SDPose — installed, generate the control maps (folder 23)",
                  "- Qwen Fun Union ControlNet — not installed, better on depth",
                  "+ LTX IC-LoRA — installed, the video equivalent (untested)"]},

"04-upscaling": {
 "title": "4× upscaling — RealESRGAN",
 "claim": "1664×928 becomes 6656×3712 — 24.7 megapixels from 1.5, in 4.5 seconds. A whole-image view proves nothing, so both panels are the SAME small region cropped at native pixels: left from the source, right from the upscale.",
 "look_at": "The right panel holds four times the pixels for the same piece of the world, so detail appears rather than the picture merely getting bigger. That distinction is the entire point of an upscaler and is invisible at fit-to-screen.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "RealESRGAN x4plus (GAN)", "released": "2026-04-27",
 "vram": "~2 GB", "cost": "4.5 s",
 "workflow": "09_image_upscale.json",
 "limits": [
   "Fixed 4×. For other factors, upscale then downsample.",
   "24.7 MP output is about the practical ceiling before file handling gets painful.",
   "NEVER chain this onto a video frame batch — ImageUpscaleWithModel processes the whole batch at once with no chunking and will OOM the server. Upscale video in small batches.",
   "A GAN sharpens what is there; it does not invent. On faces and text that shows."],
 "strong": ["Very fast", "Predictable, no hallucination", "Tiny VRAM cost"],
 "weak": ["Faces and text — invents nothing, so soft input stays soft",
          "Can look crunchy on smooth gradients"],
 "alternatives": ["+ SeedVR2 — installed, untested; diffusion upscaler, better on faces/text",
                  "+ LTX spatial upscaler — installed, for video latents (folder 14)",
                  "- Topaz / Magnific — cloud API only"]},

"12-segmentation-matting": {
 "title": "Text-prompted segmentation & automatic matting",
 "claim": "The prompt was literally the words “the wristwatch”. No clicking, no box drawing, no mask painting — SAM 3.1 read the phrase and returned the mask. BiRefNet did the portrait with no prompt at all.",
 "look_at": "The magenta panels, not the cutouts. An inverted alpha produces a file that looks COMPLETELY NORMAL in any viewer that ignores alpha — you would have saved the background and thrown away your subject without noticing. Compositing over magenta is the only way to see it.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "SAM 3.1 multiplex · BiRefNet", "released": "2026-04-26 · 2026-05-10",
 "vram": "1.6 GB · 0.4 GB", "cost": "18.1 s · 25.5 s",
 "workflow": "13_sam3_segment.json · 14_birefnet_matte.json",
 "limits": [
   "SAM handles one union mask by default; individual_masks=true gives one per object.",
   "BiRefNet works internally around 1024 px — feeding it 4K buys no extra edge quality.",
   "MASK CONVENTION: both return FOREGROUND masks; JoinImageWithAlpha inverts internally, ImageCompositeMasked does not. Always InvertMask before a join.",
   "SAM3_VideoTrack exists for video tracking — installed, never used."],
 "strong": ["Text-prompted selection with no UI interaction",
            "BiRefNet hair and fine-edge quality", "Both are cheap and fast"],
 "weak": ["BiRefNet cannot choose WHICH object — it takes all salient foreground",
          "SAM needs a threshold tweak for small or occluded objects"],
 "alternatives": ["+ RTDETR — node present, weights missing; needed for multi-person pose",
                  "- SCAIL2 — not installed; character replacement in footage"]},

"23-control-maps": {
 "title": "Control maps — depth, normals and pose",
 "claim": "These are not pictures, they are control signals. Each is fed to a ControlNet or to LTX's IC-LoRA to dictate composition, staging or camera movement in a NEW generation — so you direct a shot instead of re-rolling the dice on it. All four extracted in 1.5 s.",
 "look_at": "Compare depth against normals on the same frame. Depth flattens the jacket into one distance; normals hold the fabric folds, the hull curve and the individual pots on the shelves. That is why you want both.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "Depth Anything 3 · MoGe-2 · SDPose whole-body", "released": "2026-06-12",
 "vram": "1.2 GB · 0.6 GB · 1.8 GB", "cost": "1.5 s for all four",
 "workflow": "27_control_maps.json",
 "limits": [
   "Feed the RAW depth to models; depth_colored is a human-readable visualisation only.",
   "SDPose handles ONE person. Multi-person needs RTDETR weights, which are missing.",
   "normal_opengl for ComfyUI/Blender, normal_directx for engines expecting flipped green — backwards inverts your lighting.",
   "All three also run on a video frame batch, which is what IC-LoRA camera control wants."],
 "strong": ["Fast enough to be free in any pipeline",
            "Normals carry surface relief that depth loses",
            "Depth video → IC-LoRA is the local camera-control route"],
 "weak": ["Single-person pose only",
          "Two dynamic-combo traps: hidden sub-inputs silently drop outputs while reporting success"],
 "alternatives": ["- Lotus depth — not installed, superseded by DA3",
                  "+ MoGe panorama → mesh — installed, untested"]},

"24-outpaint-removal": {
 "title": "Outpainting & object removal",
 "claim": "One model, two jobs. Outpainting extends a 1024² square into a 2048×1024 wide, inventing the beekeeper's torso on one side and a whole apiary on the other. Object removal, on this material, failed — and the failure is kept because it defines when not to use this.",
 "look_at": "For the outpaint: the seam, which normally gives it away. There isn't one. For the removal: it produced a rope ring then a stone ring where the watch was. The mask was verified correct and both prompt conventions were tried.",
 "status": "verified", "verdict": "mixed", "updated": U,
 "model": "FLUX.1 Fill + OneReward fp8", "released": "2025-09-21",
 "vram": "20.8 GB", "cost": "27.0 s outpaint · 22.5 s removal",
 "workflow": "28_flux_outpaint.json · 29_flux_object_removal.json",
 "limits": [
   "feathering 24–48 px. Below that a visible seam; above it the model repaints your original.",
   "FluxGuidance 30 and cfg 1.0 — the Fill model's trained range, not the 4.0 used elsewhere.",
   "noise_mask FALSE for outpainting, TRUE for removal.",
   "REMOVAL RULE: works on a small object in a contextful scene. Fails on the subject of a product shot — there is no background to infer, and the composition itself says an object belongs there. Regenerate the plate empty instead."],
 "strong": ["Outpainting is excellent — grain, light and focus falloff all carry across",
            "Aspect-ratio changes after the fact", "Mask comes free from ImagePadForOutpaint"],
 "weak": ["Object removal on large centred subjects — documented failure",
          "No negative prompt (ConditioningZeroOut manufactures an empty one)"],
 "alternatives": ["+ SAM 3.1 — installed, supplies the removal mask automatically",
                  "- flux1-fill-dev — not installed; 2× the size, worse at removal",
                  "+ VACE — installed, untested; video outpainting"]},

"13-llm-prompt-studio": {
 "title": "Local LLM writes the prompt, the image renders — one graph",
 "claim": "Each started as a single line of about eight words. Qwen3.5-2B expanded it into a full art-directed prompt and Qwen-Image rendered it, in one graph, about six seconds end to end. No API, no key, no copy-paste step.",
 "look_at": "Open the .txt sidecar beside any image — it holds the exact prompt the LLM wrote plus both seeds, so a good accident is reproducible. And look at idea_00003: the astronaut is eating noodles through a sealed visor. Neither model reasons about physical plausibility.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "Qwen3.5-2B + Qwen-Image 2512", "released": "2025-12-31",
 "vram": "4.5 GB (LLM) + 29.6 GB", "cost": "3.0 s prompt · 6.0 s end to end",
 "workflow": "16_llm_to_image.json · scripts/idea.py",
 "limits": [
   "Four instruct LLMs sit in models/text_encoders and cost nothing extra to use.",
   "Gemma-3-12B follows length instructions better than the 2B; slower, and it is also LTX's encoder.",
   "CLIPLoader type must be 'stable_diffusion' for the text-only LLM path — looks wrong, is correct.",
   "sampling_mode sub-inputs are DOTTED keys ('sampling_mode.temperature'). Plain names are rejected.",
   "max_length ceiling on TextGenerate is 32768."],
 "strong": ["Removes the real bottleneck — writing prompts, not GPU time",
            "Re-rolling the LLM seed rewrites the composition, a bigger lever than the image seed",
            "Sidecars make good accidents reproducible"],
 "weak": ["A 2B often undershoots requested length",
          "Never let it write negatives — it enumerates things it then describes"],
 "alternatives": ["+ Gemma-3-12B — installed, smarter, also does vision (folder 26)",
                  "+ TextGenerateLTX2Prompt — installed, video prompts incl. soundscape"]},

"26-vision-caption": {
 "title": "Image to text — the pipeline run backwards",
 "claim": "A vision-language model looks at a picture and writes the prompt that would recreate it, entirely locally, in 7.5 seconds. Reverse-engineer a look from a reference, QA your own renders at scale, or build LoRA training captions — otherwise the most tedious part of training.",
 "look_at": "Read caption.txt against the image. It recovered the weathered hands, honeycomb, shallow depth of field and warm palette — then called the light “a bright, sunny day” when the image is deliberately flat overcast. Vision models read brightness more reliably than quality of light.",
 "status": "verified", "verdict": "mixed", "updated": U,
 "model": "Gemma-3-12B via CLIPLoader type ltxv", "released": "2026-03-05",
 "vram": "9.4 GB", "cost": "7.5 s",
 "workflow": "30_vision_caption.json",
 "limits": [
   "qwen_2.5_vl_7b CRASHES: 'Qwen25_7BVLI_Config has no attribute stop_tokens' (llama.py:883). An upstream ComfyUI bug — every other config defines it. Use Gemma.",
   "type must be 'ltxv' — the loader path LTX uses for its Gemma encoder. Gemma 3 is natively multimodal.",
   "TextGenerate also takes video (an IMAGE batch, subsampled to 1 fps) and audio inputs.",
   "Ask for a PROMPT, not a description — a description says 'a woman is smiling'."],
 "strong": ["Reverse-engineering a reference look into a reusable prompt",
            "Captioning a LoRA dataset at scale", "QA: caption 50 renders, grep for the thing that should be there"],
 "weak": ["Quality of light — reads brightness, not softness or direction",
          "Qwen2.5-VL, the obvious choice, is broken on this build"],
 "alternatives": ["+ Qwen2.5-VL — installed but BROKEN for generation (works for conditioning)",
                  "- Florence-2, JoyCaption — not installed"]},

"16-style-range": {
 "title": "Style range from prompting alone — no LoRAs",
 "claim": "Same heron. Same seed. Byte-identical subject sentence in all twelve prompts. Only the medium clause changed. Twelve renders in 59 seconds, and this is the honest baseline any style LoRA has to beat.",
 "look_at": "The stained-glass one FAILED and is kept on purpose — it put a photoreal heron in FRONT of a stained glass window instead of rendering it AS stained glass. Any medium that is also a plausible object in a scene (neon, mosaic, tapestry, projection) can be misread that way.",
 "status": "verified", "verdict": "mixed", "updated": U,
 "model": "Qwen-Image 2512 + Lightning", "released": "2025-12-31",
 "vram": "29.6 GB", "cost": "58.8 s for twelve (4.9 s each)",
 "workflow": "scripts/sweep.py + sweeps/styles.txt",
 "limits": [
   "Prompting reliably gives you a GENRE. It does not give you: the same look across 200 images with no drift, a specific named artist, or a consistent face.",
   "Those three are what LoRAs are for — see folder 17 and LORAS.md.",
   "Fix a seed when comparing styles or you are measuring two things at once."],
 "strong": ["Deciding a project's look in under a minute",
            "Zero cost — no downloads, no training",
            "Named palettes survive independent generation better than adjectives"],
 "weak": ["Media that are also objects get read as settings",
          "Drift across a long run", "No character consistency"],
 "alternatives": ["+ 2 anime style LoRAs — installed by another session",
                  "+ illustration-1.0-qwen-image — installed, untested",
                  "+ TrainLoraNode — built in; train your own (folder 27)"]},

"17-lora-mechanics": {
 "title": "What a LoRA strength value actually does",
 "claim": "The same prompt, the same seed, the same 4 steps. The ONLY thing that changed across these three renders is the accelerator LoRA strength: 0.0, 1.0, 1.3.",
 "look_at": "The left is what 4 steps looks like without the accelerator — soft, grainy, flat. The right is not “more style”, it is damage: crushed sky, oversharpened edges, streaky rain. Above ~1.1 a LoRA fights the base model instead of steering it.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "Qwen-Image 2512 + Lightning 4-step LoRA", "released": "2025-12-31",
 "vram": "29.6 GB", "cost": "36.3 s for the 5-value sweep",
 "workflow": "scripts/sweep.py",
 "limits": [
   "An accelerator LoRA has ONE correct value — the one it was trained for. It is sampler config, not a taste dial.",
   "Style LoRAs: 0.6–1.0. Stack 2–3 but keep TOTAL strength near 1.0.",
   "Accelerator first in the chain, then styles.",
   "Character/concept LoRAs need a trigger word; without it they barely engage."],
 "strong": ["The cheapest 30 seconds of education about LoRAs available",
            "The lesson generalises from accelerators to style LoRAs"],
 "weak": ["Only demonstrates an accelerator — no style LoRA sweep yet"],
 "alternatives": ["+ 11 LoRAs installed; see LORAS.md and scripts/_lora_audit.py",
                  "+ TrainLoraNode — train your own (folder 27)"]},

"15-product-composite": {
 "title": "Product compositing — new scene, pixel-identical product",
 "claim": "The watch is never regenerated. BiRefNet mattes it, Qwen-Image generates an empty stage, and the two are composited, so every pixel of the product is byte-identical to the original. For a client product with a logo and a serial number that is the difference between usable and unusable.",
 "look_at": "The backdrop was prompted with a hard key from the upper left because the watch is lit from the upper left — compositing does not relight the subject. Also note what is missing: no contact shadow, so the watch floats.",
 "status": "verified", "verdict": "mixed", "updated": U,
 "model": "BiRefNet + Qwen-Image 2512", "released": "2026-05-10",
 "vram": "~30 GB", "cost": "31.7 s",
 "workflow": "19_product_composite.json",
 "limits": [
   "Backdrop dimensions must MATCH the product image — resize_source=false, or it crops.",
   "ImageCompositeMasked takes the FOREGROUND mask directly, unlike JoinImageWithAlpha.",
   "Compositing cannot relight. Match light direction in the backdrop prompt or it reads as fake."],
 "strong": ["Product stays byte-identical — the whole point",
            "One prompt change per campaign", "Fast enough to iterate backdrops"],
 "weak": ["No contact shadow — subject floats",
          "Cannot relight the subject to the new scene"],
 "alternatives": ["+ Qwen-Image-Edit-2509-Relight — INSTALLED, untested; would fix the lighting",
                  "+ Light-Migration LoRA — installed, untested; copies light off a reference",
                  "+ Qwen-Edit 2511 — installed; use when you WANT the subject reinterpreted"]},

# ─────────────────────────── video ───────────────────────────
"05-image-to-video": {
 "title": "Image to video — Wan 2.2, the faithful one",
 "claim": "Animates an exact keyframe without redrawing it. Wan leads the open models on photoreal humans — faces, skin and hair — which is why it stays in the kit despite being 8× slower than LTX.",
 "look_at": "Watch how closely the first frame matches the keyframe it was given. That fidelity is the reason to use Wan: when a shot's art direction is already right, Wan preserves it and LTX reinterprets it.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "Wan 2.2 I2V 14B (high+low noise) + lightx2v 4-step LoRAs", "released": "2025-07-29",
 "vram": "35.4 GB", "cost": "36 s @480p · 129 s @720p/81f · ~555 s @1080p",
 "workflow": "04_wan22_i2v_turbo.json",
 "limits": [
   "16 fps native. Frame counts must be 4n+1: 81 frames = 5.06 s, 121 = 7.6 s.",
   "REALISTIC MAX: about 5 s at 720p per clip. Past ~7 s the subject drifts.",
   "Cost is LINEAR in frames and punishing — unlike LTX, a longer shot costs proportionally more.",
   "16 fps looks like 16 fps. Interpolate to 32 (folder 07) or it reads as cheap.",
   "Two experts (high/low noise) split the step budget 0–2 / 2–4.",
   "Negative prompt MUST contain 'static, still image, frozen' or it may not move."],
 "strong": ["Faithful to the input keyframe", "Best photoreal humans of the open models",
            "Fine-grained motion prompting"],
 "weak": ["Slow — 129 s for 5 s of 720p", "16 fps", "No audio", "Drift past ~7 s"],
 "alternatives": ["+ LTX-2.3 — installed, 8× faster, generates audio (folder 06)",
                  "+ HunyuanVideo 1.5 — installed, untested; physics/motion specialist",
                  "- Wan 2.2 T2V — not installed; text→video with the same strengths"]},

"06-text-to-video-with-audio": {
 "title": "Text to video WITH generated audio — one pass",
 "claim": "LTX-2.3 generates picture and a synced soundtrack in a single forward pass. Nothing else local does this. It is also roughly 8× faster than Wan at 720p, and its cost curve is nearly FLAT in clip length — an 8 s clip costs barely more than a 4 s one.",
 "look_at": "Play with sound on. The audio is not a post-process — footfalls land on feet, rain hits surfaces. It has no idea what a specific named object sounds like, so it is a 'reality bed' you layer designed SFX on top of, not a replacement for sound design.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "LTX-2.3 22B (dev fp8) + distilled LoRA", "released": "2026-03-05",
 "vram": "44.0 GB", "cost": "13.5 s @768×512 · 16.5 s @1280×704 · 13.7 s for 8 s",
 "workflow": "11_ltx23_t2v_audio.json · 12_ltx23_i2v_audio.json",
 "limits": [
   "24 fps. Frame counts must be 8n+1: 97 = 4.04 s, 193 = 8.04 s, 241 = 10.04 s.",
   "REALISTIC MAX per clip: about 10 s. Beyond that chain shots with from_prev, or use LTXVContextWindows (installed, untested).",
   "Cost curve is FLAT: 193 frames costs 13.7 s vs 13.5 s for 97. Long shots are nearly free; extra SHOTS are what cost.",
   "Height snaps to a multiple of 32 — ask for 720, get 704.",
   "44 GB VRAM vs 32 available: it offloads between text, video and audio stages.",
   "MIXING ENGINES: LTX is 24 fps, Wan is 16. One will need retiming — decide per film."],
 "strong": ["Native audio+video in one pass — unique locally",
            "Flat cost curve makes long takes cheap", "8× faster than Wan at 720p",
            "IC-LoRA and ID-LoRA extend it to control and identity"],
 "weak": ["Less faithful to an exact keyframe than Wan",
          "Audio has no semantic knowledge of specific objects",
          "Offloads on every run at 44 GB"],
 "alternatives": ["+ Two-stage upscale path — installed (folder 14)",
                  "+ Wan 2.2 I2V — installed, for exact keyframes (folder 05)",
                  "+ HunyuanVideo 1.5 — installed, untested; better physics"]},

"14-ltx-two-stage-upscale": {
 "title": "LTX-2.3 run the way it was designed — two-stage",
 "claim": "Sample the whole clip at half resolution, upsample the LATENT 2×, then re-denoise at partial strength starting from sigma 0.85 rather than 1.0. Result: 1280×704, 97 frames, with stereo audio generated in the same pass, in 21 seconds.",
 "look_at": "Play against 06's ltx23_av_00002 — the single-stage version at the same resolution in 16.5 s. The extra 4.5 s buys the refine pass. Clear on detailed subjects; not on soft foggy material, which is worth knowing before spending it.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "LTX-2.3 22B + spatial upscaler ×2", "released": "2026-03-05",
 "vram": "44.0 GB", "cost": "21.0 s",
 "workflow": "17_ltx23_t2v_upscaled.json",
 "limits": [
   "Stage-2 sigmas MUST start below 1.0 (0.85 here). At 1.0 you discard stage 1 entirely.",
   "Decoding straight off the upsampler without the refine pass gives mush.",
   "Multiples of 32 at BOTH stages: 640×352 → 1280×704 works; 768×432 does not.",
   "Use VAEDecodeTiled, not VAEDecode — and temporal_size 4096 to DISABLE temporal tiling, which seams on motion."],
 "strong": ["The correct quality path for LTX", "Only +4.5 s over single-stage",
            "Same trick applies to stills"],
 "weak": ["Marginal on low-detail material", "Adds graph complexity"],
 "alternatives": ["+ SeedVR2 — installed, untested; pixel-space diffusion upscale",
                  "+ RealESRGAN — installed, but OOMs on frame batches (folder 04)"]},

"18-audio-to-video": {
 "title": "Audio-driven video — the one thing nothing else local does",
 "claim": "A still portrait and a real narration track go in; video comes out where the mouth moves to match the audio. Note the direction: folders 06 and 14 GENERATE audio alongside video, this one is DRIVEN BY audio you already had.",
 "look_at": "Four sampled frames with clearly different mouth shapes while the face holds identity. The mechanism is one float: the audio latent is pinned with an all-zero noise mask, so the model can only satisfy its objective by generating video that fits the fixed audio.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "LTX-2.3 22B (ia2v path)", "released": "2026-03-09",
 "vram": "40.0 GB", "cost": "23.0 s for 1280×704, 97 frames",
 "workflow": "20_ltx_audio_to_video.json",
 "limits": [
   "FRAME MATH IS MANDATORY: frames = fps × audio_duration + 1. Mismatch and the latents differ in length and concat fails.",
   "Your clip must be at least as long as the trim duration.",
   "Same ~10 s per-clip ceiling as the rest of LTX.",
   "Front-facing subject with a visible mouth. A profile or downward gaze gives almost nothing."],
 "strong": ["Talking-head inserts and presenter cutaways",
            "Music-driven motion when you swap speech for a track",
            "The zero-mask pin generalises to anything you want held fixed"],
 "weak": ["NOT phoneme-accurate lip-sync — motion correlated with audio",
          "Will not survive a tight close-up against known speech"],
 "alternatives": ["+ ID-LoRA — installed, untested; adds identity lock for dialogue",
                  "- InfiniteTalk, HuMo — not installed"]},

"07-frame-interpolation": {
 "title": "Frame interpolation — 16 fps to 32 fps",
 "claim": "FILM invents a new frame between every pair of existing ones, taking 81 frames to 161. It is not frame duplication: each inserted frame is generated content showing the subject part-way between its two neighbours.",
 "look_at": "Smoothness cannot honestly be shown in a still — play the file. What the strip shows is consecutive sampled frames with no stutter or repeats, which is what removes the 16 fps tell from Wan footage.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "FILM (film_net_fp16)", "released": "2026-04-27",
 "vram": "0.1 GB", "cost": "7.5 s per clip",
 "workflow": "07_video_interpolate.json",
 "limits": [
   "Multiplier 2–16. 2× is the safe default; 4× plus setpts gives true slow motion.",
   "NEVER chain a GAN upscale after interpolation — 161 frames at 5120×2880 float32 is ~28 GB and OOM-killed the server once already.",
   "Struggles with very fast motion and occlusion — artefacts appear where objects cross."],
 "strong": ["Removes the 16 fps tell from Wan output", "Real slow motion, not duplicated frames",
            "Tiny model, tiny cost"],
 "weak": ["Occlusion artefacts on fast motion", "Not wired into any of the film scripts yet"],
 "alternatives": ["+ ffmpeg minterpolate — no model needed, lower quality",
                  "+ LTX at 24 fps natively — sidesteps the problem"]},

"21-3d-generation": {
 "title": "3D from a single image — mesh and Gaussian splat",
 "claim": "One flat picture in. Out comes a real polygon mesh (187,314 vertices, 525,708 triangles, valid glTF openable in Blender) and a Gaussian splat rendered as a 360° turntable. 19.5 seconds each. This modality did not exist on this box before 2026-07-29.",
 "look_at": "The turntable video, not this card. A still proves nothing about 3D. Play triposplat_orbit and watch the BACK of the owl — which the model never saw and had to invent — stay coherent all the way round.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "Hunyuan3D 2.1 (mesh) · TripoSplat (splat)", "released": "2025-03-01 · 2026-06-02",
 "vram": "4.6 GB · 3.7 GB", "cost": "19.5 s each",
 "workflow": "24_hunyuan3d_mesh.json · 25_triposplat.json",
 "limits": [
   "The image IS the prompt — no text conditioning exists in either graph.",
   "MESH IS GEOMETRY ONLY: POSITION attribute and nothing else. No vertex colour, no normals, no UVs, no texture. Blender for shade-smooth, decimate, unwrap, bake.",
   "525k triangles from a 1024px input is unwieldy — decimate to 5–10% first.",
   "Splats are NOT meshes: no UVs, no faces. Great for renders, unusable as a game asset.",
   "octree_resolution 256 is the mesh detail dial; 384 is much finer and much heavier.",
   "Transparent, mirrored and very dark objects defeat single-view depth."],
 "strong": ["Cheapest new modality on the box — 9.7 GB for both",
            "TripoSplat won preference tests (Elo 1137 vs 996)",
            "Turntable render communicates the result better than any still"],
 "weak": ["No texture or UVs from either", "Single view means the back is invented",
          "Not production assets without Blender work"],
 "alternatives": ["+ MoGe panorama → mesh — installed, untested",
                  "- Hunyuan3D 2.5 / multiview — not installed; multiview is more accurate",
                  "- Rigging and animation — not solved in ComfyUI at all"]},

# ─────────────────────────── audio ───────────────────────────
"08-music": {
 "title": "Text to music with vocals — ACE-Step 1.5",
 "claim": "Sixty seconds of finished, structured music from a tag list, in about eight seconds of GPU time. Tags control the music; a separate lyrics field with [verse]/[chorus] tags controls the words AND the arrangement.",
 "look_at": "Listen for structure, not timbre. bpm, keyscale and timesignature are real conditioning rather than metadata — D minor at 64 bpm genuinely produces a slow minor-key cue. Folder 19 goes further and has an LLM write the lyrics first.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "ACE-Step 1.5 Turbo", "released": "2026-04-10",
 "vram": "18.5 GB", "cost": "7.6 s per 60 s of music",
 "workflow": "06_acestep_music.json",
 "limits": [
   "Output is 48 kHz stereo, measured at −17.9 LUFS with 14.7 LU range — cinematic but needs a loudness pass.",
   "REALISTIC MAX: 120 s default, a few minutes practical. Generate LONGER than picture and trim in — asking for an exact length gives an abrupt ending with no tail.",
   "No hit-point conditioning. It cannot spot to picture. Butt-join two cues with acrossfade at the hit, or cut picture to music.",
   "duration on the encoder and seconds on the latent are SEPARATE fields with no cross-validation.",
   "Two different cfgs on purpose: 2.0 on the encoder, 1.0 on the KSampler (turbo model)."],
 "strong": ["60 s of scored music in under 8 s", "Genuine song structure from tags",
            "bpm/key/time-signature are real controls"],
 "weak": ["Cannot hit a timecode", "A generated song is ATOMIC — no stems, so you cannot duck its vocal",
          "Wide dynamic range vanishes under ambience without riding it"],
 "alternatives": ["+ ACE-Step 1 — installed; the ONLY way to remix (folder 25)",
                  "+ Stable Audio 3 — installed, for SFX not songs (folder 09)",
                  "- Demucs — not installed; would give stems, needs its own venv"]},

"25-music-remix": {
 "title": "Music to music — remix, restyle, extend an existing track",
 "claim": "Audio img2img. The source is encoded to a latent and only PARTIALLY denoised (0.32) against new tags, so the result keeps the original's bones — length, structure, broad harmonic shape — while instrumentation and character change. 6.0 s for 30 s of music.",
 "look_at": "Play source_original then remix_piano back to back. This is what makes film scoring practical: generate a theme once, remix at 0.25–0.35 per act, and get variations that are recognisably the same theme — which three separately generated cues never are.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "ACE-Step 1 (3.5B) — the v1 checkpoint", "released": "2025-03-01",
 "vram": "7.2 GB", "cost": "6.0 s for 30 s",
 "workflow": "31_acestep_remix.json",
 "limits": [
   "ACE-Step 1.5 CANNOT do this at any setting. Music-to-music exists only in v1.",
   "denoise is the whole control: 0.2 gentle re-voicing, 0.3–0.4 new arrangement, 0.6+ you have thrown the original away.",
   "Source length sets output length — there is no empty latent. To EXTEND, pad with silence first.",
   "v1 outputs 44.1 kHz; 1.5 outputs 48 kHz. Another entry in the sample-rate zoo.",
   "v1 has NO bpm/keyscale/timesignature — steer with tags only, and keep them near the source's real tempo."],
 "strong": ["Theme-and-variation scoring, which is what film actually needs",
            "Different architecture from 1.5 — single checkpoint, simpler graph"],
 "weak": ["Older model, lower fidelity than 1.5", "No structured conditioning"],
 "alternatives": ["+ ACE-Step 1.5 — installed, better quality, no remix (folder 08)"]},

"09-sound-effects": {
 "title": "Sound design — SFX, foley and ambience",
 "claim": "Named, separable sound elements generated one at a time. Ambience is the highest-value layer in the whole audio stack: nine independently generated shots share no room, and a continuous bed of room tone spanning the cuts asserts that they do — the ear believes the room over the eye.",
 "look_at": "Generate each element separately and layer in ffmpeg. One prompt asking for wind AND waves AND a bell returns a mush of all three at wrong relative levels. These are 44.1 kHz while ACE-Step is 48 and Chatterbox is 24 kHz mono — mix in ffmpeg, which resamples correctly; ComfyUI's AudioMerge does not.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "Stable Audio 3 Medium", "released": "2026-05-20",
 "vram": "14.6 GB", "cost": "1.7–3.0 s per element",
 "workflow": "10_stableaudio_sfx.json",
 "limits": [
   "8 steps with the lcm sampler — cheaper than the music model.",
   "Duration lands ~30 ms short of request (19.969 s for 20).",
   "REALISTIC MAX: tens of seconds. For a long bed, generate 30–50 s and loop with a crossfade.",
   "Prompt in field-recording register and always append 'no music, no speech'."],
 "strong": ["Ambience beds — the cheapest continuity tool in film",
            "Very fast", "Named elements stay independently levelable"],
 "weak": ["Not songs — use ACE-Step", "Sample rate differs from every other generator here"],
 "alternatives": ["+ LTX in-pass audio — free correlation, no semantic knowledge (folder 06)",
                  "+ ffmpeg — loudnorm, sidechaincompress, alimiter all present and unused"]},

"10-voice": {
 "title": "Local text-to-speech with distinct characters",
 "claim": "Narration and character dialogue generated entirely on the box — no API, no key. The emo_* files are one engine at different expressiveness settings; the char_* files are per-character voices.",
 "look_at": "The honest limitation: ChatterboxTTS ships exactly ONE voice pack, so characters here are differentiated by pitch-shifting. That is a cartoon solution and will not survive a dramatic two-hander. The real fix costs zero GB — the node has an unused optional audio_prompt input for zero-shot cloning.",
 "status": "verified", "verdict": "mixed", "updated": U,
 "model": "Chatterbox TTS (ResembleAI)", "released": "2026-07-29",
 "vram": "3.0 GB", "cost": "~5 s per line",
 "workflow": "08_chatterbox_tts.json",
 "limits": [
   "24 kHz MONO — the odd one out in the audio chain.",
   "25 tokens ≈ 1 s; hard cap 4096 tokens ≈ 163 s per call. Long VO must be chunked.",
   "exaggeration floor is 0.25 — an out-of-range value is a hard HTTP 500 that aborts the run.",
   "cfg_weight 0.4 for documentary flatness, 0.7 temperature."],
 "strong": ["Fully local, no API", "Voice CLONING is available and unwired",
            "Fast enough to iterate line readings"],
 "weak": ["One voice pack — characters are currently pitch-shifted",
          "Cannot force a line to an exact duration, which matters when cutting to picture"],
 "alternatives": ["+ ChatterboxVC — installed; convert timbre after generating",
                  "- IndexTTS 2 — not installed; has FORCED DURATION, the one thing missing",
                  "- VibeVoice — not recommended, provenance concerns"]},

"19-llm-lyrics-song": {
 "title": "One line of intent to a finished sung song",
 "claim": "The input was: “a night shift worker walking home at dawn past a closed fairground”. Qwen3.5-2B wrote structured lyrics, ACE-Step composed and sang them. Sixty seconds of music in twelve.",
 "look_at": "The [verse]/[chorus] tags are load-bearing, not decorative — ACE-Step arranges to them, and without them you get a shapeless wash with no chorus lift. One caveat I cannot resolve: I generated and verified the file but cannot listen to it, so whether the diction is intelligible is your call.",
 "status": "verified", "verdict": "works", "updated": U,
 "model": "Qwen3.5-2B + ACE-Step 1.5 Turbo", "released": "2026-04-10",
 "vram": "4.5 + 18.5 GB", "cost": "12.0 s for 60 s",
 "workflow": "21_llm_lyrics_to_song.json",
 "limits": [
   "The official split_llm template wants qwen_4b_ace15, a download you do not have. This routes your existing Qwen3.5-2B into the lyrics field instead — same outcome, zero GB.",
   "generate_audio_codes must stay TRUE for vocals; false gives an instrumental regardless of lyrics.",
   "Empty lyrics (not the codes flag) is the correct switch for an instrumental."],
 "strong": ["Idea to finished song with no human writing step",
            "Structure tags give real arrangement"],
 "weak": ["Diction is the usual weak point of this model class — unverified here"],
 "alternatives": ["+ Write lyrics by hand and use folder 08",
                  "- qwen_4b_ace15 — not installed; the official LLM-split path"]},

# ─────────────── not yet explored ───────────────
"27-lora-training": {
 "title": "Train your own LoRA — on this box, no extra tooling",
 "claim": "ComfyUI 0.28.0 has TrainLoraNode built in. No Kohya, no OneTrainer, no second Python environment. This is the only technique that gives you BOTH a consistent character and a range of performance, and it is the largest untouched capability here.",
 "look_at": "Nothing yet — this folder is a plan, not a result. The graph is LoadImageTextDataSetFromFolder → MakeTrainingDataset → TrainLoraNode → LoraSave. Note LORAS.md originally named a node that does not exist; the list above is the verified one.",
 "status": "not-explored", "verdict": "planned", "updated": U,
 "model": "TrainLoraNode (built in)", "released": "with ComfyUI 0.28.0",
 "vram": "~30 GB (gradient_checkpointing + offloading)",
 "cost": "an evening for a first run — no measured timings yet",
 "workflow": "not built yet",
 "limits": [
   "20–30 images for a character. More is not better; CONSISTENT is better.",
   "rank 32 for a character, 8–16 for a style. steps ≈ 100 per image, so ~2000–3000.",
   "learning_rate 2e-4 to 3e-4 at rank 32 (the 5e-4 default suits rank 8–16).",
   "batch_size 1 + grad_accumulation_steps 4–8 for an effective batch without the VRAM.",
   "bucket_mode TRUE for a character set so you can mix CU/medium/full-body framing.",
   "Memory ladder: gradient_checkpointing (default on) → offloading → quantized_backward last.",
   "VIDEO LoRA training is also available (LoadVideoTextDataSetFromFolder) and undocumented in the kit."],
 "strong": ["The only route to identity AND performance range",
            "Also extracts a LoRA from any full fine-tune via LoraSave model_diff",
            "Can resume or continue an existing LoRA via existing_lora"],
 "weak": ["Untested here — no measured timings, no verified graph",
          "Caption discipline is the hard part: describe everything EXCEPT the face"],
 "next_steps": [
   "Build workflows/32_train_character_lora.json with the verified four-node chain.",
   "Bootstrap a dataset: render ~25 stills of one character with 01/02, cull hard to the ~20 that agree.",
   "Caption with folder 26's vision model — that is the tedious part, automated.",
   "Train rank 32, ~2000 steps; validate at strength 0.6 / 0.8 / 1.0. Only-works-at-1.0 means overfitted.",
   "Then use it across a film to fix the identity-drift problem in FILM-CRAFT-AUDIT.md."]},

"28-vace-video-editing": {
 "title": "Video to video — restyle, inpaint and outpaint existing footage",
 "claim": "Wan 2.1 VACE 14B is three capabilities in one model: restyle a clip, remove or replace objects inside it, and extend its frame. It is the only real answer on this box to shot-to-shot look matching, which FILM-CRAFT-AUDIT names as a structural gap.",
 "look_at": "Nothing yet. WanVaceToVideo is live and takes control_video, control_masks and reference_image — that combination is effectively the matched-coverage node the cinematography audit said was missing.",
 "status": "installed-untested", "verdict": "planned", "updated": U,
 "model": "Wan 2.1 VACE 14B fp16", "released": "2025-05-21",
 "vram": "53.8 GB", "cost": "unmeasured — expect heavy offload",
 "workflow": "not built yet",
 "limits": [
   "53.8 GB wanted against 32 GB — the heaviest model on the box. Expect substantial offload.",
   "Six video_wan_vace_* templates exist; all were dead until this download.",
   "Templates want umt5_xxl_fp16 (10.6 GB), not installed — your fp8 encoder should substitute.",
   "video_wan_vace_flf2v additionally wants a lightx2v 480p LoRA that is missing."],
 "strong": ["Video restyle, inpaint AND outpaint from one model",
            "reference_image input is the closest thing to matched coverage",
            "Frame extension can change a finished clip's aspect ratio"],
 "weak": ["Largest VRAM footprint here", "Wan 2.1 generation, older than 2.2",
          "Completely unverified"],
 "next_steps": [
   "Build a v2v restyle workflow first — it is the highest-value of the three.",
   "Test the fp8 encoder substitution before assuming it works.",
   "Then video inpainting, using SAM3_VideoTrack (installed, unused) for the masks.",
   "Measure the offload cost honestly — this may be too slow to be practical at 53.8 GB."]},

"29-hunyuanvideo": {
 "title": "HunyuanVideo 1.5 — the physics and motion specialist",
 "claim": "The third video model, and it is complementary rather than competing: LTX owns audio and speed, Wan owns photoreal humans, HunyuanVideo owns believable MOTION — fluid dynamics, cloth, smoke, object interactions. It also has a native 1080p super-resolution stage.",
 "look_at": "Nothing yet. All seven files are installed and verified visible, including the VAE and byt5 encoder without which the 46.5 GB of DiTs are dead weight.",
 "status": "installed-untested", "verdict": "planned", "updated": U,
 "model": "HunyuanVideo 1.5 720p T2V + I2V + 1080p SR", "released": "2025-11-21",
 "vram": "42.3 GB", "cost": "unmeasured",
 "workflow": "not built yet",
 "limits": [
   "8.3B parameters — slimmer than its predecessor, ~14 GB with offloading.",
   "The 1080p SR stage is the only native 1080p path here that is not a 555 s Wan render.",
   "No FLF node exists for Hunyuan — it has ImageToVideo only, so it is not an editing tool.",
   "Needs sigclip_vision for the i2v path (installed)."],
 "strong": ["Best physics of the open models — water, smoke, fire, cloth",
            "Native 1080p via the SR stage", "Fills the one gap LTX and Wan share"],
 "weak": ["Untested here", "No first/last-frame control", "Another 42 GB model to offload"],
 "next_steps": [
   "Build a T2V workflow and test on a deliberately physics-heavy prompt — pouring liquid, cloth in wind, smoke.",
   "A/B the same prompt against LTX-2.3 and Wan 2.2 to see whether the motion claim holds on this hardware.",
   "Then wire the 1080p SR stage and measure it against upscaling a 720p LTX clip instead."]},

"30-camera-control": {
 "title": "Camera control for video — IC-LoRA driven by depth",
 "claim": "The highest-value zero-download build on the box. Feed a control video — a phone clip, a Blender flythrough — through Depth Anything 3, and LTX-2.3's IC-LoRA will follow that camera move. It turns 'slow push in' from a hopeful prompt phrase into an actual trajectory.",
 "look_at": "Nothing yet. Every weight is present: the IC-LoRA, DA3, MoGe, and GetICLoRAParameters + LTXVAddGuide are live nodes. This is plumbing, not shopping.",
 "status": "installed-untested", "verdict": "planned", "updated": U,
 "model": "LTX-2.3 IC-LoRA union control + Depth Anything 3", "released": "2026-04-25",
 "vram": "38.1 GB", "cost": "unmeasured — expect ~21 s like other LTX two-stage work",
 "workflow": "not built yet",
 "limits": [
   "The template hardcodes ltx-2.3-22b-distilled-fp8, which is NOT installed and was skipped deliberately (27.5 GB). Repoint to dev-fp8 + the distilled LoRA at 0.5, as workflows 11/12/17 already do. A rewire, not a download.",
   "Reference downscale is baked at 0.5 — it is in the filename. Do not change it.",
   "lora_strength is the identity-vs-freedom dial.",
   "Template sampler settings: 8 steps, cfg 1, euler_ancestral, linear_quadratic."],
 "strong": ["Arbitrary camera geometry, not just the moves a prompt can name",
            "Also accepts pose and edge control, not only depth",
            "Zero downloads"],
 "weak": ["Needs a control video, so you must shoot or render one",
          "Untested; the template needs repointing before it will even load"],
 "next_steps": [
   "Build 33_ltx_ic_control.json: control video → DA3Inference → DA3Render depth → LTXVAddGuide + GetICLoRAParameters → IC-LoRA at 1.0 on dev-fp8 + distilled 0.5.",
   "Shoot a 5 s phone clip of a dolly move as the control source.",
   "Then run a camera-move sweep with sweep.py to find which prompt phrasings actually land — there is no measured evidence on this box yet."]},

"31-character-identity": {
 "title": "Character identity locked across shots — ID-LoRA",
 "claim": "Identity drift is the single thing separating an AI short from a real one. An audience forgives soft motion and flat grading; it does not forgive a face that is 90% the same. LTX-2.3's ID-LoRA locks a character across shots, and all five required models are already here.",
 "look_at": "Nothing yet. Be clear-eyed about what it is: 'talkvid' means it was trained on TALKING video, driven by a reference identity image plus reference audio. It is identity lock for dialogue coverage, not for arbitrary wide shots.",
 "status": "installed-untested", "verdict": "planned", "updated": U,
 "model": "ltx-2.3-id-lora-talkvid-3k", "released": "2026-03-27",
 "vram": "40.5 GB", "cost": "unmeasured",
 "workflow": "not built yet",
 "limits": [
   "ID-LoRA at 1.0 stacked on the distilled LoRA at 0.5.",
   "Prompt MUST use tagged sections: [VISUAL]: / [SPEECH]: / [SOUNDS]:.",
   "Dialogue coverage only — not a general 'same character in a landscape' lock.",
   "Locking identity fights performance: high strength gives a consistent character who cannot act."],
 "strong": ["Directly attacks the biggest gap in multi-shot narrative",
            "Slots into cartoon.py, which already renders a voice clip per line — exactly the reference audio this wants"],
 "weak": ["Talking-head shots only", "Untested",
          "The whole face-embedding family (IPAdapter/PuLID/InstantID) is absent as an alternative"],
 "next_steps": [
   "Build 34_ltx_id_lora.json and test with one of folder 10's character voice clips as the reference audio.",
   "Then wire cartoon.py's per-line voice stage into it — that is the pipeline win.",
   "Compare against training a character LoRA (folder 27); they solve overlapping problems differently."]},

"32-seedvr2-upscale": {
 "title": "Diffusion upscaling — SeedVR2 vs the GAN",
 "claim": "RealESRGAN sharpens what is there; a diffusion upscaler INVENTS plausible detail. On faces and text — exactly where folder 04's GAN is weakest — that difference is decisive. Newest model on the box, released six weeks ago.",
 "look_at": "Nothing yet. The natural demo is a 1:1 crop A/B against folder 04 using the same source region, which the card renderer already supports via the crop panel type.",
 "status": "installed-untested", "verdict": "planned", "updated": U,
 "model": "SeedVR2 3B int8", "released": "2026-07-13",
 "vram": "3.7 GB", "cost": "unmeasured",
 "workflow": "not built yet",
 "limits": [
   "Built for VIDEO as well as stills, unlike RealESRGAN which OOMs on frame batches.",
   "SeedVR2PostProcessing does lab colour correction against the resized original — use it or colour drifts.",
   "Diffusion upscaling hallucinates. On documentary or product work that is a liability, not a feature."],
 "strong": ["Faces and text — the GAN's weak spot", "Handles video natively",
            "Small at 3.7 GB"],
 "weak": ["Invents detail that was not there", "Slower than a GAN", "Untested"],
 "next_steps": [
   "Build 35_seedvr2_upscale.json and run it on folder 04's exact source image.",
   "Render a crop-panel card A/B'ing GAN vs diffusion on the same region — the comparison IS the demo.",
   "Test on a face crop specifically, since that is where the claim lives."]},

"33-zimage-turbo": {
 "title": "Z-Image Turbo — one-second ideation",
 "claim": "Roughly a second per image. That is not a marginal speedup over Qwen's 4.5 s, it is a different activity: at one second you browse ideas instead of committing to them, then re-render the winner properly.",
 "look_at": "Nothing yet. The interesting test is not quality in isolation but whether 1 s changes how you work — a 40-image concept sheet in under a minute versus three minutes.",
 "status": "installed-untested", "verdict": "planned", "updated": U,
 "model": "Z-Image Turbo (bf16) + qwen_3_4b encoder", "released": "2025-11-27",
 "vram": "19.4 GB", "cost": "unmeasured — target ~1 s",
 "workflow": "not built yet",
 "limits": [
   "Optimised for bilingual text including Chinese.",
   "Fewer community LoRAs and fine-tunes than Qwen or Flux.",
   "Lower ceiling than Qwen 2512 — this is an ideation tool, not a finishing one."],
 "strong": ["Speed — a different way of working, not just faster",
            "Bilingual text rendering", "19.4 GB fits without heavy offload"],
 "weak": ["Thin ecosystem", "Not a finishing model", "Untested"],
 "next_steps": [
   "Build 36_zimage_turbo.json and measure the real per-image time on this box.",
   "Run the same 12-line styles.txt sweep through it and compare against folder 16 for both time and quality.",
   "If it is genuinely ~1 s, wire it into idea.py as a --fast mode."]},

"34-flf2v-transitions": {
 "title": "First/last-frame video — controlled transitions and match cuts",
 "claim": "Give the model a start frame AND an end frame and it generates the motion between them. This is the missing tool for deliberate transitions and cut-on-action, and it needs ZERO downloads — every weight for the Wan path is already installed.",
 "look_at": "Nothing yet. FILM-CRAFT-AUDIT ranks this among the top zero-cost builds, and templates-6-key-frames chains five of them into a long take, also on installed weights.",
 "status": "installed-untested", "verdict": "planned", "updated": U,
 "model": "Wan 2.2 FLF2V · LTX-2.3 FLF2V", "released": "2025-07-29 · 2026-03-05",
 "vram": "35.4 GB · 44.0 GB", "cost": "unmeasured — Wan ~129 s, LTX ~16.5 s expected",
 "workflow": "not built yet",
 "limits": [
   "Wan path: WanFirstLastFrameToVideo, all six weights present. Leave clip_vision inputs unconnected — that folder is empty.",
   "LTX path is ~8× cheaper and comes with audio, but the template hardcodes the distilled checkpoint you skipped — repoint to dev-fp8 + distilled LoRA 0.5.",
   "Frame quanta still apply: Wan 4n+1 at 16 fps, LTX 8n+1 at 24 fps.",
   "A bridge clip generated in the SAME model family as your footage will look-match; mixing families will not."],
 "strong": ["Controlled A→B transitions instead of hoping a prompt lands",
            "Match cuts and cut-on-action become possible",
            "Zero downloads on the Wan path"],
 "weak": ["Untested", "Needs both endpoint frames to exist first",
          "Does not propagate a LOOK, only pins two endpoints"],
 "next_steps": [
   "Build the Wan version first — it look-matches existing footage and needs no repointing.",
   "Then the LTX version for 8× the speed plus audio.",
   "Then test templates-6-key-frames for genuine long takes.",
   "Pair with the trim handles that epic.py still needs before match cuts actually work."]},
}


# Panels kept separate from the prose so the two can be edited independently.
# `crop` = [cx, cy, frac] gives a 1:1 pixel crop (for upscalers); `frames` = N gives
# a video strip (for motion). `file` may point at ../another-folder/.
PANELS = {
"01-text-to-image": [
  {"file": "typography_00001_.png", "label": "In-image text", "note": "the thing other models fail"},
  {"file": "product_00001_.png", "label": "Product", "note": "1328×1328"},
  {"file": "qwen_turbo_00001_.png", "label": "Landscape — 4 steps", "note": "1664×928 in 4.5 s"}],
"22-flux2": [{"file": "flux2_beekeeper_00001_.png", "label": "FLUX.2 dev — 8 steps, 1024²"}],
"02-image-editing": [
  {"file": "../01-text-to-image/qwen_turbo_00001_.png", "label": "ORIGINAL"},
  {"file": "qwen_edit_00001_.png", "label": "“deep winter”", "note": "snow, ice floes"},
  {"file": "relight_goldenhour_00001_.png", "label": "“golden hour”", "note": "same geometry, new light"},
  {"file": "style_watercolour_00001_.png", "label": "“watercolour”", "note": "medium changed, staging kept"}],
"20-qwen-edit-2511": [
  {"file": "../01-text-to-image/portrait_00001_.png", "label": "INPUT 1 — generated earlier"},
  {"file": "../18-audio-to-video/driver_portrait_00001_.png", "label": "INPUT 2 — different session"},
  {"file": "edit2511_two_people_00001_.png", "label": "OUTPUT — one photograph", "note": "faces distinct, light reconciled"}],
"03-controlnet": [
  {"file": "qwen_controlnet_edgemap_00001_.png", "label": "CONTROL — canny edges", "note": "from the lighthouse"},
  {"file": "qwen_controlnet_00001_.png", "label": "OUTPUT — new subject, same structure"}],
"04-upscaling": [
  {"file": "source_1664x928.png", "crop": [0.5, 0.42, 0.16], "label": "SOURCE — 1:1 crop", "note": "from 1664×928"},
  {"file": "upscaled_4x_00001_.png", "crop": [0.5, 0.42, 0.16], "label": "UPSCALED — same region, 1:1", "note": "from 6656×3712"}],
"12-segmentation-matting": [
  {"file": "sam3_proof_on_magenta_00001_.png", "label": "SAM 3.1 — prompt: “the wristwatch”", "note": "no clicks"},
  {"file": "birefnet_proof_on_magenta_00001_.png", "label": "BiRefNet — no prompt at all", "note": "note the hair edges"}],
"23-control-maps": [
  {"file": "../12-segmentation-matting/birefnet_cutout_rgba_00001_.png", "label": "SOURCE PHOTO"},
  {"file": "depth_colored_00001_.png", "label": "DEPTH", "note": "colourised for humans"},
  {"file": "normals_moge_00001_.png", "label": "NORMALS", "note": "holds relief depth loses"},
  {"file": "pose_sdpose_00001_.png", "label": "POSE", "note": "body, hands, face, feet"}],
"24-outpaint-removal": [
  {"file": "../22-flux2/flux2_beekeeper_00001_.png", "label": "INPUT — 1024×1024", "note": "cropped at the hands"},
  {"file": "outpaint_wide_00001_.png", "label": "OUTPUT — 2048×1024", "note": "both thirds invented"},
  {"file": "removed_object_v2_00001_.png", "label": "REMOVAL — failed", "note": "invented a ring where the watch was"}],
"13-llm-prompt-studio": [
  {"file": "idea_00001_.png", "label": "“lantern-keeper feeding moths to a lighthouse lamp”"},
  {"file": "idea_00002_.png", "label": "“cartographer mapping a city that rearranges nightly”"},
  {"file": "idea_00003_.png", "label": "“orbital mechanic eating noodles in a solar storm”", "note": "eating through a sealed visor"}],
"26-vision-caption": [
  {"file": "source_image.png", "label": "INPUT — the image it was shown", "note": "caption.txt holds what it wrote"}],
"16-style-range": [
  {"file": "style_03_ukiyo-e-woodblock_00001_.png", "label": "ukiyo-e — works", "note": "keyline, flat colour, paper grain"},
  {"file": "style_08_technical-blueprint_00001_.png", "label": "blueprint — works", "note": "construction lines"},
  {"file": "style_09_stained-glass_00001_.png", "label": "stained glass — FAILED", "note": "read as a setting, not a medium"}],
"17-lora-mechanics": [
  {"file": "strength_01_0-0_00001_.png", "label": "strength 0.0 — LoRA off", "note": "needed 20 steps, got 4"},
  {"file": "strength_04_1-0_00001_.png", "label": "strength 1.0 — CORRECT", "note": "the design point"},
  {"file": "strength_05_1-3_00001_.png", "label": "strength 1.3 — overcooked", "note": "damage, not more style"}],
"15-product-composite": [
  {"file": "../01-text-to-image/product_00001_.png", "label": "PRODUCT — as shot"},
  {"file": "backdrop_only_00001_.png", "label": "STAGE — generated empty", "note": "key light placed to match"},
  {"file": "product_composite_00001_.png", "label": "COMPOSITE", "note": "product untouched; no contact shadow"}],
"05-image-to-video": [
  {"file": "wan22_i2v_00002_.mp4", "frames": 5, "label": "Wan 2.2 I2V", "note": "16 fps, 81 frames = 5.06 s"}],
"06-text-to-video-with-audio": [
  {"file": "ltx23_av_00002_.mp4", "frames": 5, "label": "LTX-2.3 — 1280×704 + generated audio", "note": "16.5 s single-stage"}],
"14-ltx-two-stage-upscale": [
  {"file": "ltx23_2stage_00001_.mp4", "frames": 5, "label": "TWO-STAGE — 1280×704 + audio", "note": "sigmas start at 0.85"}],
"18-audio-to-video": [
  {"file": "driver_portrait_00001_.png", "label": "INPUT — one still"},
  {"file": "ltx_ia2v_speech_00001_.mp4", "frames": 4, "label": "OUTPUT — mouth follows the track", "note": "correlated, not phoneme-accurate"}],
"07-frame-interpolation": [
  {"file": "interp32_00001_.mp4", "frames": 6, "label": "INTERPOLATED — sampled frames", "note": "81 → 161 frames"}],
"21-3d-generation": [
  {"file": "source_owl_00001_.png", "label": "INPUT — one flat image", "note": "no text prompt in either graph"},
  {"file": "triposplat_orbit_00001_.mp4", "frames": 4, "label": "OUTPUT — 360° turntable", "note": "the back is invented"}],
}


def main():
    for name, spec in CAPS.items():
        d = os.path.join(R, name)
        os.makedirs(d, exist_ok=True)
        if name in PANELS:
            spec = dict(spec, panels=PANELS[name])
        with open(os.path.join(d, "CAPABILITY.json"), "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)
        print("wrote", name)
    print(f"\n{len(CAPS)} declarations, {len(PANELS)} with panels")


if __name__ == "__main__":
    main()
