#!/usr/bin/env python3
"""Is anyone else in the frame?

The warm tier shipped one portrait with a second person in it, and it was found by eye on a
contact sheet - which is luck, not a process. The persona text had said "looking off to the
side at someone out of frame" and the engine drew the someone, exactly as the studio's own
doctrine says it will. The wording is fixed. This is the check that would have caught it
without the luck, and it will catch the next one.

There is no face detector on this box, but there is a segmenter, and headbox.py already
labels the matte into connected blobs biggest-first precisely so that "a second person or a
prop should not move the box". That labelling is the detector: one person alone in a frame
is one blob. A second figure standing apart is a second blob of comparable size.

It over-flags on purpose - a cut-out plant, a mug, an arm the matte separates at the elbow
all raise a hand - because the job here is to narrow seventy-two frames down to the handful
worth looking at, not to return a verdict. Anything flagged gets eyes on it.

    python3 studio/_tools/qc_faces.py --tier warm
    python3 studio/_tools/qc_faces.py --tier warm --sheet /tmp/flagged.jpg
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import headbox as HB

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FACES = os.path.join(ROOT, "studio", "foundry", "faces")

# a blob this much of the main figure, and this much of the frame, is worth a look
REL = 0.06
ABS = 0.004


def extras(path, work):
    """-> list of (area_fraction_of_frame, relative_to_main) for every blob after the first"""
    cut = os.path.join(work, os.path.basename(os.path.dirname(path)) + "_cut.png")
    if not os.path.exists(cut):
        sys.path.insert(0, HERE)
        import compose as C
        cut = C.cutout(path, cut, tag="qc")
    im = Image.open(cut).convert("RGBA")
    W, H = im.size
    sc = 240.0 / max(W, H)
    small = im if sc >= 1 else im.resize((max(1, int(W * sc)), max(1, int(H * sc))),
                                         Image.BILINEAR)
    a = np.asarray(small.split()[-1]) >= HB.MIN_ALPHA
    if not a.any():
        return None
    regs = HB._regions(a)
    if not regs:
        return None
    main = float(regs[0].sum())
    frame = float(a.size)
    out = []
    for r in regs[1:]:
        n = float(r.sum())
        if n / main >= REL and n / frame >= ABS:
            ys, xs = np.nonzero(r)
            out.append((n / frame, n / main, int(xs.min()), int(ys.min()),
                        int(xs.max()), int(ys.max()), small.size))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", default="warm")
    ap.add_argument("--sheet", default="")
    a = ap.parse_args()

    work = "/tmp/qc_faces"
    os.makedirs(work, exist_ok=True)
    # the first hundred predate tiers and carry no key; the page builder defaults them
    # to casting, so this must default them the same way or they are silently unchecked
    rows = [r for r in json.load(open(os.path.join(FACES, "faces.json")))
            if r.get("tier", "casting") == a.tier]
    flagged = []
    for r in rows:
        p = os.path.join(FACES, r["id"], "portrait.png")
        if not os.path.exists(p):
            print("  %-7s MISSING" % r["id"])
            continue
        ex = extras(p, work)
        if ex:
            big = max(e[1] for e in ex)
            print("  %-7s %-14s %-10s %d extra blob(s), largest %.0f%% of the figure"
                  % (r["id"], r["heritage"], r["persona"], len(ex), 100 * big))
            flagged.append((r, p, big))
    print("%d of %d flagged" % (len(flagged), len(rows)))

    if a.sheet and flagged:
        flagged.sort(key=lambda t: -t[2])
        cw, ch, head = 300, 375, 16
        cols = min(6, len(flagged))
        n = (len(flagged) + cols - 1) // cols
        S = Image.new("RGB", (cw * cols, (ch + head) * n), (20, 19, 18))
        from PIL import ImageDraw
        dr = ImageDraw.Draw(S)
        for i, (r, p, big) in enumerate(flagged):
            im = Image.open(p).convert("RGB")
            w, h = im.size
            s = min(cw / w, ch / h)
            im = im.resize((int(w * s), int(h * s)))
            x, y = (i % cols) * cw, (i // cols) * (ch + head)
            S.paste(im, (x + (cw - im.size[0]) // 2, y + head))
            dr.text((x + 3, y + 3), "%s %s %.0f%%" % (r["id"], r["persona"][:9], 100 * big),
                    fill=(240, 200, 160))
        S.save(a.sheet, quality=88)
        print("sheet -> %s" % a.sheet)


if __name__ == "__main__":
    main()
