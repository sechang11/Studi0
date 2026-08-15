#!/usr/bin/env python3
"""ltx25_probe.py - the same keyframe + motion through LTX-2.3 (12_ltx23_i2v_audio) and
LTX-2.5 (51_ltx25_i2v); wall clock, frame-0 fidelity to the keyframe, and a frame strip
for LOOKING at. Writes MEASURED evidence onto the 2.5 model card when it renders, and
says plainly when the 2.5 weights are not on disk instead of pretending.

    python3 studio/_tools/ltx25_probe.py [--key PNG] [--motion TEXT] [--seconds 4]

The gate for routing 2.5 is not "it runs" - it is "frame-0 SSIM to the keyframe is at
least what 2.3 delivers, and a human watched the strip". This tool produces both inputs.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, STUDIO)
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run, set_path                 # noqa: E402
from engine import load_wf, HOST                # noqa: E402

COMFY = os.environ.get("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
OUT = os.path.join(STUDIO, "samples", "ltx25_probe")


def have_25():
    need = ["diffusion_models/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors",
            "text_encoders/gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors",
            "vae/ltx-2.5-video-vae-bf16.safetensors", "vae/ltx-2.5-audio-vae-bf16.safetensors",
            "latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors"]
    missing = [n for n in need if not (os.path.exists(os.path.join(COMFY, "models", n))
                                       and os.path.getsize(os.path.join(COMFY, "models", n))
                                       > 1_000_000)]
    return missing


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def first_frame(mp4, png):
    sh("ffmpeg", "-y", "-v", "error", "-i", mp4, "-vf", "select=eq(n\\,0)", "-vframes",
       "1", png)
    return png if os.path.exists(png) else None


def ssim(a, b):
    """Frame-0 SSIM to the keyframe via ffmpeg (both scaled to the clip size)."""
    r = sh("ffmpeg", "-v", "error", "-i", a, "-i", b, "-lavfi",
           "[0:v][1:v]scale2ref[x][y];[x][y]ssim=stats_file=-", "-f", "null", "-")
    for tok in (r.stdout or "").split():
        if tok.startswith("All:"):
            try:
                return float(tok.split(":")[1])
            except ValueError:
                pass
    return None


def strip(mp4, png):
    sh("ffmpeg", "-y", "-v", "error", "-i", mp4, "-vf",
       "fps=2,scale=320:-2,tile=6x1", "-frames:v", "1", png)


def render(wfname, key, motion, seconds, tag, seed=1234):
    staged = "ltx25_probe_%s.png" % tag
    shutil.copy(key, os.path.join(COMFY, "input", staged))
    wf = load_wf(wfname)
    if wfname.startswith("12_"):
        frames = int(round(seconds * 24 / 8)) * 8 + 1
        set_path(wf, "8.inputs.image", staged)
        set_path(wf, "10.inputs.text", motion)
        set_path(wf, "20.inputs.width", 1216)
        set_path(wf, "20.inputs.height", 704)
        set_path(wf, "20.inputs.length", frames)
        set_path(wf, "21.inputs.frames_number", frames)
        set_path(wf, "21.inputs.frame_rate", 24)
        set_path(wf, "32.inputs.noise_seed", seed)
        set_path(wf, "43.inputs.filename_prefix", "claude-generated/ltx25_probe/%s" % tag)
    else:
        set_path(wf, "395.inputs.image", staged)
        set_path(wf, "376.inputs.value", motion)
        set_path(wf, "383.inputs.value", False)      # no LLM expansion: same text both arms
        set_path(wf, "362.inputs.value", int(seconds))
        set_path(wf, "339.inputs.noise_seed", seed)
        set_path(wf, "338.inputs.noise_seed", seed)
        set_path(wf, "75.inputs.filename_prefix", "claude-generated/ltx25_probe/%s" % tag)
    t0 = time.time()
    _, outs = run(HOST, wf, quiet=True)
    secs = time.time() - t0
    mp4 = None
    for o in outs or []:
        if str(o).lower().endswith((".mp4", ".webm", ".mov")):
            mp4 = os.path.join(COMFY, "output", o)
    if not mp4 or not os.path.exists(mp4):
        return None, secs
    dst = os.path.join(OUT, "%s.mp4" % tag)
    shutil.copy(mp4, dst)
    return dst, secs


def main():
    ap = argparse.ArgumentParser(description="LTX-2.3 vs LTX-2.5 on one keyframe.")
    ap.add_argument("--key", default=os.path.join(
        STUDIO, "samples", "isolation", "places", "clean_airship_deck_0.png"))
    ap.add_argument("--motion", default="the camera drifts slowly forward along the deck, "
                                        "ropes sway gently in the wind, clouds drift")
    ap.add_argument("--seconds", type=float, default=4.0)
    ap.add_argument("--seed", type=int, default=1234)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    report = {"key": a.key, "motion": a.motion, "seconds": a.seconds, "arms": {}}

    clip23, s23 = render("12_ltx23_i2v_audio.json", a.key, a.motion, a.seconds, "ltx23",
                         a.seed)
    if clip23:
        f0 = first_frame(clip23, os.path.join(OUT, "ltx23_f0.png"))
        report["arms"]["ltx23"] = {"secs": round(s23, 1), "ssim_f0": ssim(a.key, f0)}
        strip(clip23, os.path.join(OUT, "ltx23_strip.png"))
        print("ltx23  %5.1fs  ssim_f0=%s" % (s23, report["arms"]["ltx23"]["ssim_f0"]))
    else:
        report["arms"]["ltx23"] = {"error": "no clip"}
        print("ltx23  FAILED")

    missing = have_25()
    if missing:
        report["arms"]["ltx25"] = {"error": "weights not on disk", "missing": missing}
        print("ltx25  NOT RUN - %d gated file(s) missing; see docs/LTX25-RUNBOOK.md"
              % len(missing))
    else:
        clip25, s25 = render("51_ltx25_i2v.json", a.key, a.motion, a.seconds, "ltx25",
                             a.seed)
        if clip25:
            f0 = first_frame(clip25, os.path.join(OUT, "ltx25_f0.png"))
            report["arms"]["ltx25"] = {"secs": round(s25, 1), "ssim_f0": ssim(a.key, f0)}
            strip(clip25, os.path.join(OUT, "ltx25_strip.png"))
            print("ltx25  %5.1fs  ssim_f0=%s" % (s25, report["arms"]["ltx25"]["ssim_f0"]))
            try:
                import cards
                cards.stamp("models", "ltx_2_5_22b_distilled_transformer_comfy_int8_convrot",
                            "MEASURED", "ltx25_probe vs 2.3 on one keyframe",
                            note="%.1fs, ssim_f0 %s (2.3: %.1fs, %s) - strip at "
                                 "samples/ltx25_probe/ltx25_strip.png; a human must watch"
                                 % (s25, report["arms"]["ltx25"]["ssim_f0"], s23,
                                    report["arms"]["ltx23"].get("ssim_f0")))
            except Exception as e:                                       # noqa: BLE001
                print("  (could not stamp the model card: %s)" % e)
        else:
            report["arms"]["ltx25"] = {"error": "no clip"}
            print("ltx25  FAILED")
    json.dump(report, open(os.path.join(OUT, "report.json"), "w"), indent=1)
    print("report:", os.path.join(OUT, "report.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
