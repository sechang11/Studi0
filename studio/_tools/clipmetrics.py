#!/usr/bin/env python3
"""studio/_tools/clipmetrics.py - the four numbers that separate "holds the keyframe"
from "drifts away", and "moves" from "frozen". One instrument, used by every video
comparison from here on.

    python3 studio/_tools/clipmetrics.py CLIP.mp4 --key KEYFRAME.png

    hold_f0     SSIM, clip frame 0 vs the keyframe. Codec + VAE + redraw only; nothing
                has moved yet, so this is the clean "did the engine repaint my frame".
    hold_last   SSIM, final frame vs the keyframe. LOW is ambiguous by itself - a clip
                that correctly animates scores low here - so it is read against motion.
    motion      mean frame-to-frame absolute luma difference (per second of clip, at a
                common 8fps time base so engines at 24 and 16fps compare).
    drift       hold_f0 - hold_last. HIGH means the picture walked away from the frame
                you approved; that is the LTX failure mode the film pipeline pays for,
                and it is NOT the same as motion.

A good i2v pass for this project is HIGH hold_f0, LOW drift, NON-ZERO motion. An engine
that scores low drift only because it froze is caught by motion being ~0 - which is why
both numbers are always reported together.
"""
import argparse
import json
import os
import subprocess
import sys


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def frames(clip, out_dir, fps=8):
    os.makedirs(out_dir, exist_ok=True)
    sh("ffmpeg", "-y", "-v", "error", "-i", clip, "-vf", "fps=%d,scale=320:-2" % fps,
       os.path.join(out_dir, "f%04d.png"))
    return sorted(os.path.join(out_dir, f) for f in os.listdir(out_dir)
                  if f.endswith(".png"))


def ssim(a, b):
    """SSIM via ffmpeg, both scaled to the first input."""
    r = sh("ffmpeg", "-v", "error", "-i", a, "-i", b, "-lavfi",
           "[0:v][1:v]scale2ref[x][y];[x][y]ssim=stats_file=-", "-f", "null", "-")
    for tok in (r.stdout or "").split():
        if tok.startswith("All:"):
            try:
                return float(tok.split(":")[1])
            except ValueError:
                pass
    return None


def mad(a, b):
    from PIL import Image, ImageChops
    ia, ib = Image.open(a).convert("L"), Image.open(b).convert("L")
    if ia.size != ib.size:
        ib = ib.resize(ia.size)
    px = list(ImageChops.difference(ia, ib).getdata())
    return sum(px) / len(px)


def measure(clip, key=None, workdir=None):
    workdir = workdir or (os.path.splitext(clip)[0] + "_frames")
    fs = frames(clip, workdir)
    if len(fs) < 2:
        return {"error": "fewer than two frames"}
    out = {"frames_sampled": len(fs)}
    if key and os.path.exists(key):
        out["hold_f0"] = ssim(key, fs[0])
        out["hold_last"] = ssim(key, fs[-1])
        if out["hold_f0"] is not None and out["hold_last"] is not None:
            out["drift"] = round(out["hold_f0"] - out["hold_last"], 4)
    steps = [mad(fs[i], fs[i + 1]) for i in range(len(fs) - 1)]
    out["motion"] = round(sum(steps) / len(steps), 3)
    out["motion_max"] = round(max(steps), 3)
    # a clip whose motion is all in one place is a cut/pop, not a move
    out["motion_evenness"] = round((sum(steps) / len(steps)) / max(max(steps), 1e-6), 3)
    for f in fs:
        os.remove(f)
    try:
        os.rmdir(workdir)
    except OSError:
        pass
    return out


def main():
    ap = argparse.ArgumentParser(description="hold / drift / motion for one clip.")
    ap.add_argument("clip")
    ap.add_argument("--key")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    m = measure(a.clip, a.key)
    print(json.dumps(m, indent=1) if a.json else
          " ".join("%s=%s" % (k, v) for k, v in m.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
