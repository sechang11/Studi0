#!/usr/bin/env python3
"""Where is the head, actually?

The identity ruler has been guessing.  It takes the compose geometry - where the figure was
told to stand, how tall a 1.7 m person is there - and derives a head box from it, then carries
that box through the measured camera to find the head at the end.  That is exact for an
upright figure at eye level in a shot where only the camera moved, and it has been wrong
every time the person did something: a crouch drops the head a third of a frame and the box
reads the chest, a low view foreshortens and the box reads the shoulders, a walk toward the
camera changes the head's size faster than the camera curve says.

There is no face detector on this box.  There is a segmenter, and it is very good: BiRefNet
cuts a person out of a picture cleanly, which is how every composite is made.  A silhouette
does not say where a FACE is, but it says exactly where the top of a person is, and that is
enough - a head is the top of a standing body whatever the body is doing.

    from headbox import head_box
    box = head_box("frame.png")     # -> [x0, y0, x1, y1] fractions, or None

HOW.  Matte the picture, keep the largest connected region (a second person or a prop should
not move the box), and read the head off its top: the head's height is a fixed fraction of
the figure's, and its width is measured from the silhouette rather than assumed, so a hat, a
hood or hair are inside it.  A figure flush against the top of the frame has its head cut off
and gets None rather than a guess.
"""
import os
import sys

import numpy as np
from PIL import Image

HEAD_FRACTION = 0.20      # of the figure's height, from its top
MIN_ALPHA = 96
MIN_FIGURE = 0.04         # a "figure" must be this tall a fraction of the frame


def _regions(mask):
    """every 4-connected blob as a boolean mask, biggest first (two-pass label, no scipy)"""
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    nxt = 1
    parent = {0: 0}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for y in range(h):
        row = mask[y]
        up = lab[y - 1] if y else None
        left = 0
        for x in range(w):
            if not row[x]:
                left = 0
                continue
            a = up[x] if up is not None else 0
            if left and a:
                lab[y, x] = min(left, a)
                union(left, a)
            elif left:
                lab[y, x] = left
            elif a:
                lab[y, x] = a
            else:
                lab[y, x] = nxt
                parent[nxt] = nxt
                nxt += 1
            left = lab[y, x]
    if nxt == 1:
        return None
    flat = np.vectorize(lambda v: find(v) if v else 0)(lab)
    ids, counts = np.unique(flat[flat > 0], return_counts=True)
    if not len(ids):
        return []
    order = np.argsort(-counts)
    return [flat == ids[i] for i in order[:6]]


def _largest_region(mask):
    r = _regions(mask)
    return r[0] if r else None


def figure_box(src, work=None, near=None):
    """the whole figure's bounding box, in fractions -> [x0, y0, x1, y1] or None"""
    b = head_box(src, work=work, near=near, _want="figure")
    return b


def _head_of(reg, sh, sw, head_fraction, want="head"):
    ys, xs = np.nonzero(reg)
    if not len(ys):
        return None
    y0, y1 = int(ys.min()), int(ys.max())
    if (y1 - y0 + 1) < MIN_FIGURE * sh or y0 <= 1:
        return None
    if want == "figure":
        fxs = np.nonzero(reg.any(axis=0))[0]
        if not len(fxs):
            return None
        return [int(fxs.min()) / float(sw), y0 / float(sh),
                (int(fxs.max()) + 1) / float(sw), (y1 + 1) / float(sh)]
    hh = max(2, int(round((y1 - y0 + 1) * head_fraction)))
    band = reg[y0:y0 + hh]
    bxs = np.nonzero(band.any(axis=0))[0]
    if not len(bxs):
        return None
    x0, x1 = int(bxs.min()), int(bxs.max())
    pad_x = max(1, int(0.12 * (x1 - x0 + 1)))
    pad_y = max(1, int(0.10 * hh))
    return [max(0, x0 - pad_x) / float(sw), max(0, y0 - pad_y) / float(sh),
            min(sw - 1, x1 + pad_x + 1) / float(sw), min(sh - 1, y0 + hh + pad_y + 1) / float(sh)]


def head_box(src, head_fraction=HEAD_FRACTION, work=None, quiet=True, near=None, _want="head"):
    """-> [x0, y0, x1, y1] in fractions of the picture, or None.

    `src` may be a path to an RGBA cutout (used directly) or to an ordinary picture, which
    is matted first through the compositor's own segmenter.

    `near` is an (x, y) hint in fractions - normally the middle of where the compose geometry
    thought the subject's head would be.  With two people in a frame the largest silhouette is
    not necessarily the one being asked about, and an over-the-shoulder foreground is larger
    than the subject by design."""
    path = src
    if not str(src).lower().endswith(".png") or Image.open(src).mode != "RGBA":
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import compose as C
        work = work or "/tmp/headbox"
        os.makedirs(work, exist_ok=True)
        path = C.cutout(src, os.path.join(work, os.path.basename(str(src))[:-4] + "_cut.png"),
                        tag="hb")
    im = Image.open(path).convert("RGBA")
    W, H = im.size
    # work small: the head's position does not need full resolution and the labelling is slow
    sc = 240.0 / max(W, H)
    small = im if sc >= 1 else im.resize((max(1, int(W * sc)), max(1, int(H * sc))), Image.BILINEAR)
    a = np.asarray(small.split()[-1]) >= MIN_ALPHA
    if not a.any():
        return None
    regs = _regions(a)
    if not regs:
        return None
    sh, sw = a.shape
    boxes = [b for b in (_head_of(r, sh, sw, head_fraction, _want) for r in regs) if b]
    if not boxes:
        return None
    if near is None:
        return boxes[0]
    hx, hy = float(near[0]), float(near[1])
    return min(boxes, key=lambda b: ((b[0] + b[2]) / 2 - hx) ** 2 + ((b[1] + b[3]) / 2 - hy) ** 2)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        b = head_box(p)
        print("%-58s %s" % (os.path.basename(p)[:58],
                            ("[%.3f %.3f %.3f %.3f]" % tuple(b)) if b else "no head found"))
