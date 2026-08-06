#!/usr/bin/env python3
"""One frame strip per generated clip: 8 frames evenly spaced, timestamped, plus a
first-to-last drift number so "the face left frame before the cut" is measurable and not
just an impression.

The identity budget on this box is BY THE ACTION, not by the clock - on a head turn the
face is frontal to 5s and back-of-head by 8s - so the question a strip has to answer is
"where is she at second N", which a single thumbnail cannot.

drift is the mean absolute pixel difference between the first and last frame, scaled to
0-100. It is a blunt instrument and it is meant to be: it separates a clip that held from
a clip that dissolved, and the strip above it says which.
"""
import json, os, subprocess, sys

HOME = os.path.expanduser("~")
OUT = f"{HOME}/ComfyUI/output/claude-generated/12-shorts/the-coat"
DST = f"{HOME}/shared/comfy-studio/studio/samples/the_film/strips"
FILM = f"{HOME}/shared/comfy-studio/studio/samples/the_film/terra_field_coat.json"
N = 8


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def dur(p):
    r = sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "csv=p=0", p)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


os.makedirs(DST, exist_ok=True)
film = json.load(open(FILM, encoding="utf-8"))
rows = []
for i, b in enumerate(film["beats"], 1):
    src = f"{OUT}/clips/{b['id']}_00001_.mp4"
    if not os.path.exists(src):
        print(f"{i:2d} {b['id']:32s} NO CLIP")
        continue
    d = dur(src)
    ins, fc = [], []
    for k in range(N):
        t = d * k / N
        ins += ["-ss", f"{t:.3f}", "-i", src]
        fc.append(f"[{k}:v]scale=440:-2,drawtext=text='{t:.1f}s':fontsize=30:"
                  f"fontcolor=yellow:box=1:boxcolor=black:x=6:y=6[v{k}]")
    fc += ["[v0][v1][v2][v3]hstack=4[r0]", "[v4][v5][v6][v7]hstack=4[r1]",
           "[r0][r1]vstack=2"]
    sh("ffmpeg", "-y", "-v", "error", *ins, "-frames:v", "1",
       "-filter_complex", ";".join(fc), "-q:v", "3", f"{DST}/{i:02d}_{b['id']}.jpg")
    r = sh("ffmpeg", "-v", "error", "-i", src, "-vf",
           f"select='eq(n,0)+gte(t,{max(d - 0.1, 0):.3f})',tblend=all_mode=difference,"
           f"signalstats,metadata=print:key=lavfi.signalstats.YAVG",
           "-f", "null", "-")
    vals = [float(x.split("=")[-1]) for x in r.stderr.splitlines() if "YAVG" in x]
    drift = max(vals[1:]) if len(vals) > 1 else (vals[0] if vals else 0.0)
    rows.append((i, b["id"], d, drift))
    print(f"{i:2d} {b['id']:32s} {d:5.2f}s  drift {drift:6.2f}")
print(f"\nstrips -> {DST}")
