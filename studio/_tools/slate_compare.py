#!/usr/bin/env python3
"""studio/_tools/slate_compare.py - the old slate against the new one, to be LOOKED AT.

The rule here is that video is judged by watching and the numbers only say where to look,
so a rebuild that reports "+59% luma" and nothing else has not actually been checked. This
pairs each delivered film with its predecessor, puts a frame from each side by side, and
prints the measurement underneath - so the claim and the evidence for it arrive together.

    python3 studio/_tools/slate_compare.py
    python3 studio/_tools/slate_compare.py --old ~/shared/SHORTS --new ~/shared/SHORTS-v3

Pairing is by slug, because the old slate files carry their titles
(commercial/ad-lumen-lamp__LUMEN.mp4) and the new ones do not (ad-lumen-lamp.mp4). A film
present on only one side is reported rather than skipped - a rebuild that quietly dropped
a film is exactly the kind of thing this project keeps shipping.
"""
import argparse
import json
import os
import re
import subprocess


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def slug(path):
    b = os.path.splitext(os.path.basename(path))[0]
    return b.split("__")[0]


def films(root):
    out = {}
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            if f.endswith(".mp4"):
                out[slug(f)] = os.path.join(dp, f)
    return out


def luma_stats(path):
    r = sh("ffprobe", "-v", "error", "-f", "lavfi",
           "-i", "movie=%s,signalstats" % path.replace(":", "\\:"),
           "-show_entries", "frame_tags=lavfi.signalstats.YAVG",
           "-of", "default=nw=1:nk=1")
    ys = []
    for line in (r.stdout or "").splitlines():
        try:
            ys.append(float(line.strip()))
        except ValueError:
            pass
    if not ys:
        return None
    return {"yavg": round(sum(ys) / len(ys), 1),
            "p_dark": round(sum(1 for y in ys if y < 64) / len(ys), 3)}


def pair_image(old, new, dst, at=3.0):
    """One frame from each, side by side, labelled."""
    fc = ("[0:v]scale=340:-2,pad=iw:ih+34:0:34:color=black,"
          "drawtext=text='BEFORE':fontcolor=white:fontsize=22:x=10:y=6[a];"
          "[1:v]scale=340:-2,pad=iw:ih+34:0:34:color=black,"
          "drawtext=text='AFTER':fontcolor=white:fontsize=22:x=10:y=6[b];"
          "[a][b]hstack=2")
    r = sh("ffmpeg", "-y", "-v", "error", "-ss", "%.2f" % at, "-i", old,
           "-ss", "%.2f" % at, "-i", new, "-filter_complex", fc, "-frames:v", "1", dst)
    return dst if os.path.exists(dst) else (r.stderr or "")[-200:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", default=os.path.expanduser("~/shared/SHORTS"))
    ap.add_argument("--new", default=os.path.expanduser("~/shared/SHORTS-v3"))
    ap.add_argument("--out", default=os.path.expanduser("~/shared/SHORTS-v3/_compare"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    old, new = films(a.old), films(a.new)
    both = sorted(set(old) & set(new))
    only_old = sorted(set(old) - set(new))
    only_new = sorted(set(new) - set(old))

    rows = []
    for s in both:
        so, sn = luma_stats(old[s]), luma_stats(new[s])
        if not so or not sn:
            print("  could not measure: %s" % s)
            continue
        pair_image(old[s], new[s], os.path.join(a.out, "%s.jpg" % s))
        rows.append({"film": s, "old_yavg": so["yavg"], "new_yavg": sn["yavg"],
                     "old_dark": so["p_dark"], "new_dark": sn["p_dark"],
                     "delta": round(sn["yavg"] - so["yavg"], 1)})
        print("  %-22s %5.1f -> %5.1f  (%+.1f)" % (s, so["yavg"], sn["yavg"],
                                                   rows[-1]["delta"]))

    rows.sort(key=lambda r: -r["delta"])
    print("\n%-22s %8s %8s %8s %9s %9s" %
          ("film", "before", "after", "delta", "dark_pre", "dark_post"))
    for r in rows:
        print("%-22s %8.1f %8.1f %+8.1f %9.3f %9.3f" %
              (r["film"], r["old_yavg"], r["new_yavg"], r["delta"],
               r["old_dark"], r["new_dark"]))

    if rows:
        n = len(rows)
        print("\n%d films paired · mean luma %.1f -> %.1f (%+.1f) · films more than a "
              "quarter under luma 64: %d -> %d"
              % (n, sum(r["old_yavg"] for r in rows) / n,
                 sum(r["new_yavg"] for r in rows) / n,
                 sum(r["delta"] for r in rows) / n,
                 sum(1 for r in rows if r["old_dark"] > 0.25),
                 sum(1 for r in rows if r["new_dark"] > 0.25)))
        worse = [r["film"] for r in rows if r["delta"] < 0]
        if worse:
            print("DARKER THAN BEFORE, look at these: %s" % ", ".join(worse))
    # a rebuild that silently dropped a film is the failure this reports rather than hides
    if only_old:
        print("\nIN THE OLD SLATE ONLY (not rebuilt): %s" % ", ".join(only_old))
    if only_new:
        print("IN THE NEW SLATE ONLY: %s" % ", ".join(only_new))

    json.dump(rows, open(os.path.join(a.out, "compare.json"), "w"), indent=1)
    print("\nside-by-side frames: %s" % a.out)


if __name__ == "__main__":
    main()
