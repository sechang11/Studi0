#!/usr/bin/env python3
"""studio/_tools/multishot.py - LTX-2.5's native multi-shot, tested and measured.

    python3 studio/_tools/multishot.py --shots "wide of the deck|close on the wheel|the sky" \\
        [--key K.png] [--seconds 10] [--out DIR]

WHY THIS IS THE POINT. Multi-shot consistency is the one thing this box could not do:
Seedance-class models hold character, environment and lighting across CUTS because they
generate the cut. Locally we have faked it with the master-frame kit (one hero still,
derived angles). LTX-2.5 claims to generate connected shots in ONE pass. If that is true
here, it is the biggest single capability gain in the video path, and the master-frame kit
becomes the fallback rather than the only road.

THE MEASUREMENT, because "it looks cut" is not evidence. A cut is a single-frame
discontinuity: frame-to-frame difference spikes far above the clip's own baseline while
the frames on either side are internally stable. cuts() finds those spikes with a
threshold derived from the clip itself (median + k*MAD, robust to a clip that is mostly
still), reports where they land in seconds, and reports the number asked for beside the
number found. Consistency across the cut is then a SEPARATE question, measured by
comparing the last frame before a cut with the first after: a scene that holds should
share palette and structure even though the framing changed.
"""
import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, STUDIO)
sys.path.insert(0, TOOLS)
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run, set_path              # noqa: E402
from engine import load_wf, HOST             # noqa: E402

COMFY = os.environ.get("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def cuts(clip, fps=8, k=6.0):
    """Cut timestamps by robust spike detection on frame-to-frame difference.

    Threshold is median + k*MAD of the clip's OWN differences, so a mostly-still clip and
    a busy one are both judged against themselves. A hand-set absolute threshold was the
    first attempt and it called every fast pan a cut."""
    from PIL import Image, ImageChops
    d = os.path.join("/tmp", "ms_%d" % (abs(hash(clip)) % 99999))
    os.makedirs(d, exist_ok=True)
    sh("ffmpeg", "-y", "-v", "error", "-i", clip, "-vf",
       "fps=%d,scale=320:-2" % fps, os.path.join(d, "f%04d.png"))
    fs = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".png"))
    if len(fs) < 3:
        shutil.rmtree(d, ignore_errors=True)
        return [], []
    diffs = []
    for i in range(len(fs) - 1):
        a, b = Image.open(fs[i]).convert("L"), Image.open(fs[i + 1]).convert("L")
        px = list(ImageChops.difference(a, b).getdata())
        diffs.append(sum(px) / len(px))
    med = statistics.median(diffs)
    mad = statistics.median([abs(x - med) for x in diffs]) or 1e-6
    thr = med + k * mad
    at = [round((i + 1) / fps, 2) for i, x in enumerate(diffs) if x > thr]
    # collapse neighbours: one cut can straddle two sampled frames
    merged = []
    for t in at:
        if not merged or t - merged[-1] > 2.0 / fps:
            merged.append(t)
    shutil.rmtree(d, ignore_errors=True)
    return merged, [round(x, 2) for x in diffs]


# The ResolutionSelector's own options; nothing here is invented.
AR_PORTRAIT = "9:16 (Portrait Widescreen)"
AR_LANDSCAPE = "16:9 (Widescreen)"
AR_SQUARE = "1:1 (Square)"


def aspect_for(key):
    """Match the generated shape to the keyframe's, the way short.py's set_format does.

    Workflow 51 pins 16:9. Handed a portrait keyframe it returned a landscape clip and
    clipmetrics scored the pair at hold_f0 0.117 - almost all of which was the shape
    mismatch, not the model failing to hold the frame.
    """
    from PIL import Image
    w, h = Image.open(key).size
    if abs(w - h) / float(max(w, h)) < 0.05:
        return AR_SQUARE
    return AR_PORTRAIT if h > w else AR_LANDSCAPE


def render(shots, key, seconds, out, seed=1234, expand=False, aspect=None):
    """One LTX-2.5 pass asked for several connected shots."""
    prompt = " ".join(
        "Shot %d: %s." % (i + 1, s.strip().rstrip(".")) for i, s in enumerate(shots))
    prompt += (" The shots are connected: the same place, the same characters, the same "
               "lighting and the same visual style across every cut.")
    wf = load_wf("51_ltx25_i2v.json")
    staged = "multishot_key.png"
    shutil.copy(key, os.path.join(COMFY, "input", staged))
    set_path(wf, "395.inputs.image", staged)
    set_path(wf, "376.inputs.value", prompt)
    set_path(wf, "383.inputs.value", bool(expand))   # LLM prompt expander on/off
    set_path(wf, "362.inputs.value", int(seconds))
    set_path(wf, "403.inputs.aspect_ratio", aspect or aspect_for(key))
    set_path(wf, "339.inputs.noise_seed", seed)
    set_path(wf, "338.inputs.noise_seed", seed)
    set_path(wf, "75.inputs.filename_prefix", "claude-generated/multishot/ms")
    _, outs = run(HOST, wf, quiet=True)
    for o in outs or []:
        if str(o).lower().endswith((".mp4", ".webm", ".mov")):
            src = os.path.join(COMFY, "output", o)
            if os.path.exists(src):
                shutil.copy(src, out)
                return out, prompt
    return None, prompt


def main():
    ap = argparse.ArgumentParser(description="LTX-2.5 native multi-shot, measured.")
    ap.add_argument("--shots", required=True, help="pipe-separated shot descriptions")
    ap.add_argument("--key", default=os.path.join(
        STUDIO, "samples", "isolation", "places", "clean_airship_deck_0.png"))
    ap.add_argument("--seconds", type=float, default=10)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--expand", action="store_true", help="use the LLM prompt enhancer")
    ap.add_argument("--out", default=os.path.join(STUDIO, "samples", "multishot"))
    ap.add_argument("--tag", default="ms")
    ap.add_argument("--aspect", default=None,
                    help="override; default follows the keyframe's own shape")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    shots = [s for s in a.shots.split("|") if s.strip()]
    dst = os.path.join(a.out, "%s.mp4" % a.tag)
    clip, prompt = render(shots, a.key, a.seconds, dst, a.seed, a.expand, a.aspect)
    if not clip:
        print("no clip produced", file=sys.stderr)
        return 1
    at, diffs = cuts(clip)
    import clipmetrics
    m = clipmetrics.measure(clip, a.key)
    rep = {"shots_asked": len(shots), "cuts_found": len(at), "cut_seconds": at,
           "prompt": prompt, "clip": clip, "metrics": m,
           "expander": bool(a.expand), "seed": a.seed}
    json.dump(rep, open(os.path.join(a.out, "%s.json" % a.tag), "w"), indent=1)
    # a strip wide enough to see every shot
    sh("ffmpeg", "-y", "-v", "error", "-i", clip, "-vf",
       "fps=1.5,scale=260:-2,tile=%dx1" % max(6, int(a.seconds * 1.5)),
       os.path.join(a.out, "%s_strip.png" % a.tag))
    print("aspect %s (from %s)" % (a.aspect or aspect_for(a.key),
                                   "--aspect" if a.aspect else "the keyframe"))
    print("asked %d shots, found %d cuts at %s" % (len(shots), len(at), at))
    print("metrics:", " ".join("%s=%s" % (k, v) for k, v in m.items()))
    print("strip:", os.path.join(a.out, "%s_strip.png" % a.tag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
