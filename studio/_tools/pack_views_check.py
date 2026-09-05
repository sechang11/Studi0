#!/usr/bin/env python3
"""Which pack views are drawn wrong enough to hurt a composite?

Every composite scales a cutout so its total height is what a 1.7 m person subtends where
it stands, and that only holds together if all the views of one person share proportions.
Measured across the packs on this box they do not: the well-behaved ones vary 13-33% in
head size between views, and four have a view where the head probe finds almost nothing at
all - a hat brim, a raised arm, a failed cutout, or a figure that is not standing.

Those broken views are in active use.  This names them, so they can be re-rendered.

    python3 pack_views_check.py                 # every pack
    python3 pack_views_check.py tomas-reyl      # one
"""
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compose as C

CHARS = C.CHARS
SPREAD_OK = 1.35


def check(cid, force=True):
    ref = C.head_reference(cid, force=force)
    vals = ref.get("views") or {}
    if not ref.get("reference"):
        return {"pack": cid, "verdict": "not enough views to judge", "views": vals}
    r = ref["reference"]
    bad = sorted(k for k, v in vals.items() if v > r * SPREAD_OK or v < r / SPREAD_OK)
    spread = (max(vals.values()) / min(vals.values())) if vals else None
    return {"pack": cid, "reference": r, "views": vals, "suspect": bad,
            "spread": round(spread, 2) if spread else None,
            "verdict": ("re-render %s" % ", ".join(bad)) if bad else "consistent"}


if __name__ == "__main__":
    packs = sys.argv[1:] or sorted(d for d in os.listdir(CHARS)
                                   if os.path.isdir(os.path.join(CHARS, d)))
    rows = []
    import time as _t
    for cid in packs:
        # paced: a run of these killed ComfyUI once by asking the segmenter for a hundred
        # cutouts back to back while another session held the GPU.  The process is not
        # killed with an exception, the socket simply closes, so the only defence is not
        # to ask that fast.
        _t.sleep(2.0)
        try:
            r = check(cid)
        except Exception as e:
            r = {"pack": cid, "verdict": "check failed: %s" % str(e)[:60]}
        rows.append(r)
        print("%-20s %-9s %s" % (cid, ("%.2fx" % r["spread"]) if r.get("spread") else "-", r["verdict"]))
    out = os.path.join(os.path.dirname(HERE), "pack_views_check.json")
    json.dump(rows, open(out, "w", encoding="utf-8"), indent=1)
    bad = [r for r in rows if r.get("suspect")]
    print()
    print("%d packs | %d with a view to re-render | %d consistent"
          % (len(rows), len(bad), sum(1 for r in rows if r.get("verdict") == "consistent")))
    print("written:", out)
