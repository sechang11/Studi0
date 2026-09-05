"""Is a figure seen from below?  A ruler that needs no pose model.

The angle ruler reads the world's verticals and a person on a plain background has none, so
it says nothing useful here.  What a low camera does to a FIGURE is foreshorten it: the near
parts (feet, legs) grow and the far parts (head, shoulders) shrink, so the silhouette becomes
bottom-heavy.  That is measurable straight off the matte the pack already makes:

    weight = the fraction of the silhouette's area that lies in the lower half of the figure

against the pack's own base_fullbody, which is by construction at eye level.  A positive
delta means the camera dropped.  Calibrated below on the four packs that just had a low view
made, where one is right by eye and three are not."""
import os
import sys

sys.path.insert(0, os.path.expanduser("~/shared/comfy-studio/studio/_tools"))
import numpy as np
from PIL import Image

import compose as C

CHARS = os.path.expanduser("~/shared/comfy-studio/studio/foundry/characters")


def silhouette(path, work="/tmp/lvp"):
    os.makedirs(work, exist_ok=True)
    cut = C.cutout(path, os.path.join(work, os.path.basename(path)), tag="lv")
    im = Image.open(cut).convert("RGBA")
    a = np.asarray(im)[:, :, 3] > 24
    ys, xs = np.nonzero(a)
    if not len(ys):
        return None
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def weight(sil):
    """fraction of the silhouette's area in its lower half"""
    h = sil.shape[0]
    tot = sil.sum()
    if not tot:
        return None
    return float(sil[h // 2:].sum()) / float(tot)


def widths(sil, n=6):
    """the silhouette's width in n horizontal bands, normalised by its own mean"""
    h = sil.shape[0]
    out = []
    for i in range(n):
        band = sil[int(h * i / n):int(h * (i + 1) / n)]
        out.append(float(band.sum(axis=1).mean()) if band.size else 0.0)
    m = np.mean(out) or 1.0
    return [round(v / m, 3) for v in out]


if __name__ == "__main__":
    print("%-14s %-16s %6s  %s" % ("pack", "view", "weight", "width by band (head -> feet)"))
    for cid in (sys.argv[1:] or ["tomas-reyl", "ines-varga", "bai-liwen", "mara-okonjo"]):
        base = None
        for view in ("base_fullbody", "pres_low_full"):
            p = os.path.join(CHARS, cid, view + ".png")
            if not os.path.exists(p):
                continue
            s = silhouette(p)
            if s is None:
                print("%-14s %-16s   no silhouette" % (cid, view))
                continue
            w = weight(s)
            if view == "base_fullbody":
                base = w
            d = "" if base is None or view == "base_fullbody" else "   delta %+.3f" % (w - base)
            print("%-14s %-16s %6.3f  %s%s" % (cid, view, w, widths(s), d))
