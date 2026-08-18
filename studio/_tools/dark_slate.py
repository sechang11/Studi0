#!/usr/bin/env python3
"""Was the slate actually dark, or did it just feel dark?

    "the shorts you made aren't good enough. they all seem to have a darkness to them"

That was said about films this project delivered and passed through its own QC, and until
tonight nothing here measured brightness at all - so the complaint could not be checked,
only agreed with. clipmetrics now reports luma, so the twenty-odd delivered pieces can be
asked directly.

ffmpeg's signalstats gives the same Y average over EVERY frame rather than a 16-frame
sample, which is the right instrument for a whole film: a piece that is bright throughout
and black for its last two seconds should not read as mid-grey.

    YAVG    mean luma, 0-255, over every frame of the delivered file
    YLOW    the 10th percentile frame - how dark the dark end actually gets
    p_dark  share of frames whose mean luma is under 64 (a quarter scale). This is the
            one that matches the complaint: "a darkness to them" is not about the
            average, it is about how much of the running time sits in the mud.

No threshold is asserted here. The point is to SORT the slate and look at the ends of it.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/SHORTS")


def frame_lumas(path):
    """Mean luma per frame, 0-255, straight from signalstats."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-f", "lavfi",
         "-i", "movie=%s,signalstats" % path.replace("\\", "/").replace(":", "\\:"),
         "-show_entries", "frame_tags=lavfi.signalstats.YAVG",
         "-of", "default=nw=1:nk=1"],
        capture_output=True, text=True)
    out = []
    for line in (r.stdout or "").splitlines():
        try:
            out.append(float(line.strip()))
        except ValueError:
            pass
    return out


def main():
    files = []
    for dirpath, _dn, fn in os.walk(ROOT):
        for f in sorted(fn):
            if f.endswith(".mp4"):
                files.append(os.path.join(dirpath, f))
    if not files:
        sys.exit("no films under %s" % ROOT)

    rows = []
    for p in files:
        ys = frame_lumas(p)
        if not ys:
            print("  no frames read: %s" % os.path.basename(p))
            continue
        ys_sorted = sorted(ys)
        rows.append({
            "film": os.path.relpath(p, ROOT),
            "frames": len(ys),
            "yavg": round(sum(ys) / len(ys), 1),
            "ylow": round(ys_sorted[max(0, len(ys) // 10)], 1),
            "p_dark": round(sum(1 for y in ys if y < 64) / len(ys), 3),
        })

    rows.sort(key=lambda r: r["yavg"])
    print("%-44s %7s %7s %7s %7s" % ("film", "frames", "YAVG", "YLOW", "p_dark"))
    for r in rows:
        print("%-44s %7d %7.1f %7.1f %7.3f"
              % (r["film"][:44], r["frames"], r["yavg"], r["ylow"], r["p_dark"]))

    n = len(rows)
    print("\n%d films  ·  median YAVG %.1f  ·  %d with more than a quarter of their "
          "running time under luma 64"
          % (n, sorted(r["yavg"] for r in rows)[n // 2],
             sum(1 for r in rows if r["p_dark"] > 0.25)))
    json.dump(rows, open(os.path.join(ROOT, "brightness.json"), "w"), indent=1)
    print("-> %s/brightness.json" % ROOT)


if __name__ == "__main__":
    main()
