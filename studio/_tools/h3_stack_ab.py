#!/usr/bin/env python3
"""studio/_tools/h3_stack_ab.py - the MiniMax H3 acceleration stack, measured against ours.

A workflow posted online stacks four things on H3: TeaCache, SageAttention, Spectrum and the
v4 step-600 EMA turbo LoRA.  Three of those are step-skippers or kernel swaps whose whole claim
is speed, and speed is the one thing this project has never let a screenshot decide.  So each
piece is a separate arm on the SAME start frames, and the arms are read against LTX-2.5 doing
the same shot, because "is H3 worth reaching for" is the only question that changes what the
film pipeline does.

The start frames are not neutral benchmarks.  Two of the three are the shots LTX measurably
failed on while making the book's opening film: a still close-up it would not hold past about
1.5 s (six takes, all pulled back to the street) and an empty market it filled with people in
six takes out of seven.  If H3 holds either, that is a capability this studio did not have.

COLUMNS (clipmetrics owns hold_f0 / drift / motion; the rest are this file's):

    secs        wall clock for the render, model load included on the first of a run
    hold_f0     SSIM of the first frame against the start picture - did it repaint it
    drift       hold_f0 - hold_last; HIGH means the picture walked away from the frame
    motion      mean luma change per second; ~0 means it froze, which drift alone hides
    luma_drop   start picture luma minus clip luma; positive = delivered darker
    frames      delivered frame count, and the seconds they make at the clip's fps
    audio_db    mean dB of the render's own soundtrack; H3 and LTX both make sound

    python3 studio/_tools/h3_stack_ab.py --arms h3_v1,h3_v4 --keys closeup,market
    python3 studio/_tools/h3_stack_ab.py --list
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
ROOT = os.path.dirname(os.path.dirname(HERE))
COMFY = os.path.expanduser("~/ComfyUI")
COMFY_IN = os.path.join(COMFY, "input")
COMFY_OUT = os.path.join(COMFY, "output")
FILMS = os.path.join(ROOT, "studio", "films")
FOUNDRY = os.path.join(ROOT, "studio", "foundry")

# Every arm renders the same picture from the same words. `extra` is dotted-path overrides
# handed to scripts/comfy.py, so an arm is exactly its recipe and nothing is hidden in a file.
ARMS = {
    "h3_v1": {
        "wf": "workflows/60_minimax_h3_i2v.json", "engine": "h3",
        "label": "H3 i2v, turbo v1.0, 4 steps res_multistep/simple, shift 5",
    },
    "h3_v4": {
        "wf": "workflows/64_minimax_h3_i2v_turbo_v4.json", "engine": "h3",
        "label": "H3 i2v, turbo v4 ema600, 8 steps euler/beta, shift 12",
    },
    "h3_v4_4step": {
        "wf": "workflows/64_minimax_h3_i2v_turbo_v4.json", "engine": "h3",
        "extra": {"32.inputs.steps": 4},
        "label": "H3 i2v, turbo v4 ema600, 4 steps euler/beta, shift 12",
    },
    # Core block sparse attention (ComfyUI >= 0.35), which has a dedicated MiniMax-H3 path.
    # Same turbo recipe as h3_v4, so the pair isolates the kernel.
    "h3_v4_sparse": {
        "wf": "workflows/67_minimax_h3_i2v_sparse.json", "engine": "h3",
        "label": "H3 i2v, v4 turbo 4 steps + BlockSparseAttention sol-attn tau 1.3",
    },
    "h3_v4_sparse_2": {
        "wf": "workflows/67_minimax_h3_i2v_sparse.json", "engine": "h3",
        "extra": {"9.inputs.selection.tau": 2.0},
        "label": "H3 i2v, v4 turbo 4 steps + BlockSparseAttention sol-attn tau 2.0 (sparser)",
    },
    # The non-turbo path, which is the only one Spectrum was written for: the LoRA at strength 0
    # and a 20-step schedule. Both arms run identically apart from the Spectrum patcher, so the
    # pair answers "is 20 steps worth it" and "does Spectrum make it affordable" at once.
    "h3_20": {
        "wf": "workflows/64_minimax_h3_i2v_turbo_v4.json", "engine": "h3",
        "extra": {"5.inputs.strength_model": 0.0, "32.inputs.steps": 20},
        "label": "H3 i2v, NO turbo LoRA, 20 steps euler/beta",
    },
    "h3_20_spec": {
        "wf": "workflows/66_minimax_h3_i2v_spectrum.json", "engine": "h3",
        "extra": {"5.inputs.strength_model": 0.0, "32.inputs.steps": 20},
        "label": "H3 i2v, NO turbo LoRA, 20 steps + Spectrum (Chebyshev forecast)",
    },
    "ltx25": {
        "wf": "workflows/70_ltx25_i2v.json", "engine": "ltx",
        # the enhancer rewrites the prompt; off, so both engines are handed the same words.
        # 1.0 MP 16:9 lands within a hair of the 1344x768 the H3 arms run at.
        "extra": {"sg1_383.inputs.value": "false", "403.inputs.megapixels": 1.0},
        "label": "LTX-2.5 22B distilled i2v (prompt enhancer off)",
    },
    # The film pipeline renders with the enhancer ON by default, and the two shots H3 was
    # brought in for are exactly the two Lantern Night lost on LTX.  With the enhancer off
    # and plain words LTX did both correctly, so the enhancer is a suspect and gets its own
    # arm rather than a guess: same graph, same words, one switch.
    "ltx25_enh": {
        "wf": "workflows/70_ltx25_i2v.json", "engine": "ltx",
        "extra": {"sg1_383.inputs.value": "true", "403.inputs.megapixels": 1.0},
        "label": "LTX-2.5 22B distilled i2v (prompt enhancer ON - the film default)",
    },
}

# (key name, source picture, the words). The words name only what is in the picture - the
# rule the book's chapter 5 is about, and the reason two earlier comparisons measured nothing.
KEYS = {
    "closeup": (os.path.join(FILMS, "lantern-night", "assets", "anchor_shot_040.png"),
                "a young woman with long pale green hair smiles slowly, her eyes close for a "
                "moment and open again, warm lantern light on her face, the camera holds still "
                "on her face"),
    "market": (os.path.join(FOUNDRY, "places", "night-market", "night_wide.png"),
               "paper lanterns sway gently on their strings over the empty stalls and their "
               "light flickers on the wet stone, nobody is there, the camera holds still"),
    "lantern": (os.path.join(FILMS, "lantern-night", "assets", "anchor_shot_030.png"),
                "a young woman with long pale green hair lifts a paper lantern in both hands "
                "and turns it slowly, looking into its light"),
}

DIALS = {
    "h3": {"image": "8.inputs.image", "text": "20.inputs.prompt", "seed": "33.inputs.noise_seed",
           "prefix": "51.inputs.filename_prefix",
           "w": "20.inputs.width", "h": "20.inputs.height", "length": "20.inputs.length"},
    "ltx": {"image": "395.inputs.image", "text": "sg1_376.inputs.value",
            "seed": "sg1_339.inputs.noise_seed", "prefix": "75.inputs.filename_prefix",
            "seconds": "sg1_362.inputs.value"},
}


def sh(*a, **kw):
    return subprocess.run(a, capture_output=True, text=True, **kw)


def h3_length(seconds, fps=24):
    """H3 wants 17n+5 frames (compose.h3_length, restated so this file runs standalone)."""
    n = max(0, (int(seconds * fps) - 5) // 17)
    return int(17 * n + 5)


def h3_size(width, height):
    """H3's VAE divides by 16 and the model patchifies the latent by 2, so every pixel
    dimension must be a multiple of 32.  Asking for 1280x720 raises a reshape error deep in
    patchify_video ("shape [...22,2,40,2] is invalid for input of size 86400") because 720/16
    is 45, an odd latent height.  Snap here instead of letting a run die 15 s in."""
    return (max(32, (width // 32) * 32), max(32, (height // 32) * 32))


def stage(src):
    """Copy a keyframe into ComfyUI/input, which is the only place LoadImage will look."""
    name = "h3ab_" + os.path.basename(src)
    shutil.copy(src, os.path.join(COMFY_IN, name))
    return name


def render(arm, staged, text, seed, seconds, width, height, prefix):
    a = ARMS[arm]
    d = DIALS[a["engine"]]
    cmd = [sys.executable, os.path.join(ROOT, "scripts", "comfy.py"), "run",
           os.path.join(ROOT, a["wf"]),
           "-s", "%s=%s" % (d["image"], staged),
           "-s", "%s=%s" % (d["text"], text),
           "-s", "%s=%d" % (d["seed"], seed),
           "-s", "%s=%s" % (d["prefix"], prefix)]
    if a["engine"] == "h3":
        w, h = h3_size(width, height)
        cmd += ["-s", "%s=%d" % (d["w"], w), "-s", "%s=%d" % (d["h"], h),
                "-s", "%s=%d" % (d["length"], h3_length(seconds))]
    else:
        cmd += ["-s", "%s=%d" % (d["seconds"], int(round(seconds)))]
    for k, v in (a.get("extra") or {}).items():
        cmd += ["-s", "%s=%s" % (k, v)]
    t0 = time.time()
    r = sh(*cmd, cwd=ROOT)
    secs = time.time() - t0
    m = re.search(r"-> (\S+\.mp4)", r.stdout or "")
    if not m:
        print("      FAILED: %s" % ((r.stderr or r.stdout or "").strip()[-400:]))
        return secs, None
    return secs, os.path.join(COMFY_OUT, m.group(1))


def probe(clip):
    n = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
           "-show_entries", "stream=nb_read_frames,r_frame_rate", "-of", "csv=p=0", clip)
    frames, fps = 0, 24.0
    parts = (n.stdout or "").strip().split(",")
    for p in parts:
        if "/" in p:
            a, _, b = p.partition("/")
            try:
                fps = float(a) / float(b or 1)
            except (ValueError, ZeroDivisionError):
                pass
        elif p.isdigit():
            frames = int(p)
    d = sh("ffmpeg", "-hide_banner", "-i", clip, "-af", "volumedetect", "-vn", "-f", "null", "-")
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", d.stderr or "")
    return frames, fps, (float(m.group(1)) if m else None)


def metrics(clip, key_path):
    r = sh(sys.executable, os.path.join(HERE, "clipmetrics.py"), clip, "--key", key_path, "--json")
    try:
        return json.loads(r.stdout)
    except (ValueError, TypeError):
        out = {}
        for tok in (r.stdout or "").split():
            k, _, v = tok.partition("=")
            try:
                out[k] = float(v)
            except ValueError:
                pass
        return out


def strip(clip, dest, n=6):
    d = sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", clip)
    try:
        dur = float((d.stdout or "0").strip())
    except ValueError:
        return None
    sh("ffmpeg", "-y", "-v", "error", "-i", clip, "-vf",
       "fps=1/%.4f,scale=320:-2,tile=%dx1" % (max(dur / n, 0.01), n), "-frames:v", "1", dest)
    return dest if os.path.exists(dest) else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--arms", default="h3_v1,h3_v4")
    p.add_argument("--keys", default="closeup,market,lantern")
    p.add_argument("--seed", type=int, default=4207)
    p.add_argument("--seconds", type=float, default=5.0)
    p.add_argument("--width", type=int, default=1344)   # the turbo LoRA's native 768p class,
    p.add_argument("--height", type=int, default=768)   # and both are multiples of 32
    p.add_argument("--tag", default="", help="a label for this run, e.g. sage_on")
    p.add_argument("--text", default="", help="override the key's words; the point of the "
                                              "tool is that everything else stays equal")
    p.add_argument("--out", default=os.path.join(ROOT, "studio", "samples", "h3stack"))
    p.add_argument("--list", action="store_true")
    a = p.parse_args()
    if a.list:
        for k, v in ARMS.items():
            print("  %-12s %s" % (k, v["label"]))
        for k, (src, _) in ((k, v) for k, v in KEYS.items()):
            print("  key %-9s %s" % (k, "MISSING " + src if not os.path.exists(src) else src))
        return
    os.makedirs(a.out, exist_ok=True)
    tag = a.tag or "run"
    rows, report = [], []
    print("%-9s %-13s %7s %8s %7s %8s %10s %8s %9s"
          % ("key", "arm", "secs", "hold_f0", "drift", "motion", "luma_drop", "frames", "audio_dB"))
    for kname in [k for k in a.keys.split(",") if k]:
        src, text = KEYS[kname]
        text = a.text or text
        if not os.path.exists(src):
            print("  %s: no such start picture: %s" % (kname, src))
            continue
        staged = stage(src)
        for arm in [x for x in a.arms.split(",") if x]:
            prefix = "claude-generated/h3stack/%s_%s_%s" % (tag, kname, arm)
            secs, clip = render(arm, staged, text, a.seed, a.seconds, a.width, a.height, prefix)
            if not clip or not os.path.exists(clip):
                rows.append({"key": kname, "arm": arm, "tag": tag, "secs": round(secs, 1),
                             "error": "no clip"})
                continue
            m = metrics(clip, src)
            frames, fps, db = probe(clip)
            dest = os.path.join(a.out, "%s_%s_%s.mp4" % (tag, kname, arm))
            shutil.copy(clip, dest)
            strip(clip, dest[:-4] + "_strip.jpg")
            row = {"key": kname, "arm": arm, "tag": tag, "secs": round(secs, 1),
                   "hold_f0": m.get("hold_f0"), "hold_last": m.get("hold_last"),
                   "drift": m.get("drift"), "motion": m.get("motion"),
                   "luma_drop": m.get("luma_drop"), "frames": frames, "fps": round(fps, 2),
                   "seconds_out": round(frames / fps, 2) if fps else None,
                   "audio_db": db, "clip": dest}
            rows.append(row)
            print("%-9s %-13s %7.1f %8.3f %7.3f %8.4f %10.3f %5d@%2.0f %9s"
                  % (kname, arm, row["secs"], row["hold_f0"] or 0, row["drift"] or 0,
                     row["motion"] or 0, row["luma_drop"] or 0, frames, fps,
                     ("%.1f" % db) if db is not None else "-"))
    out = os.path.join(a.out, "%s_report.json" % tag)
    json.dump({"arms": {k: ARMS[k]["label"] for k in a.arms.split(",") if k},
               "seed": a.seed, "seconds": a.seconds, "size": [a.width, a.height],
               "rows": rows}, open(out, "w"), indent=1)
    print("\n-> %s" % out)


if __name__ == "__main__":
    main()
