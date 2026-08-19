#!/usr/bin/env python3
"""studio/_tools/vibrancy.py - measure how vivid a grade actually is, not how it looks on a sheet.

    "the colors still don't look vibrant - something is off with the style"

Third time this has been raised. The first two times I changed the grade by eye, off a
contact sheet, and the second change was a REGRESSION - measured on one clip frame:

    no grade                        sat 0.324
    old base (contrast 1.06/sat 1.12)  sat 0.435
    filmic_warm (what I shipped)       sat 0.355

I replaced a grade with a less saturated one because it looked richer in a strip of
thumbnails. Looking is necessary and it is not sufficient; a strip at 300px flatters
contrast and hides chroma.

WHAT THIS MEASURES, per candidate, on real frames:

    sat        mean HSV saturation. The direct reading of "vibrant".
    sat_p90    the 90th percentile - how saturated the COLOURFUL parts get, which is
               what the eye actually notices. A picture can have a low mean because
               half of it is a grey wall and still read as vivid.
    val        mean HSV value. Dark kills apparent saturation regardless of chroma,
               which is why both numbers are reported and neither is read alone.
    clip       share of pixels at 250+ in any channel. A grade that wins on saturation
               by blowing the highlights has not won.

Run it on frames from the actual pipeline, not on a test pattern - a grade behaves
differently on a moody mountain than on a white product table.

    python3 studio/_tools/vibrancy.py FRAME.png [FRAME.png ...]
    python3 studio/_tools/vibrancy.py --clips atlas-showcase
"""
import argparse
import colorsys
import glob
import os
import subprocess
import sys

COMFY = os.path.expanduser("~/ComfyUI")

# id -> filter chain. Ordered from what shipped to progressively more vivid.
CANDIDATES = [
    ("none", "null"),
    ("old_base", "eq=contrast=1.06:saturation=1.12"),
    ("filmic_warm", "curves=all='0/0.02 0.22/0.26 0.5/0.58 0.78/0.88 1/0.995',"
                    "eq=saturation=1.22,colorbalance=gm=-0.05:rm=0.05:bh=0.03"),
    ("vivid", "eq=contrast=1.10:saturation=1.45"),
    ("vivid_lift", "curves=all='0/0.02 0.22/0.28 0.5/0.60 0.78/0.88 1/0.995',"
                   "eq=saturation=1.42"),
    # `vibrance` raises MUTED colours much more than already-saturated ones, so it adds
    # life without turning skin and sky into poster paint. This is the filter most
    # colourists reach for when the note is "not vibrant".
    ("vibrance", "eq=contrast=1.08,vibrance=intensity=0.55,eq=saturation=1.15"),
    ("vibrance_lift", "curves=all='0/0.02 0.22/0.28 0.5/0.60 0.78/0.88 1/0.995',"
                      "vibrance=intensity=0.60,eq=saturation=1.12"),
]


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def stats(path):
    from PIL import Image
    im = Image.open(path).convert("RGB").resize((200, 266))
    px = list(im.getdata())
    sats, vals, clipped = [], [], 0
    for r, g, b in px:
        _h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        sats.append(s)
        vals.append(v)
        if r > 250 or g > 250 or b > 250:
            clipped += 1
    sats.sort()
    return {"sat": sum(sats) / len(sats),
            "sat_p90": sats[int(0.90 * (len(sats) - 1))],
            "val": sum(vals) / len(vals),
            "clip": clipped / float(len(px))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frames", nargs="*")
    ap.add_argument("--clips", default="",
                    help="a film slug under 12-shorts; samples a frame from each clip")
    ap.add_argument("--out", default=os.path.expanduser("~/shared/AB/vibrancy"))
    a = ap.parse_args()

    frames = list(a.frames)
    if a.clips:
        d = os.path.join(COMFY, "output", "claude-generated", "12-shorts", a.clips,
                         "clips")
        for i, c in enumerate(sorted(glob.glob(os.path.join(d, "*.mp4")))):
            f = "/tmp/_vib_src%d.png" % i
            sh("ffmpeg", "-y", "-v", "error", "-ss", "1", "-i", c, "-frames:v", "1", f)
            if os.path.exists(f):
                frames.append(f)
    if not frames:
        sys.exit("give some frames, or --clips <slug>")
    os.makedirs(a.out, exist_ok=True)

    print("%d source frame(s). higher sat and sat_p90 is more vivid; val must not fall;"
          % len(frames))
    print("clip is blown highlights - a grade that wins by clipping has not won.\n")
    print("%-15s %7s %8s %7s %7s" % ("grade", "sat", "sat_p90", "val", "clip"))
    rows = []
    for name, vf in CANDIDATES:
        acc = {"sat": 0.0, "sat_p90": 0.0, "val": 0.0, "clip": 0.0}
        n = 0
        for i, f in enumerate(frames):
            dst = os.path.join(a.out, "%s_%d.png" % (name, i))
            sh("ffmpeg", "-y", "-v", "error", "-i", f, "-vf", vf, "-frames:v", "1", dst)
            if not os.path.exists(dst):
                continue
            s = stats(dst)
            for k in acc:
                acc[k] += s[k]
            n += 1
        if not n:
            print("%-15s  FILTER FAILED" % name)
            continue
        for k in acc:
            acc[k] /= n
        rows.append((name, acc))
        print("%-15s %7.3f %8.3f %7.3f %7.3f"
              % (name, acc["sat"], acc["sat_p90"], acc["val"], acc["clip"]))

    base = dict(rows).get("none")
    if base:
        print("\nagainst no grade at all:")
        for name, acc in rows:
            if name == "none":
                continue
            print("  %-15s sat %+6.1f%%   val %+6.1f%%   clip %+.3f"
                  % (name, 100 * (acc["sat"] / base["sat"] - 1),
                     100 * (acc["val"] / base["val"] - 1),
                     acc["clip"] - base["clip"]))
    print("\nframes written to %s - LOOK at them before choosing." % a.out)


if __name__ == "__main__":
    main()
