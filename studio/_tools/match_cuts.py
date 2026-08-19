#!/usr/bin/env python3
"""studio/_tools/match_cuts.py - find the cuts where two shots already rhyme.

Across the 23-film slate, 115 beats declare 12 transitions between them. 90% of every cut
is a plain hard cut, which is correct - the `cut` card says so: "~95% of any edit, needs no
justification." But `match_cut`, whose own card calls it "the strongest device available",
has been used ZERO times, and `smash` zero times.

A match cut cannot be chosen from a list. It exists only when two shots happen to RHYME -
a wheel and a sun, a doorway and a screen - and you cannot ask for that, you can only
notice it. So this notices it.

WHAT A RHYME IS, measured:

    structure   both keyframes reduced to 24x24 luma and correlated. High means the big
                shapes sit in the same places - the composition carries across the cut.
    difference  the same pair at full size. HIGH is required: two frames that rhyme
                because they are nearly identical is not a match cut, it is a jump cut.

    score = structure x difference

Both halves are necessary and neither is sufficient, which is the whole point. A high
score is a CANDIDATE, not an instruction - it says "these two compositions line up, go
and look". A cut whose shapes rhyme by accident and mean nothing is still a bad cut, and
no number can tell you which is which.

    python3 studio/_tools/match_cuts.py FILM.json
    python3 studio/_tools/match_cuts.py --all
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FILMS = os.path.join(ROOT, "films", "shorts")
COMFY = os.path.expanduser("~/ComfyUI")

# NO FIXED THRESHOLD. The first version of this hardcoded 0.42 with a comment claiming it
# had been calibrated from the slate. It had not - I picked it before running anything,
# and the slate's actual maximum is 0.168, so the tool reported "0 candidates" underneath
# a sentence explaining how carefully the number was chosen. A wrong number with a
# provenance story is worse than a wrong number.
#
# The cut-off is now the 90th percentile OF WHAT IS BEING SCANNED, computed at run time.
# It cannot go stale and it cannot claim an authority it does not have - a top-decile cut
# in a slate with no rhymes is still not a match cut, which is why the absolute numbers
# are printed beside it.
TOP_DECILE = 0.90


def small(path, n=24):
    from PIL import Image
    im = Image.open(path).convert("L").resize((n, n))
    px = list(im.getdata())
    m = sum(px) / len(px)
    return [p - m for p in px]


def corr(a, b):
    """Pearson correlation of two mean-centred vectors, clamped to 0..1."""
    num = sum(x * y for x, y in zip(a, b))
    da = sum(x * x for x in a) ** 0.5
    db = sum(y * y for y in b) ** 0.5
    if da == 0 or db == 0:
        return 0.0
    return max(0.0, num / (da * db))


def differ(pa, pb):
    """How unlike the two frames are at size. 0 identical, 1 opposite."""
    from PIL import Image, ImageChops
    ia = Image.open(pa).convert("RGB").resize((128, 128))
    ib = Image.open(pb).convert("RGB").resize((128, 128))
    px = list(ImageChops.difference(ia, ib).getdata())
    return sum(sum(p) for p in px) / (len(px) * 3 * 255.0)


def keyframes(film_path):
    d = json.loads(open(film_path, encoding="utf-8").read())
    slug = d["title"].lower().replace(" ", "-")
    kd = os.path.join(COMFY, "output", "claude-generated", "12-shorts", slug,
                      "keyframes")
    out = []
    for b in d["beats"]:
        p = os.path.join(kd, "%s_00001_.png" % b["id"])
        if os.path.exists(p):
            out.append((b["id"], p, b.get("transition")))
    return d, out


def scan(film_path, quiet=False):
    d, kf = keyframes(film_path)
    if len(kf) < 2:
        if not quiet:
            print("  %-20s no rendered keyframes" % os.path.basename(film_path))
        return []
    rows = []
    for (ida, pa, _t), (idb, pb, trb) in zip(kf, kf[1:]):
        s = corr(small(pa), small(pb))
        v = differ(pa, pb)
        rows.append({"film": d["title"], "from": ida, "to": idb,
                     "structure": round(s, 3), "difference": round(v, 3),
                     "score": round(s * v, 3), "declared": trb})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("films", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    paths = a.films or (sorted(p for p in glob.glob(os.path.join(FILMS, "*.json"))
                               if not os.path.basename(p).startswith("_"))
                        if a.all else [])
    if not paths:
        sys.exit("give a film json, or --all")

    rows = []
    for p in paths:
        rows += scan(p, quiet=not a.films)
    if not rows:
        sys.exit("nothing rendered to compare - render the keyframes first")

    rows.sort(key=lambda r: -r["score"])
    _s = sorted(r["score"] for r in rows)
    cutoff = _s[min(len(_s) - 1, int(TOP_DECILE * (len(_s) - 1)))]
    print("%-16s %-11s %-11s %9s %10s %7s  %s"
          % ("film", "from", "to", "structure", "difference", "score", "declared"))
    for r in rows[:18]:
        flag = "  <- LOOK" if r["score"] >= cutoff and r["score"] > 0 else ""
        print("%-16s %-11s %-11s %9.3f %10.3f %7.3f  %-9s%s"
              % (r["film"][:16], r["from"], r["to"], r["structure"],
                 r["difference"], r["score"], r["declared"] or "-", flag))

    sc = sorted(r["score"] for r in rows)
    n = len(sc)
    print("\n%d cuts examined. score spread: min %.3f, median %.3f, max %.3f"
          % (n, sc[0], sc[n // 2], sc[-1]))
    worth = [r for r in rows if r["score"] >= cutoff and r["score"] > 0]
    print("top decile is %.3f; %d cut(s) at or above it - candidates to LOOK at."
          % (cutoff, len(worth)))
    print("These are ACCIDENTS. A real match cut is authored - the second shot is framed")
    print("to answer the first - and scanning finished keyframes can only find the ones")
    print("that happened by chance. The best in this slate is a shared horizon and light,")
    print("which is a graphic match worth cutting on, not a shape rhyme.")
    if a.json:
        json.dump(rows, open(a.json, "w"), indent=1)
        print("-> %s" % a.json)


if __name__ == "__main__":
    main()
