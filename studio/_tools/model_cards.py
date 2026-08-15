#!/usr/bin/env python3
"""studio/_tools/model_cards.py - models become a card kind (ARCHITECTURE Phase 5).

    python3 studio/_tools/model_cards.py            # rebuild studio/models/*.json

96 checkpoints were legible only as filenames in a folder. A model card is EARNED BY
CONTENT: what dialect it reads, what it is measurably good and bad at, how it is reached
(which workflow files mention it, and whether any code can load them), and where its
rendered proof lives. The measured knowledge below comes from the project's own sessions
- the engine A/Bs, the FLUX.2 typography gallery, the LTX frame-math fixes, the ACE-Step
keyscale incident - so a card says what THIS box learned, not what a model zoo claims.

Scan facts (file, size, folder, workflow mentions, reachability) refresh on every run;
MEASURED text is keyed by filename and survives rescans. A model on disk with no
measured entry gets an UNTESTED card and UNVERIFIED evidence - the debt list again.
Deleting a file deletes its card on the next run (status unavailable first, so a card
never points at nothing without saying so).
"""
import glob
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, STUDIO)
COMFY = os.environ.get("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))

FOLDERS = ["checkpoints", "diffusion_models", "text_encoders", "vae", "upscale_models",
           "controlnet"]

# What this box has measured, keyed by filename. `role` is the one-line job description;
# `dialect` matters only for prompted image/video engines.
MEASURED = {
    "animagine-xl-4.0.safetensors": dict(
        engine="anime", dialect="tags", status="ready", role="The tag engine.",
        desc="Reads danbooru TAGS and nothing else - prose contributes NOTHING here "
             "(the wave-4 lesson: 82 of 200 frames lost a prose-only character). "
             "Fast, consistent anime faces; the character sheet engine.",
        strengths="anime characters, emotions via tags, reference sheets, LoRA base",
        weaknesses="prose-blind; realism reads as anime-realistic at best",
        strip="samples/isolation/characters/*.png"),
    "Illustrious-XL-v2.0.safetensors": dict(
        engine="anime", dialect="tags", status="untested",
        role="Alternative tag engine.",
        desc="On disk, never routed by compose. Would need a base A/B via model_intake "
             "before earning a route.", strengths="", weaknesses=""),
    "qwen_image_2512_fp8_e4m3fn.safetensors": dict(
        engine="qwen", dialect="prose", status="ready", role="The prose engine.",
        desc="Reads PROSE. Cannot be prompted off photography at any cfg - a style must "
             "arrive as a LoRA or a concrete noun, never as an adjective. Watercolour "
             "and hand-media are its lane against FLUX.2 (measured pair).",
        strengths="painterly and photographic stills, places, hand media",
        weaknesses="typography (gibberish), cannot leave photography by prompt alone",
        strip="samples/isolation/places/*.png"),
    "flux2_dev_fp8mixed.safetensors": dict(
        engine="flux2", dialect="prose", status="ready",
        role="Layout, count, hex colour and QUOTED text.",
        desc="Spells ONLY quoted strings - unquoted text is gibberish even at 4 steps. "
             "Dials are set BY INPUT KEY (noise_seed on RandomNoise, steps on "
             "Flux2Scheduler): matching class names set nothing and cost a silent "
             "no-op sweep. Self-contained styles (signs, printed pages) drop the "
             "character - excluded from character pools.",
        strengths="typography (quoted), physical media, layout obedience, hex colour",
        weaknesses="unquoted text, anime faces, character consistency",
        strip="samples/flux2_gallery/*.png"),
    "ltx-2.3-22b-dev-fp8.safetensors": dict(
        engine="video", dialect="prose", status="ready",
        role="The image-to-video pass with its own audio track.",
        desc="frames = 8n+1 at 24fps (the shipped workflow said 25 for the audio "
             "latent and drifted - corrected, task 45). 16:9 at 1216x704; ~10s drift "
             "ceiling. Camera moves asked in the motion text FAIL (5-22% measured); "
             "cameras render as ffmpeg post passes instead.",
        strengths="gentle subject motion, free ambience track, keyframe fidelity",
        weaknesses="prompted camera moves, long clips, fast action",
        strip="samples/rolled/video/*.mp4"),
    "ace_step_v1_3.5b.safetensors": dict(
        engine="audio", dialect="prose", status="ready", role="The music engine.",
        desc="Key names must match its 34-item combo exactly - `B flat minor` kills "
             "the whole graph, `Bb minor` passes (SOUND-05; engine.keyscale reads the "
             "list from the running server so it cannot drift).",
        strengths="cues, movements, leitmotifs", weaknesses="lyrics intelligibility",
        strip="samples/audio/*.mp3"),
    "acestep_v1.5_turbo.safetensors": dict(
        engine="audio", dialect="prose", status="untested",
        role="Faster ACE-Step distill.", desc="On disk, not yet routed.", strengths="",
        weaknesses=""),
    "stable_audio_3_medium.safetensors": dict(
        engine="audio", dialect="prose", status="ready", role="The SFX engine.",
        desc="Raw output levels are all over the place; SFX are normalised before a "
             "film (two-pass loudnorm, alimiter level=disabled - auto-level silently "
             "undid a -20.9 to -14.9 LUFS correction once).",
        strengths="short named effects", weaknesses="long ambiences, levels"),
    "hunyuan_3d_v2.1.safetensors": dict(
        engine="mesh", status="ready", role="Image-to-mesh for the print pipeline.",
        desc="Feeds to_print/mesh_doctor; characters meshify from turnaround stills.",
        strengths="single-object meshes from clean plates", weaknesses="thin features"),
    "triposplat_fp16.safetensors": dict(
        engine="mesh", status="untested", role="Alternative 3D path.",
        desc="On disk, not yet compared against hunyuan_3d.", strengths="",
        weaknesses=""),
    "z_image_turbo_bf16.safetensors": dict(
        engine="image", status="untested", role="Fast image distill.",
        desc="On disk, never A/B'd against the three routed engines.", strengths="",
        weaknesses=""),
}

WAN_NOTE = dict(engine="video", status="untested", role="Video engine, unrouted.",
                desc="On disk, never rendered through the app. LTX-2.3 is the routed "
                     "video pass; these would need a measured A/B to earn a route.",
                strengths="", weaknesses="")
for f in ("wan2.1_vace_14B_fp16.safetensors",
          "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
          "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
          "hunyuanvideo1.5_720p_i2v_fp16.safetensors",
          "hunyuanvideo1.5_720p_t2v_fp16.safetensors",
          "hunyuanvideo1.5_1080p_sr_distilled_fp16.safetensors"):
    MEASURED[f] = dict(WAN_NOTE)

UTILITY = dict(status="ready", role="Utility.", strengths="", weaknesses="")
for f, role in (("sam3.1_multiplex_fp16.safetensors", "Segmentation (masks)."),
                ("sdpose_wholebody_fp16.safetensors", "Pose extraction (v2v, dance)."),
                ("seedvr2_3b_int8_convrot.safetensors", "Video restoration/upscale."),
                ("qwen_image_edit_2509_fp8_e4m3fn.safetensors", "Qwen image EDIT pass."),
                ("qwen_image_edit_2511_fp8mixed.safetensors",
                 "Qwen image EDIT pass (2511)."),
                ("flux.1-fill-dev-OneReward-transformer_fp8.safetensors",
                 "Inpaint/outpaint fill - the master-frame kit's outpaint arm.")):
    MEASURED[f] = dict(UTILITY, role=role, engine="utility",
                       desc="Reached through its workflow rather than prompted.")


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:60]


