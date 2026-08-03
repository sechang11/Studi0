#!/usr/bin/env python3
"""Sweep img2img denoise on one keyframe so the restyle strength can be CHOSEN, not guessed.

    python3 scripts/restyle_sweep.py films/derby.json --beat 020_rask

Denoise is the whole trade-off of the restyle stage:

    too low   the frame stays a Western comic - the anime checkpoint barely touches it
    too high  the face drifts off the character sheet and the reference-lock is wasted

The left tile is always the untouched Qwen keyframe, so the strip shows what each step
actually costs and buys. Look at the FACE, not the palette: the palette will look better
at every strength, which is exactly how a drifted face gets waved through.
"""
import argparse, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("COMFY_ROOT", "Z:/ComfyUI")
os.environ.setdefault("COMFY_HOST", "192.168.1.46:8188")
from comfy import run, set_path                            # noqa: E402
from epic import load_wf, COMFY, HOST, ensure_local, sh, expand   # noqa: E402

ANIME_POS = ("anime screencap, cel shading, flat colour fills, hard shadow edges, "
             "clean thin linework, vibrant saturated palette, 2d animation still")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film")
    ap.add_argument("--beat", required=True)
    ap.add_argument("--ckpt", default="animagine-xl-4.0.safetensors")
    ap.add_argument("--denoise", default="0.35,0.5,0.65,0.8")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    film = json.load(open(a.film, encoding="utf-8"))
    slug = film["title"].lower().replace(" ", "-")
    out = f"{COMFY}/output/claude-generated/12-shorts/{slug}"
    kf = f"{out}/keyframes/{a.beat}_00001_.png"
    if not os.path.exists(kf):
        raise SystemExit(f"no keyframe at {kf} - render the film first")

    # LoadImage only reads from ComfyUI/input
    stage = f"{COMFY}/input/restyle_in.png"
    shutil.copy(kf, stage)

    # The positive prompt must describe the SUBJECT, not just the style. With style
    # words alone the sampler has nothing to hold onto once denoise passes ~0.6 - it
    # corrupted the shirt number at 0.65 and invented an entirely different scene at 0.8.
    beat = next(b for b in film["beats"] if b["id"] == a.beat)
    pos = f"{expand(beat['prompt'], film.get('characters', {}))}, {ANIME_POS}"

    tiles = [kf]
    for d in [float(x) for x in a.denoise.split(",")]:
        wf = load_wf("21_sdxl_anime_restyle.json")
        set_path(wf, "1.inputs.ckpt_name", a.ckpt)
        set_path(wf, "2.inputs.image", "restyle_in.png")
        set_path(wf, "5.inputs.text", pos)
        set_path(wf, "7.inputs.denoise", d)
        set_path(wf, "7.inputs.seed", a.seed)
        tag = f"{a.beat}_d{str(d).replace('.','p')}"
        set_path(wf, "10.inputs.filename_prefix", f"claude-generated/restyle/{tag}")
        print(f"  > denoise {d}", flush=True)
        run(HOST, wf, quiet=True)
        p = f"{COMFY}/output/claude-generated/restyle/{tag}_00001_.png"
        ensure_local(f"claude-generated/restyle/{tag}_00001_.png", p, required=True)
        tiles.append(p)

    grid = f"{COMFY}/output/claude-generated/restyle/_sweep_{a.beat}.png"
    ins = []
    for p in tiles:
        ins += ["-i", p]
    sh("ffmpeg", "-y", "-v", "error", *ins, "-filter_complex",
       f"hstack=inputs={len(tiles)},scale={340*len(tiles)}:-1", "-frames:v", "1", grid)
    print(f"\n{grid}\n  left = original Qwen keyframe, then denoise {a.denoise}")


if __name__ == "__main__":
    main()
