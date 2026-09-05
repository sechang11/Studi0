"""Keep a pack's low view only if it is BOTH whole and actually low.

A view that is whole but shot at eye level is worse than no view at all: the builder would
use it for a low angle and the picture would quietly disagree with the promise.  So the
gate is both rulers, and a pack that fails loses the file and the entry.

Written after the measurement that produced it: the pack renderer's far-framing retry buys
wholeness by moving the camera back to eye level, and extending the picture downward buys
wholeness by adding legs - which is the right repair but dilutes the foreshortening the
second ruler reads.  Both are honest; neither is a low view unless it passes here.
"""
import json
import os
import sys

sys.path.insert(0, os.path.expanduser("~/shared/comfy-studio/studio/_tools"))
sys.path.insert(0, "/tmp")
import importlib.util

import lowview_probe as LV

TOOLS = os.path.expanduser("~/shared/comfy-studio/studio/_tools")
spec = importlib.util.spec_from_file_location("fr_v", os.path.join(TOOLS, "foundry_routes.py"))
FR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(FR)
FY = FR.FY
CHARS = os.path.expanduser("~/shared/comfy-studio/studio/foundry/characters")
KEY = "pres_low_full"
MIN_DELTA = 0.04
MIN_HEAD = 0.74          # the view's head may be at most a third bigger than the turnaround's

rows = []
for cid in (sys.argv[1:] or sorted(os.listdir(CHARS))):
    d = os.path.join(CHARS, cid)
    p = os.path.join(d, KEY + ".png")
    if not os.path.isdir(d) or not os.path.exists(p):
        continue
    base = os.path.join(d, "base_fullbody.png")
    ok, detail = FR._fullbody_ok(p)
    wb = LV.weight(LV.silhouette(base)) if os.path.exists(base) else None
    wl = LV.weight(LV.silhouette(p))
    delta = (wl - wb) if (wb is not None and wl is not None) else None
    import compose as C
    hf, hnote = C.head_scale(cid, KEY, "turn_front")
    keep = bool(ok) and delta is not None and delta >= MIN_DELTA and hf >= MIN_HEAD
    rows.append({"pack": cid, "whole": bool(ok), "delta": round(delta, 3) if delta is not None else None,
                 "head": round(hf, 3), "kept": keep})
    print("%-14s whole=%-5s bottom-heavy %+.3f head %.2f -> %s"
          % (cid, ok, delta or 0, hf, "KEPT" if keep else "removed"))
    if not keep:
        os.remove(p)
        a = FY.load_asset("character", cid)
        if (a.get("images") or {}).pop(KEY, None) is not None:
            json.dump(a, open(os.path.join(d, "asset.json"), "w", encoding="utf-8"),
                      indent=1, ensure_ascii=False)
json.dump(rows, open(os.path.expanduser("~/shared/comfy-studio/studio/low_views.json"), "w"), indent=1)
print("kept %d of %d" % (sum(1 for r in rows if r["kept"]), len(rows)))
