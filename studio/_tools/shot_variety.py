#!/usr/bin/env python3
"""studio/_tools/shot_variety.py - how many of a film's "shots" are actually new pictures.

The second half of the complaint that opened this work:

    "they ... use the same shots in non fluid repetitive clips"

short.py generates ONE video clip per beat and then expand_template slices it into
micro-shots with different crops and moves. ATLAS logged 9 shots and held 4 generations -
over half its cuts were re-framings of footage already seen. The film reports the higher
number, so the log has been agreeing with itself about variety it does not have.

This measures the real ratio from the work directory, which is where the truth is:

    clips     source generations - one per beat, what the video engine actually made
    shots     cuts in the delivered edit
    reuse     shots / clips. 1.0 means every cut is a new picture. 3.0 means two out of
              three cuts are re-crops of something already on screen.
    seconds   how many delivered seconds each generation has to carry. This is the number
              that decides whether reuse READS as repetition - the same 4 clips over 12
              seconds is a montage, over 40 seconds it is a loop.

NO THRESHOLD IS ASSERTED. A re-crop is a legitimate edit; cutting from wide to detail off
one plate is what an editor does with one setup. The point is that the number should be
visible when a film is judged, instead of a shot count that flatters it.

    python3 studio/_tools/shot_variety.py
    python3 studio/_tools/shot_variety.py --work ~/ComfyUI/output/claude-generated/12-shorts
"""
import argparse
import json
import os
import re
import subprocess


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def duration(path):
    r = sh("ffprobe", "-v", "error", "-select_streams", "v:0",
           "-show_entries", "format=duration", "-of", "csv=p=0", path)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


# The cutter writes one file per delivered slice as NNNN_<beat-id>_<slice>.mp4.
# Matching on a "cut_" prefix found nothing and the fallback then reported every film in
# the library at reuse 1.00 - the exact answer this tool exists to test.
SLICE_RE = re.compile(r"^\d{4}_.+_\d+\.mp4$")


def count_cuts(film_dir):
    """Delivered cuts, counted from the cutter's numbered slice files.

    Returns None - not 0 - when the work directory cannot answer, so the caller reports
    the film as unmeasurable instead of substituting a ratio nobody measured.
    """
    work = os.path.join(film_dir, "_work")
    if not os.path.isdir(work):
        return None
    n = len([f for f in os.listdir(work) if SLICE_RE.match(f)])
    return n or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=os.path.expanduser(
        "~/ComfyUI/output/claude-generated/12-shorts"))
    a = ap.parse_args()
    if not os.path.isdir(a.work):
        raise SystemExit("no work dir: %s" % a.work)

    rows, unmeasured = [], []
    for slug in sorted(os.listdir(a.work)):
        d = os.path.join(a.work, slug)
        if not os.path.isdir(d):
            continue
        clips_dir = os.path.join(d, "clips")
        clips = ([f for f in os.listdir(clips_dir) if f.endswith(".mp4")]
                 if os.path.isdir(clips_dir) else [])
        final = os.path.join(d, slug + ".mp4")
        if not clips or not os.path.exists(final):
            continue
        cuts = count_cuts(d)
        dur = duration(final)
        if cuts is None:
            unmeasured.append(slug)
            continue
        rows.append({"film": slug, "clips": len(clips), "shots": cuts,
                     "secs": round(dur, 1),
                     "reuse": round(cuts / max(1, len(clips)), 2),
                     "secs_per_clip": round(dur / max(1, len(clips)), 1)})

    if not rows:
        raise SystemExit("no rendered films found under %s" % a.work)

    rows.sort(key=lambda r: -r["secs_per_clip"])
    print("%-22s %6s %6s %7s %8s %10s" %
          ("film", "clips", "shots", "reuse", "secs", "s/clip"))
    for r in rows:
        flag = "  <- each generation carries a long time on screen" \
            if r["secs_per_clip"] >= 4.0 else ""
        print("%-22s %6d %6d %7.2f %8.1f %10.1f%s"
              % (r["film"], r["clips"], r["shots"], r["reuse"], r["secs"],
                 r["secs_per_clip"], flag))

    n = len(rows)
    print("\n%d films · %.1f generations per film · reuse %.2f · %.1f delivered seconds "
          "per generation"
          % (n, sum(r["clips"] for r in rows) / n, sum(r["reuse"] for r in rows) / n,
             sum(r["secs_per_clip"] for r in rows) / n))
    print("reuse 1.00 = every cut is a new picture. Above that, the difference is "
          "re-crops of footage already on screen.")
    if unmeasured:
        print("\nNO SLICE FILES, not measured (%d): %s"
              % (len(unmeasured), ", ".join(unmeasured[:12])
                 + (" ..." if len(unmeasured) > 12 else "")))
    out = os.path.join(a.work, "_variety.json")
    json.dump(rows, open(out, "w"), indent=1)
    print("-> %s" % out)


if __name__ == "__main__":
    main()
