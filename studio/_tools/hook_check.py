#!/usr/bin/env python3
"""studio/_tools/hook_check.py - what the first second of a film actually does.

    "what would you use to grab a human's attention?"

A feed gives a film one poster frame and then about half a second of motion to earn the
next half. Everything this project has measured so far - brightness, saturation, cuts,
sync, drift - describes a WHOLE film, and a whole film is a thing nobody reaches unless
the opening works. So measure the opening on its own terms.

    frame0_luma     brightness of the poster frame. A dark thumbnail in a bright feed
                    loses before it starts.
    frame0_sat      saturation of the poster frame.
    motion_0_5      mean frame-to-frame change over the first HALF second, against the
                    film's own average. Below 1.0 means the film opens slower than it
                    runs - the worst possible arrangement, since the opening is the only
                    part with no audience yet.
    motion_1_0      the same over the first second.
    first_cut       when the picture first changes. A feed short that holds one shot for
                    four seconds has spent its entire budget of attention on one image.
    text_at_0       does the poster frame carry the hook text? (measured as ink in the
                    top third)

NO TARGETS ASSERTED. A luxury brand opening on a slow static plate is a choice. The
numbers exist so the choice is visible, because right now every film in this slate makes
the same one and nobody decided it.
"""
import argparse
import glob
import os
import statistics
import subprocess
import sys


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def frames(clip, upto=None, fps=12):
    d = "/tmp/_hk_%d" % (abs(hash(clip)) % 99999)
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))
    cmd = ["ffmpeg", "-y", "-v", "error"]
    if upto:
        cmd += ["-t", str(upto)]
    cmd += ["-i", clip, "-vf", "fps=%d,scale=160:-2" % fps,
            os.path.join(d, "f%04d.png")]
    sh(*cmd)
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".png"))


def mad(a, b):
    from PIL import Image, ImageChops
    ia, ib = Image.open(a).convert("L"), Image.open(b).convert("L")
    px = ImageChops.difference(ia, ib).getdata()
    return sum(px) / len(px)


def frame_stats(p):
    import colorsys
    from PIL import Image
    im = Image.open(p).convert("RGB").resize((120, 160))
    px = list(im.getdata())
    lum = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in px) / len(px)
    sat = sum(colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)[1]
              for r, g, b in px) / len(px)
    # ink in the top third: near-white pixels where the hook sits
    top = px[:len(px) // 3]
    ink = sum(1 for r, g, b in top if r > 220 and g > 220 and b > 220) / float(len(top))
    return lum, sat, ink


def check(path):
    fs = frames(path)
    if len(fs) < 6:
        return {"film": os.path.basename(path), "note": "too short to read"}
    steps = [mad(a, b) for a, b in zip(fs, fs[1:])]
    # AGAINST THE MEDIAN, not the mean. A cut is a frame difference an order of magnitude
    # above any real motion, so a mean is mostly cuts - and the first half-second contains
    # no cut, which made every film look like it opened at a third of its own pace. The
    # source clips are flat: 0.75 to 0.85 across five seconds. There is no slow opening,
    # there is only a metric that was measuring "is there a cut in this window".
    typical = statistics.median(steps) or 1e-6
    half = 6                                                 # 12fps -> 0.5s
    m05 = statistics.mean(steps[:half]) / typical
    m10 = statistics.mean(steps[:half * 2]) / typical
    m05_abs = statistics.mean(steps[:half])
    # first cut: first step more than 4x the median step
    med = statistics.median(steps) or 1e-6
    cut = next((i / 12.0 for i, s in enumerate(steps) if s > 4 * med), None)
    lum, sat, ink = frame_stats(fs[0])
    for f in fs:
        os.remove(f)
    return {"film": os.path.basename(path)[:-4], "motion_abs": round(m05_abs, 2),
            "f0_luma": round(lum, 1), "f0_sat": round(sat, 3),
            "motion_0_5": round(m05, 2), "motion_1_0": round(m10, 2),
            "first_cut": round(cut, 2) if cut else None,
            "text_at_0": round(ink, 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("films", nargs="*")
    ap.add_argument("--dir", default=os.path.expanduser("~/shared/SHORTS-v5"))
    a = ap.parse_args()
    paths = a.films or sorted(glob.glob(os.path.join(a.dir, "*.mp4")))
    if not paths:
        sys.exit("no films")
    rows = [check(p) for p in paths]
    rows = [r for r in rows if "f0_luma" in r]
    rows.sort(key=lambda r: r["motion_0_5"])
    print("%-22s %8s %7s %8s %9s %9s %8s"
          % ("film", "f0 luma", "f0 sat", "mot abs", "vs median", "first cut", "text"))
    for r in rows:
        flag = ""
        if r["first_cut"] is None or r["first_cut"] > 2.5:
            flag = "  <- holds shot one past 2.5s"
        print("%-22s %8.1f %7.3f %8.2f %9.2f %9s %8.4f%s"
              % (r["film"][:22], r["f0_luma"], r["f0_sat"], r["motion_abs"],
                 r["motion_0_5"],
                 ("%.2fs" % r["first_cut"]) if r["first_cut"] else "none",
                 r["text_at_0"], flag))
    n = len(rows)
    nocut = [r for r in rows if not r["first_cut"] or r["first_cut"] > 2.5]
    print("\n%d films - median opening motion %.2f absolute, %.2fx the film's median step"
          % (n, statistics.median([r["motion_abs"] for r in rows]),
             statistics.median([r["motion_0_5"] for r in rows])))
    print("%d hold their first shot past 2.5s." % len(nocut))
    print("The generated footage is uniformly slow - a source clip measures 0.75 to 0.85")
    print("across its whole length - so on this material the CUT is what makes pace.")
    print("The lever for attention is the edit and the subject, not the camera move.")


if __name__ == "__main__":
    main()
