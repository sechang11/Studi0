#!/usr/bin/env python3
"""Time passes: the place's own plates, in order, dissolved into one shot.

A place in the foundry has plates for several times of day (dawn_wide,
day_wide, dusk_wide, night_wide ...).  They were made from one description, so
they agree on the geometry and disagree only in light - which is exactly what
a time-lapse is.  Nothing is generated: each plate holds for `hold` seconds,
cross-dissolves over `fade` seconds into the next, and the whole shot carries a
slow push (or none).  Deterministic, so the same call gives the same pixels.

    python3 platefade.py <place_dir> <out.mp4> [--plates dawn_wide,day_wide,dusk_wide,night_wide]
                         [--hold 2.0] [--fade 1.2] [--push 1.06] [--fps 24] [--w 1920 --h 1080]
    from platefade import render; render(place_dir, out, plates=None, hold=2.0, fade=1.2, push=1.06)
"""
import json
import math
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

ORDER = ["dawn", "morning", "day", "afternoon", "golden", "dusk", "evening", "night", "late_night"]


def pick_plates(place_dir, key="wide"):
    """the place's plates of one framing key, in time-of-day order"""
    found = []
    for f in os.listdir(place_dir):
        if not f.endswith(".png") or f.endswith("_depth.png"):
            continue
        stem = f[:-4]
        if not stem.endswith("_" + key):
            continue
        tod = stem[: -(len(key) + 1)]
        rank = next((i for i, o in enumerate(ORDER) if tod == o), None)
        if rank is None:
            rank = next((i for i, o in enumerate(ORDER) if o in tod), len(ORDER))
        found.append((rank, stem))
    return [s for _, s in sorted(found)]


def _smooth(u):
    return u * u * (3 - 2 * u)


def render(place_dir, out, plates=None, hold=2.0, fade=1.2, push=1.06, fps=24, w=1920, h=1080, crf=16):
    stems = plates or pick_plates(place_dir)
    if len(stems) < 2:
        raise SystemExit("need at least two plates of one framing in %s (found %s)" % (place_dir, stems))
    ims = []
    for s in stems:
        im = Image.open(os.path.join(place_dir, s + ".png")).convert("RGB")
        # letterbox-free: cover the output aspect, then centre crop
        scale = max(w / im.width, h / im.height)
        im = im.resize((int(math.ceil(im.width * scale)), int(math.ceil(im.height * scale))), Image.LANCZOS)
        left, top = (im.width - w) // 2, (im.height - h) // 2
        ims.append(np.asarray(im.crop((left, top, left + w, top + h))).astype(np.float32))
    n_hold, n_fade = int(round(hold * fps)), int(round(fade * fps))
    total = len(ims) * n_hold + (len(ims) - 1) * n_fade
    tmp = tempfile.mkdtemp(prefix="platefade_")
    idx = 0
    for k, im in enumerate(ims):
        for _ in range(n_hold):
            _emit(im, idx, total, push, w, h, tmp)
            idx += 1
        if k + 1 < len(ims):
            for j in range(n_fade):
                a = _smooth((j + 1) / (n_fade + 1))
                _emit(im * (1 - a) + ims[k + 1] * a, idx, total, push, w, h, tmp)
                idx += 1
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(fps), "-i", os.path.join(tmp, "f%05d.png"),
                    "-c:v", "libx264", "-crf", str(crf), "-pix_fmt", "yuv420p", out], check=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    return {"plates": stems, "frames": total, "seconds": round(total / fps, 2), "hold": hold, "fade": fade, "push": push, "file": out}


def _emit(arr, i, total, push, w, h, tmp):
    u = i / max(1, total - 1)
    z = 1.0 + (push - 1.0) * _smooth(u) if push and push != 1.0 else 1.0
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if z != 1.0:
        vw, vh = int(round(w / z)), int(round(h / z))
        left, top = (w - vw) // 2, (h - vh) // 2
        im = im.crop((left, top, left + vw, top + vh)).resize((w, h), Image.LANCZOS)
    im.save(os.path.join(tmp, "f%05d.png" % i))


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        print(__doc__)
        sys.exit(1)
    place_dir, out = a[0], a[1]
    kw = {}
    rest = a[2:]
    while rest:
        k = rest.pop(0)
        if k == "--plates":
            kw["plates"] = rest.pop(0).split(",")
        elif k == "--hold":
            kw["hold"] = float(rest.pop(0))
        elif k == "--fade":
            kw["fade"] = float(rest.pop(0))
        elif k == "--push":
            kw["push"] = float(rest.pop(0))
        elif k == "--fps":
            kw["fps"] = int(rest.pop(0))
        elif k == "--w":
            kw["w"] = int(rest.pop(0))
        elif k == "--h":
            kw["h"] = int(rest.pop(0))
    print(json.dumps(render(place_dir, out, **kw)))
