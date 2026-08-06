#!/usr/bin/env python3
"""First-to-last drift per clip, and the drift up to the frame the EDIT actually keeps.

Two numbers per beat, because they answer different questions:

  drift_full  first frame vs last frame of the generated clip - how far the model went.
  drift_cut   first frame vs the last frame the template's slice keeps - how far the
              FILM goes. This is the one that matters, and it is usually much smaller,
              because the whole thesis of short.py is generate long and cut short.

A beat where drift_full is large and drift_cut is small is not a broken clip: it is a
clip whose collapse happens after the cut. A beat where drift_cut is large is a shot the
audience will see fall apart.

Mean absolute difference over RGB, 0-255. The strip beside it says what changed.
"""
import json, os, subprocess, sys

from PIL import Image, ImageChops, ImageStat

sys.path.insert(0, os.path.expanduser("~/shared/comfy-studio/scripts"))
from scene_templates import expand as expand_template            # noqa: E402

H = os.path.expanduser("~")
OUT = f"{H}/ComfyUI/output/claude-generated/12-shorts/the-coat"
film = json.load(open(f"{H}/shared/comfy-studio/studio/samples/the_film/"
                      "terra_field_coat.json", encoding="utf-8"))
TMP = "/tmp/_drift"
os.makedirs(TMP, exist_ok=True)


def frame(src, t, tag):
    p = f"{TMP}/{tag}.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", src,
                    "-frames:v", "1", "-vf", "scale=320:-2", p], check=True)
    return Image.open(p).convert("RGB")


def mad(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3.0


def dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", p], capture_output=True, text=True)
    return float(r.stdout.strip())


print(f"{'#':>2} {'beat':32s} {'len':>6} {'cut':>12} {'drift_full':>10} {'drift_cut':>9}")
for i, b in enumerate(film["beats"], 1):
    src = f"{OUT}/clips/{b['id']}_00001_.mp4"
    if not os.path.exists(src):
        print(f"{i:2d} {b['id']:32s}  NO CLIP")
        continue
    d = dur(src)
    cuts, _ = expand_template(b, float(b.get("clip_secs", 4)))
    end = max(min(c["at"] + c["len"], d - 0.05) for c in cuts)
    f0 = frame(src, 0.0, "a")
    fl = frame(src, max(d - 0.1, 0), "b")
    fc = frame(src, end, "c")
    print(f"{i:2d} {b['id']:32s} {d:5.2f}s {cuts[0]['at']:.2f}-{end:.2f}s "
          f"{mad(f0, fl):10.2f} {mad(f0, fc):9.2f}")