def main():
    import cards
    # what mentions each model, and which workflow files code actually loads
    wf_text = {}
    for wf in glob.glob(os.path.join(ROOT, "workflows", "*.json")):
        try:
            wf_text[os.path.basename(wf)] = open(wf, encoding="utf-8").read()
        except OSError:
            pass
    code = ""
    for pat in ("studio/*.py", "studio/_tools/*.py", "scripts/*.py"):
        for f in glob.glob(os.path.join(ROOT, pat)):
            try:
                code += open(f, encoding="utf-8").read()
            except OSError:
                pass
    loaded = set(re.findall(r"load_wf\(\s*[\"\']([^\"\']+)", code))

    outdir = os.path.join(STUDIO, "models")
    os.makedirs(outdir, exist_ok=True)
    seen = set()
    made = {"ready": 0, "untested": 0}
    for folder in FOLDERS:
        d = os.path.join(COMFY, "models", folder)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith((".safetensors", ".ckpt", ".pt", ".pth", ".gguf")):
                continue
            cid = slug(fn.rsplit(".", 1)[0])
            seen.add(cid)
            m = MEASURED.get(fn, {})
            mentions = sorted(w for w, t in wf_text.items() if fn in t)
            card = {
                "id": cid,
                "name": fn.rsplit(".", 1)[0],
                "file": fn,
                "folder": folder,
                "size_gb": round(os.path.getsize(os.path.join(d, fn)) / 1e9, 2),
                "status": m.get("status", "untested"),
                "engine": m.get("engine"),
                "dialect": m.get("dialect"),
                "role": m.get("role", "On disk, unmeasured."),
                "desc": m.get("desc", "Nothing on this box has rendered through this "
                                      "model yet."),
                "strengths": m.get("strengths", ""),
                "weaknesses": m.get("weaknesses", ""),
                "workflows": mentions,
                "reachable": any(w in loaded for w in mentions),
                "strip": m.get("strip"),
            }
            p = os.path.join(outdir, cid + ".json")
            old = {}
            if os.path.exists(p):
                old = json.load(open(p, encoding="utf-8"))
                for keep in ("evidence", "evidence_history"):
                    if keep in old:
                        card[keep] = old[keep]
            with open(p, "w", encoding="utf-8") as f:
                json.dump(card, f, indent=2, ensure_ascii=False)
                f.write("\n")
            if not card.get("evidence"):
                if fn in MEASURED and m.get("status") == "ready":
                    cards.stamp("models", cid, "MEASURED",
                                "engine sessions on this box; see desc",
                                note=m.get("role", ""))
                else:
                    cards.stamp("models", cid, "UNVERIFIED",
                                "on disk; nothing rendered through it here")
            made["ready" if card["status"] == "ready" else "untested"] += 1

    # a card whose file left the disk says so instead of pointing at nothing
    for p in glob.glob(os.path.join(outdir, "*.json")):
        cid = os.path.basename(p)[:-5]
        if cid.startswith("_") or cid in seen:
            continue
        c = json.load(open(p, encoding="utf-8"))
        if c.get("status") != "unavailable":
            c["status"] = "unavailable"
            c["desc"] = "File no longer on disk. " + str(c.get("desc") or "")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(c, f, indent=2, ensure_ascii=False)
                f.write("\n")
    print("model cards:", made)
    return 0


if __name__ == "__main__":
    import argparse
    argparse.ArgumentParser(description="Rebuild studio/models/ cards from disk + "
                                        "measured knowledge.").parse_args()
    sys.exit(main())
