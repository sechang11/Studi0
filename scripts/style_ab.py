#!/usr/bin/env python3
"""Render one prompt at several style-LoRA strengths so a look can be CHOSEN, not assumed.

    python3 scripts/style_ab.py films/derby.json --strengths 0,0.5,0.8,1.1

Exists because THE DERBY shipped looking like a Western sports comic while imitating an
anime reference, and the style LoRA had been sitting at strength 0.0 the whole time without
anyone rendering a comparison. Ten seconds of GPU answers this; guessing does not.
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("COMFY_ROOT", "Z:/ComfyUI")
os.environ.setdefault("COMFY_HOST", "192.168.1.46:8188")
from comfy import run, set_path                        # noqa: E402
from epic import load_wf, COMFY, HOST, ensure_local, sh, expand   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film")
    ap.add_argument("--beat", default=None, help="beat id to test (default: first no-ref)")
    ap.add_argument("--lora", default=None, help="override the film's style_lora")
    ap.add_argument("--strengths", default="0,0.5,0.8,1.1")
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    film = json.load(open(a.film, encoding="utf-8"))
    beats = film["beats"]
    b = (next(x for x in beats if x["id"] == a.beat) if a.beat
         else next(x for x in beats if not x.get("ref")))
    lora = a.lora or film.get("style_lora")
    if not lora:
        raise SystemExit("film has no style_lora to test")

    tiles = []
    for s in [float(x) for x in a.strengths.split(",")]:
        wf = load_wf("13_qwen_t2i_styled.json")
        set_path(wf, "7.inputs.lora_name", lora)
        set_path(wf, "7.inputs.strength_model", s)
        set_path(wf, "10.inputs.text",
                 f"{expand(b['prompt'], film.get('characters', {}))}, "
                 f"{film.get('style','')}")
        set_path(wf, "12.inputs.width", 1328)
        set_path(wf, "12.inputs.height", 1328)
        set_path(wf, "13.inputs.seed", a.seed)          # same seed: only style varies
        tag = f"{os.path.basename(lora)[:18]}_s{str(s).replace('.','p')}"
        set_path(wf, "15.inputs.filename_prefix", f"claude-generated/style_ab/{tag}")
        print(f"  > strength {s}", flush=True)
        run(HOST, wf, quiet=True)
        p = f"{COMFY}/output/claude-generated/style_ab/{tag}_00001_.png"
        ensure_local(f"claude-generated/style_ab/{tag}_00001_.png", p, required=True)
        tiles.append(p)

    grid = a.out or f"{COMFY}/output/claude-generated/style_ab/_compare.png"
    ins = []
    for p in tiles:
        ins += ["-i", p]
    sh("ffmpeg", "-y", "-v", "error", *ins, "-filter_complex",
       f"hstack=inputs={len(tiles)},scale={400*len(tiles)}:-1", "-frames:v", "1", grid)
    print(f"\n{grid}\n  left to right: {a.strengths}  (beat {b['id']}, same seed)")


if __name__ == "__main__":
    main()
