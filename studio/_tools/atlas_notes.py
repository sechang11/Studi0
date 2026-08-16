#!/usr/bin/env python3
"""Fix HAVE by naming the cards, instead of guessing from the model's name.

The first pass matched a note to our library by looking for its key inside our filenames.
It reported FLUX.2 as not installed - we run it as a whole engine - and Animagine as not
installed, when animagine-xl-4.0.safetensors is sitting right there. That is precisely
the id-matching failure this file's own docstring warns about, committed one function
below the warning.

So each note now NAMES the model cards it corresponds to, the same way the audio taxonomy
names its cards. Explicit, checkable, and it fails loudly: a note listing a card id that
does not exist is printed rather than silently counted as missing.

Reading the real card list also corrected the atlas itself. We already have Wan 2.2,
HunyuanVideo 1.5, Z-Image Turbo, Hunyuan3D 2.1, SeedVR2, SAM 3.1 and TripoSplat - several
of which the first draft was about to recommend downloading.
"""
import json
import os

SEARCHED = "2026-08-16"

N = [
    # ---------------------------------------------------------------- image
    ("flux2", "FLUX.2 [dev]", "image", "Black Forest Labs", "2025-11-25", "12B+",
     ["flux2_dev_fp8mixed", "flux2_vae", "mistral_3_small_flux2_fp8"],
     "Text-to-image and multi-reference editing on an improved diffusion transformer, "
     "native up to 4 megapixels.",
     "The current benchmark for open-weight image quality, and the leader on prompt "
     "fidelity. Spells only QUOTED strings - our typography engine.",
     "searched", "https://www.sevenlabs.site/blogs/open-source-image-generation-models-2026"),
    ("qwen_image", "Qwen-Image 2512", "image", "Alibaba Qwen", None, "20B",
     ["qwen_image_2512_fp8_e4m3fn", "qwen_image_vae"],
     "Text-to-image with the strongest in-image text rendering of the open models.",
     "Leads multilingual text-to-image. Our default image engine - PROSE, and it cannot "
     "be prompted off photography at any cfg.",
     "searched", "https://medium.com/diffusion-doodles/model-rundown-z-image-turbo-qwen-image-2512-edit-2511-flux-2-dev-fc787f5e87ad"),
    ("qwen_edit", "Qwen-Image-Edit 2511", "image", "Alibaba Qwen", None, "20B",
     ["qwen_image_edit_2511_fp8mixed", "qwen_image_edit_2509_fp8_e4m3fn"],
     "Instruction editing: change one thing and keep everything else.",
     "Two-image fusion - compose separately generated people into one photo. Capability 20.",
     "searched", "https://medium.com/diffusion-doodles/model-rundown-z-image-turbo-qwen-image-2512-edit-2511-flux-2-dev-fc787f5e87ad"),
    ("zimage", "Z-Image Turbo", "image", "Tongyi", None, "6B", ["z_image_turbo_bf16"],
     "Small, very fast text-to-image - about a second an image.",
     "Throughput-per-dollar leader. The ideation model: twenty options in the time "
     "FLUX.2 takes for one. Capability 33.",
     "searched", "https://zimage.run/blog/zi-068-vs-flux2-dev-en-20260530"),
    ("animagine", "Animagine XL 4.0", "image", "Cagliostro Lab", None, "3.5B",
     ["animagine_xl_4_0", "illustrious_xl_v2_0"],
     "Danbooru-tag anime generation on an SDXL base.",
     "Speaks TAGS, not prose - the dialect law. Crossing a character card between this "
     "and a prose engine silently deletes the character.",
     "local", None),
    ("flux_fill", "FLUX.1 Fill + OneReward", "image", "Black Forest Labs", None, None,
     ["flux_1_fill_dev_onereward_transformer_fp8"],
     "Inpainting and outpainting.",
     "How master-frame outpainting widens a shot without redrawing the subject.",
     "local", None),

    # ---------------------------------------------------------------- video
    ("wan22", "Wan 2.2", "video", "Alibaba", None, "14B MoE (high+low noise)",
     ["wan2_2_i2v_high_noise_14b_fp8_scaled", "wan2_2_i2v_low_noise_14b_fp8_scaled",
      "wan2_2_vae"],
     "Image-to-video, the photorealism leader among open models.",
     "Best open model for HUMAN subjects - faces, skin and hair hold where others "
     "smear. Roughly 8x slower than LTX, which is why LTX carries the slate.",
     "searched", "https://www.aimagicx.com/blog/open-source-ai-video-models-comparison-2026"),
    ("hunyuanvideo15", "HunyuanVideo 1.5", "video", "Tencent", None, "~13B",
     ["hunyuanvideo1_5_720p_i2v_fp16", "hunyuanvideo1_5_720p_t2v_fp16",
      "hunyuanvideo1_5_1080p_sr_distilled_fp16", "hunyuanvideo15_vae_fp16"],
     "Text-to-video and image-to-video, plus a 1080p super-resolution stage.",
     "Strongest scene coherence over longer clips and the most realistic human motion. "
     "INSTALLED AND UNTESTED here - the largest unopened box in the library.",
     "searched", "https://www.aimagicx.com/blog/open-source-ai-video-models-comparison-2026"),
    ("ltx23", "LTX-2.3", "video", "Lightricks", None, "22B",
     ["ltx_2_3_22b_dev_fp8"],
     "Image-to-video with a synchronised audio track in the same forward pass.",
     "Speed, and a nearly flat cost curve in clip length. The only engine here that "
     "generates picture and sound together. Our default.",
     "searched", "https://ltx.io/blog/best-open-source-video-generation-models"),
    ("ltx25", "LTX-2.5", "video", "Lightricks", "2026-08-12", "22B distilled",
     ["ltx_2_5_22b_distilled_transformer_comfy_int8_convrot", "ltx_2_5_video_vae_bf16",
      "ltx_2_5_audio_vae_bf16", "ltx_2_5_latent_spatial_upscaler_x2_bf16_1_0",
      "gemma4_12b_with_proj_ltx_2_5_comfy_int8_convrot"],
     "Native MULTI-SHOT video: several connected shots with real cuts in one generation.",
     "A cut is where identity normally breaks. Measured here against 2.3 on the same "
     "subject: drift -0.004 against 0.141. Capability 51.",
     "local", None),
    ("wan_vace", "Wan 2.1 VACE 14B", "video", "Alibaba", None, "14B",
     ["wan2_1_vace_14b_fp16", "wan_2_1_vae"],
     "Video editing: restyle, inpaint or extend footage that already exists.",
     "The only real answer here to shot-to-shot look matching. Installed, not built.",
     "local", None),

    # ---------------------------------------------------------------- audio
    ("indextts2", "IndexTTS-2", "audio", "Bilibili", None, "~1B", [],
     "Zero-shot voice cloning with independent timbre and emotion control, and precise "
     "duration control.",
     "Beats other zero-shot TTS on word error rate, speaker similarity AND emotional "
     "fidelity. The duration control is the dubbing feature - a line can be made to fit "
     "a shot. Runs via TTS-Audio-Suite, no checkpoint of its own in models/.",
     "searched", "https://www.siliconflow.com/articles/en/best-open-source-models-for-voice-cloning"),
    ("higgs", "Higgs Audio v3", "audio", "Boson AI", None, None, [],
     "Voice cloning from a reference clip.",
     "What our 17 usable voice packs run on. Node-managed, so no file in models/.",
     "local", None),
    ("acestep", "ACE-Step v1 3.5B", "audio", "ACE Studio", None, "3.5B",
     ["ace_step_v1_3_5b", "acestep_v1_5_turbo", "ace_1_5_vae"],
     "Text-to-music from tag prompts, with bpm and key control.",
     "Our 32 music cues. The FULL model at cfg 5 - the v1.5 turbo at cfg 1.0 ignores "
     "the prompt entirely, measured here the hard way.",
     "local", None),
    ("stableaudio", "Stable Audio 3 Medium", "audio", "Stability AI", None, None,
     ["stable_audio_3_medium"],
     "Text-to-audio for sound effects and short samples.",
     "Our 35 sound effects. One sound per bed at cfg 7 / 100 steps; the defaults "
     "produce mush.",
     "local", None),
    ("f5tts", "F5-TTS", "audio", "SWivid", None, "~330M", [],
     "Flow-matching text-to-speech.",
     "Noticeably more natural prosody than XTTS v2 on long inputs. NOT INSTALLED - the "
     "strongest candidate for narration if Higgs disappoints.",
     "searched", "https://rarebuildsoftware.com/blog/best-open-source-voice-cloning-2026"),
    ("fishspeech", "Fish Speech V1.5", "audio", "Fish Audio", None, "~500M", [],
     "Multilingual zero-shot voice cloning.",
     "Named with IndexTTS-2 and CosyVoice2 as the 2026 front rank. NOT INSTALLED.",
     "searched", "https://www.siliconflow.com/articles/en/best-open-source-models-for-voice-cloning"),
    ("cosyvoice2", "CosyVoice2-0.5B", "audio", "Alibaba", None, "0.5B", [],
     "Streaming-capable zero-shot TTS.",
     "Small and fast enough to stream. NOT INSTALLED.",
     "searched", "https://www.siliconflow.com/articles/en/best-open-source-models-for-voice-cloning"),

    # ---------------------------------------------------------------- 3d / control / other
    ("hunyuan3d", "Hunyuan3D 2.1", "3d", "Tencent", None, None, ["hunyuan_3d_v2_1"],
     "Image to textured 3D mesh.",
     "The 3D-print route: shape plus PBR texture rather than shape alone.",
     "local", None),
    ("triposplat", "TripoSplat", "3d", "Tripo AI", None, None,
     ["triposplat_fp16", "triposplat_vae_decoder_fp16"],
     "Image to 3D gaussian splat.",
     "Splats rather than meshes - better for viewing, not printable. Installed, untested.",
     "local", None),
    ("seedvr2", "SeedVR2 3B", "upscale", "ByteDance", None, "3B",
     ["seedvr2_3b_int8_convrot", "seedvr2_ema_vae_fp16"],
     "Diffusion video and image restoration.",
     "Restoration, not interpolation - it reconstructs detail instead of smoothing it. "
     "Installed, untested.",
     "local", None),
    ("realesrgan", "RealESRGAN x4plus", "upscale", "Tencent ARC", None, None,
     ["realesrgan_x4plus"],
     "Classic 4x upscaler.",
     "1664x928 to 6656x3712 in 4.5s. Fast and predictable; SeedVR2 is the quality "
     "option when it is finally tested.",
     "local", None),
    ("sam31", "SAM 3.1", "control", "Meta", None, None, ["sam3_1_multiplex_fp16"],
     "Segment anything - masks from a point, a box or a prompt.",
     "The masking layer under removal and compositing.",
     "local", None),
    ("qwen_vl", "Qwen2.5-VL 7B", "control", "Alibaba Qwen", None, "7B",
     ["qwen_2_5_vl_7b_fp8_scaled"],
     "Vision-language model: describe an image, answer questions about it.",
     "Our frame_check instrument - it is what looks at a render and says whether the "
     "nouns we asked for are actually in it.",
     "local", None),
]

