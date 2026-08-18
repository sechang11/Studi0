#!/usr/bin/env python3
"""studio/_tools/grade_options.py - candidate base grades, side by side, to be picked by eye.

    "the colors can still use some work, maybe more contrast or brightness, i'm not sure
     exactly what it is, but it doesn't feel alive"

That is not a number, and guessing at it is how this project has burned time before. So
this renders the SAME delivered frame through several candidate base grades and labels
each one, because a grade is chosen by looking and the only useful thing I can do is put
the options next to each other.

The current base is deliberately gentle - `eq=contrast=1.06:saturation=1.12` - and its
comment says why: it multiplies with the per-shot `hot` effect and at 1.12x1.45 saturation
whole shots went neon magenta. So every candidate here is checked at BOTH ends: alone, and
stacked with `hot`, which is the case that actually broke.

    python3 studio/_tools/grade_options.py FRAME.png [--out DIR]
    python3 studio/_tools/grade_options.py --film ~/shared/SHORTS-v3/ad-northwind-tea.mp4
"""
import argparse
import os
import subprocess
import sys

# (id, base grade, one line on what it is going for)
CANDIDATES = [
    ("current", "eq=contrast=1.06:saturation=1.12",
     "the control - what ships today"),
    ("lift", "eq=brightness=0.05:contrast=1.18:saturation=1.20",
     "open it up: brighter, more range, more colour, all at once"),
    ("filmic", "curves=all='0/0.02 0.22/0.26 0.5/0.58 0.78/0.88 1/0.995',"
               "eq=saturation=1.24",
     "an S-curve that LIFTS the mids rather than crushing them - the shadows keep "
     "their detail and the midtones come up, which is usually what 'flat' means"),
    ("filmic_warm", "curves=all='0/0.02 0.22/0.26 0.5/0.58 0.78/0.88 1/0.995',"
                    "eq=saturation=1.22,colorbalance=gm=-0.05:rm=0.05:bh=0.03",
     "the same lift, minus the green lean measured in the mids (+4.2 over R/B) and "
     "a little warmth back in"),
]

# The effect that broke the last saturation experiment. Every candidate is also shown
# stacked with it, because that is the combination that actually ships on punchy shots.
HOT = "eq=contrast=1.10:saturation=1.18,vibrance=intensity=0.22"


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def label_render(src, vf, label, dst, width=440):
    fc = ("%s,scale=%d:-2,pad=iw:ih+30:0:30:color=black,"
          "drawtext=text='%s':fontcolor=white:fontsize=24:x=10:y=5"
          % (vf, width, label.replace(":", r"\:").replace("'", "")))
    r = sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vf", fc, "-frames:v", "1", dst)
    return dst if os.path.exists(dst) else (r.stderr or "")[-200:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frame", nargs="?", help="a PNG to grade")
    ap.add_argument("--film", help="pull a frame from this film instead")
    ap.add_argument("--at", type=float, default=4.0)
    ap.add_argument("--out", default=os.path.expanduser("~/shared/AB/grades"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    src = a.frame
    if a.film:
        src = os.path.join(a.out, "_src.png")
        sh("ffmpeg", "-y", "-v", "error", "-ss", "%.2f" % a.at, "-i", a.film,
           "-frames:v", "1", src)
    if not src or not os.path.exists(src):
        sys.exit("no frame: pass a PNG or --film")

    rows = []
    for cid, vf, why in CANDIDATES:
        plain = label_render(src, vf, cid, os.path.join(a.out, "%s.png" % cid))
        stacked = label_render(src, vf + "," + HOT, cid + " + hot",
                               os.path.join(a.out, "%s_hot.png" % cid))
        rows.append((cid, plain, stacked, why))
        print("  %-12s %s" % (cid, why))

    ok = [r for r in rows if os.path.exists(str(r[1])) and os.path.exists(str(r[2]))]
    if not ok:
        sys.exit("no candidate rendered - check the filter strings")

    # two rows: the grade alone on top, the same grade stacked with `hot` underneath,
    # because the stacked case is the one that has broken before
    top = os.path.join(a.out, "_row_plain.png")
    bot = os.path.join(a.out, "_row_hot.png")
    sh(*(["ffmpeg", "-y", "-v", "error"]
         + sum([["-i", r[1]] for r in ok], [])
         + ["-filter_complex", "hstack=%d" % len(ok), "-frames:v", "1", top]))
    sh(*(["ffmpeg", "-y", "-v", "error"]
         + sum([["-i", r[2]] for r in ok], [])
         + ["-filter_complex", "hstack=%d" % len(ok), "-frames:v", "1", bot]))
    sheet = os.path.join(a.out, "grades.png")
    sh("ffmpeg", "-y", "-v", "error", "-i", top, "-i", bot,
       "-filter_complex", "vstack", "-frames:v", "1", sheet)
    print("\ntop row: the grade alone.  bottom row: the same grade stacked with `hot`,")
    print("which is the combination that turned shots magenta the last time saturation moved.")
    print("sheet: %s" % sheet)


if __name__ == "__main__":
    main()
