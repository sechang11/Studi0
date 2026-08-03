#!/usr/bin/env python3
"""
pipeline.py - one command: prompt -> still -> animated clip.

    python3 pipeline.py "a lighthouse in a storm" --motion "slow push in, waves crash"

Runs Qwen-Image 2512 (4-step Lightning) for the keyframe, then hands that frame to
Wan 2.2 I2V 14B (4-step lightx2v) for motion. Everything lands in
ComfyUI/output/claude-generated/<slug>/.

Options:
    --ar        16:9 | 9:16 | 1:1 | 4:3 | 3:2      (default 16:9)
    --seconds   clip length in seconds            (default 5, max ~7.5 practical)
    --res       720 | 480 | 1080                  (video height, default 720)
    --shots     N keyframes -> N clips, one per prompt line from stdin
    --still     stop after the image
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COMFY = os.path.expanduser("~/ComfyUI")
sys.path.insert(0, HERE)
from comfy import api, run, set_path  # noqa: E402

HOST = os.environ.get("COMFY_HOST", "127.0.0.1:8188")

AR = {
    "1:1": (1328, 1328), "16:9": (1664, 928), "9:16": (928, 1664),
    "4:3": (1472, 1104), "3:4": (1104, 1472), "3:2": (1584, 1056), "2:3": (1056, 1584),
}
VID = {
    "480":  {"16:9": (832, 480),   "9:16": (480, 832),   "1:1": (640, 640)},
    "720":  {"16:9": (1280, 720),  "9:16": (720, 1280),  "1:1": (960, 960)},
    "1080": {"16:9": (1920, 1088), "9:16": (1088, 1920), "1:1": (1440, 1440)},
}

NEG_IMG = "blurry, low quality, watermark, text, jpeg artifacts, oversaturated, deformed"
NEG_VID = ("static, still image, frozen, blurry, distorted, warping, morphing, "
           "flickering, low quality, jpeg artifacts, watermark, text")


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:48] or "shot"


def load(name):
    return {k: v for k, v in json.load(open(f"{ROOT}/workflows/{name}")).items()
            if not k.startswith("_")}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("prompt")
    p.add_argument("--motion", default="subtle natural motion, slow cinematic camera drift")
    p.add_argument("--ar", default="16:9", choices=list(AR))
    p.add_argument("--seconds", type=float, default=5.0)
    p.add_argument("--res", default="720", choices=list(VID))
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--still", action="store_true")
    p.add_argument("--steps", type=int, default=4, help="image steps; >4 disables the Lightning LoRA path")
    a = p.parse_args()

    slug = slugify(a.prompt)
    seed = a.seed or int(time.time()) % 2**31

    # ---- 1. keyframe ------------------------------------------------------
    w, h = AR[a.ar]
    wf = load("01_qwen_t2i_turbo.json")
    set_path(wf, "10.inputs.text", a.prompt)
    set_path(wf, "11.inputs.text", NEG_IMG)
    set_path(wf, "12.inputs.width", w)
    set_path(wf, "12.inputs.height", h)
    set_path(wf, "13.inputs.seed", seed)
    set_path(wf, "13.inputs.steps", a.steps)
    set_path(wf, "15.inputs.filename_prefix", f"claude-generated/{slug}/keyframe")
    print(f"[1/2] keyframe {w}x{h} seed={seed}")
    _, outs = run(HOST, wf)
    if not outs:
        sys.exit("no image produced")
    still = os.path.join(COMFY, "output", outs[0])

    if a.still:
        print(still)
        return

    # ---- 2. motion --------------------------------------------------------
    # Wan needs the start frame in ComfyUI/input/
    staged = f"pipeline_{slug}.png"
    shutil.copy(still, os.path.join(COMFY, "input", staged))

    vw, vh = VID[a.res].get(a.ar) or VID[a.res]["16:9"]
    # length must satisfy 4n+1
    length = max(5, int(round(a.seconds * 16 / 4)) * 4 + 1)

    wf = load("04_wan22_i2v_turbo.json")
    set_path(wf, "10.inputs.image", staged)
    set_path(wf, "11.inputs.text", f"{a.prompt}. {a.motion}")
    set_path(wf, "12.inputs.text", NEG_VID)
    set_path(wf, "13.inputs.width", vw)
    set_path(wf, "13.inputs.height", vh)
    set_path(wf, "13.inputs.length", length)
    set_path(wf, "14.inputs.noise_seed", seed)
    set_path(wf, "18.inputs.filename_prefix", f"claude-generated/{slug}/clip")
    print(f"[2/2] video {vw}x{vh} {length}f @16fps = {length/16:.1f}s")
    run(HOST, wf)

    print(f"\n-> {COMFY}/output/claude-generated/{slug}/")


if __name__ == "__main__":
    main()