FAM_ORDER = ["image", "video", "audio", "3d", "control", "upscale"]


def main():
    ids = set()
    import glob
    for p in glob.glob(os.path.join("studio", "models", "*.json")):
        try:
            ids.add(json.load(open(p, encoding="utf-8")).get("id"))
        except Exception:
            pass

    notes, bad = [], []
    for (key, name, fam, vendor, rel, params, cards, what, special, prov, src) in N:
        missing = [c for c in cards if c not in ids]
        bad += [(key, c) for c in missing]
        # Node-managed models run here but ship no checkpoint into models/, so "names a
        # card" is the wrong test for them and would report our own TTS as missing.
        NODE_MANAGED = {"indextts2": "managed by the TTS-Audio-Suite node, no checkpoint "
                                     "in models/ - runs every time a film speaks",
                        "higgs": "managed by the TTS-Audio-Suite node, no checkpoint in "
                                 "models/ - our 17 voice packs run on it"}
        notes.append(dict(key=key, name=name, family=fam, vendor=vendor, released=rel,
                          params=params, cards=cards,
                          have=bool(cards) or key in NODE_MANAGED,
                          node_managed=NODE_MANAGED.get(key),
                          missing_cards=missing, what=what, special=special,
                          provenance=prov, source=src))
    notes.sort(key=lambda n: (FAM_ORDER.index(n["family"]) if n["family"] in FAM_ORDER
                              else 9, n["name"]))
    doc = {
        "generated": SEARCHED,
        "note": ("The authored layer over the ComfyUI catalogue: what each model is FOR "
                 "and what makes it worth having, which the catalogue does not carry. "
                 "HAVE is decided by NAMING our model cards, never by matching the "
                 "model's name against filenames - the first version of this file did "
                 "that and reported FLUX.2 as not installed."),
        "provenance_key": {
            "searched": "checked on the web %s; source URL on the entry" % SEARCHED,
            "recalled": "training knowledge, cutoff May 2026 - may be stale",
            "local": "measured on this machine",
        },
        "notes": notes,
    }
    json.dump(doc, open(os.path.join("studio", "atlas_notes.json"), "w",
                        encoding="utf-8"), indent=1)
    import collections
    print("%d notes, %d we have, %d we do not"
          % (len(notes), sum(1 for n in notes if n["have"]),
             sum(1 for n in notes if not n["have"])))
    print("provenance:", dict(collections.Counter(n["provenance"] for n in notes)))
    for k, c in bad:
        print("  ! %s names a card that does not exist: %s" % (k, c))
    if not bad:
        print("every named card exists")


if __name__ == "__main__":
    main()
