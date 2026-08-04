#!/usr/bin/env python3
"""Old captions against new captions, in one frame, at one seed.

Two grids read one after the other is not a comparison - it is two memories. This puts the
uncaptioned LoRA and the recaptioned LoRA on adjacent rows of a single image so the only
difference between row 1 and row 2 is the caption file the weights were trained from.

  row 1   v1 uncaptioned, full tags        the state of the world before this change
  row 2   v2 recaptioned,  full tags       the change, in real usage
  row 3   v1 uncaptioned, name stripped
  row 4   v2 recaptioned,  name stripped   the change, with the danbooru name out of the way
"""
import argparse, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from costume_probe import cell, card, OUT, FRAME, PLACE, Q          # noqa: E402


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    # Labels default to the actual filenames. Hardcoded row labels once said
    # "v1 uncaptioned / v2 RECAPTIONED" while the run was in fact comparing v2 against v3,
    # which makes a grid that cannot be read back correctly a week later - or five minutes
    # later. A panel should say what it is, not what it usually is.
    ap.add_argument("--old-label")
    ap.add_argument("--new-label")
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--strength", type=float, default=0.5)
    ap.add_argument("--out", default="costume_ab.jpg")
    a = ap.parse_args()

    c = card()
    tags, base = c["tags"], c.get("base_tags", "")
    nameless = ", ".join(x for x in tags.split(", ")
                         if "terra branford" not in x and "final fantasy" not in x)
    costumes = c["costumes"]
    order = ["default", "armour", "court", "field"]

    def short(fn):
        return fn.replace("character_terra_", "").replace(".safetensors", "")
    ol = a.old_label or short(a.old)
    nl = a.new_label or short(a.new)
    rows = [
        ("%s  full tags" % ol, tags,     a.old),
        ("%s  full tags" % nl, tags,     a.new),
        ("%s  no name"   % ol, nameless, a.old),
        ("%s  no name"   % nl, nameless, a.new),
    ]

    os.makedirs(OUT, exist_ok=True)
    os.system("rm -rf /tmp/_abg && mkdir -p /tmp/_abg")
    i = 0
    for rlabel, tg, lo in rows:
        for cid in order:
            wear = costumes[cid]["wear_tags"][0]
            prompt = ", ".join(x for x in [tg, base, wear, FRAME, PLACE, Q] if x)
            print("  %-28s %-8s" % (rlabel, cid), flush=True)
            p = cell("ab_%d" % i, prompt, lo, a.strength, a.seed)
            if not p:
                print("     FAILED")
                i += 1
                continue
            label = "%s | %s" % (rlabel, costumes[cid]["name"])
            sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
               "scale=440:-1,drawtext=text='%s':fontcolor=yellow:fontsize=18:x=6:y=6:"
               "box=1:boxcolor=black@0.85:boxborderw=5" % label.replace(":", "\\:"),
               "/tmp/_abg/%02d.png" % i)
            i += 1

    dst = os.path.join(OUT, a.out)
    sh("ffmpeg", "-y", "-v", "error", "-pattern_type", "glob", "-i", "/tmp/_abg/*.png",
       "-filter_complex", "tile=4x%d:margin=6:padding=6:color=0x111111" % len(rows),
       "-frames:v", "1", "-q:v", "3", dst)
    print("\n%s" % dst)
    print("Row 1 against row 2 is the whole question. Has the gold dress gone?")


if __name__ == "__main__":
    main()
