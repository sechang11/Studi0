"""A quarter of ordinary shots lose the face.  Which ones, and is there a rule?

The face clock says how long a face lasts by what the person is doing.  It does not say what
makes one still shot keep its face for five seconds and another lose it at two.  The obvious
suspects are all measurable from what the takes already carry: how big the head is in the
frame (the framing), how much the engine moved the camera, and how well the place held.
"""
import json
import os
import statistics
import sys
from collections import defaultdict

ROOT = os.path.expanduser("~/shared/comfy-studio/studio")
FILMS = os.path.join(ROOT, "films")

rows = []
for fid in sorted(os.listdir(FILMS)):
    fp = os.path.join(FILMS, fid, "film.json")
    if not os.path.exists(fp):
        continue
    try:
        film = json.load(open(fp, encoding="utf-8"))
    except Exception:
        continue
    for sid, sh in (film.get("shots") or {}).items():
        src = sh.get("anchor_source") or {}
        beats = sh.get("beats") or [{}]
        for t in sh.get("takes") or []:
            ident = t.get("identity") or {}
            hc = ident.get("hold_curve") or {}
            if not hc or not hc.get("duration"):
                continue
            cam = t.get("cam_measured") or {}
            rows.append({
                "film": fid, "shot": sid, "take": t["id"],
                "framing": (src.get("framing") or "?").lower(),
                "motion": (beats[0].get("motion") or "still").lower() or "still",
                "zoom": float(cam.get("zoom", 1.0) or 1.0),
                "pan": abs(float(cam.get("pan", 0.0) or 0.0)),
                "tilt": abs(float(cam.get("tilt", 0.0) or 0.0)),
                "place_hold": ident.get("place_hold"),
                "start": ident.get("start"),
                "held": bool(hc.get("holds")),
                "hold": hc.get("holds_until"),
                "dur": hc["duration"],
            })

print("takes with a clock:", len(rows))


def rate(sel, label):
    if not sel:
        return
    held = sum(1 for r in sel if r["held"])
    holds = [r["hold"] for r in sel if r["hold"] is not None]
    print("  %-26s n=%3d  held %3d (%3.0f%%)  median hold %s" % (
        label, len(sel), held, 100.0 * held / len(sel),
        ("%.2f" % statistics.median(holds)) if holds else "-"))


print("\nBY FRAMING")
by = defaultdict(list)
for r in rows:
    by[r["framing"]].append(r)
for k in sorted(by, key=lambda k: -len(by[k])):
    rate(by[k], k)

print("\nBY HOW FAR THE ENGINE MOVED THE CAMERA (measured zoom)")
bands = [("still, under 1.05", lambda r: r["zoom"] < 1.05),
         ("1.05 to 1.20", lambda r: 1.05 <= r["zoom"] < 1.20),
         ("1.20 to 1.50", lambda r: 1.20 <= r["zoom"] < 1.50),
         ("past 1.50", lambda r: r["zoom"] >= 1.50)]
for label, f in bands:
    rate([r for r in rows if f(r)], label)

print("\nBY HOW WELL THE PLACE HELD")
for label, f in (("place held, 0.85+", lambda r: (r["place_hold"] or 0) >= 0.85),
                 ("drifted, 0.70-0.85", lambda r: 0.70 <= (r["place_hold"] or 0) < 0.85),
                 ("changed, under 0.70", lambda r: r["place_hold"] is not None and r["place_hold"] < 0.70)):
    rate([r for r in rows if f(r)], label)

print("\nBY HOW GOOD THE FACE WAS AT THE START")
for label, f in (("start 0.65+", lambda r: (r["start"] or 0) >= 0.65),
                 ("0.55 to 0.65", lambda r: 0.55 <= (r["start"] or 0) < 0.65),
                 ("under 0.55", lambda r: (r["start"] or 0) < 0.55 and r["start"] is not None)):
    rate([r for r in rows if f(r)], label)

json.dump(rows, open("/tmp/who_loses.json", "w"), indent=1)
