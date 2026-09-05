"""The angle chain, scored link by link.

Two things can go wrong between asking for a low angle and getting one, and they need
separate numbers:

  1. asked -> the plate the studio made.  Arithmetic, and it either matches or it does not.
  2. that plate -> the take the engine returned.  The engine's business.

Scoring the take against the ORIGINAL plate's own pitch mixes the two and is wrong for a
third reason: a keystone REPLACES a picture's vertical vanishing point rather than composing
with it, so a plate that already reads +0.74 warped by +0.32 does not read +1.06.  Measured
in calibration and forgotten once already."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.expanduser("~/shared/comfy-studio/studio/_tools"))
import anglemeasure as A

ROOT = os.path.expanduser("~/shared/comfy-studio/studio")
film = json.load(open(os.path.join(ROOT, "films", "angles-and-mass", "film.json"), encoding="utf-8"))
SIGN = {"u": 1, "d": -1}
cache = {}


def pitch(p):
    if p not in cache:
        m = A.measure(p) if os.path.exists(p) else {}
        cache[p] = m.get("pitch") if m.get("confidence") not in (None, "none") else None
    return cache[p]


rows = []
for sid, sh in sorted(film["shots"].items()):
    t = next((x for x in sh.get("takes") or [] if x["id"] == sh.get("picked")), None) \
        or (sh.get("takes") or [None])[-1]
    if not t:
        continue
    src = sh.get("anchor_source") or {}
    plate = str(src.get("plate") or "")
    if not plate:
        a = str(sh.get("anchor") or "")
        plate = a[5:] if a.startswith("file:") else ""
    name = os.path.basename(plate)
    m = re.search(r"__angle([ud])(\d+)\.png$", name)
    asked = (SIGN[m.group(1)] * int(m.group(2)) / 100.0) if m else 0.0
    plate_pitch = pitch(plate) if plate else None
    am = t.get("angle_measured") or {}
    cm = t.get("cam_measured") or {}
    post = cm.get("post") or {}
    got = am.get("pitch") if am.get("confidence") not in (None, "none") else None
    rows.append({"shot": sid, "plate": name, "asked": asked, "plate_pitch": plate_pitch,
                 "take": got, "conf": am.get("confidence"),
                 "plate_err": (plate_pitch - asked) if (plate_pitch is not None and asked) else None,
                 "engine_drift": (got - plate_pitch) if (got is not None and plate_pitch is not None) else None,
                 "camera": cm.get("camera"), "move": post.get("move"), "ease": post.get("ease"),
                 "duration": t.get("duration"),
                 "qc": [q[:110] for q in t.get("qc") or []]})

f = lambda v: ("%+.2f" % v) if isinstance(v, float) else "  -  "
print("%-4s %-28s %6s %6s %6s %8s %9s  %s" % ("shot", "plate", "asked", "plate", "take", "arith", "engine", "camera"))
for r in rows:
    print("%-4s %-28s %6s %6s %6s %8s %9s  %s" % (
        r["shot"], r["plate"][:28], f(r["asked"]), f(r["plate_pitch"]), f(r["take"]),
        f(r["plate_err"]), f(r["engine_drift"]), (r["camera"] or "-")[:26]))

ang = [r for r in rows if r["asked"]]
pe = [abs(r["plate_err"]) for r in ang if r["plate_err"] is not None]
ed = [abs(r["engine_drift"]) for r in rows if r["engine_drift"] is not None]
import statistics
print()
print("shots that asked for an angle: %d" % len(ang))
if pe:
    print("  asked -> plate   : median error %.3f, worst %.3f" % (statistics.median(pe), max(pe)))
if ed:
    print("  plate -> take    : median drift %.3f, within 0.20 on %d of %d" % (
        statistics.median(ed), sum(1 for x in ed if x <= 0.20), len(ed)))
right = [r for r in ang if r["take"] is not None and r["take"] * r["asked"] > 0]
print("  the take reads the angle it was asked for, by sign: %d of %d" % (len(right), len(ang)))
json.dump(rows, open(os.path.join(ROOT, "angles_and_mass.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
lines = ["# Angles and mass, checked", "",
         "Every entry added on 2026-09-05, built once and measured. The angle is two separate",
         "questions: did the studio's arithmetic make the plate it was asked for, and did the engine",
         "keep it? A keystone replaces a picture's vanishing point rather than composing with it, so",
         "the plate is scored against what was asked and the take against the plate.", "",
         "| shot | plate | asked | plate measures | take measures | arithmetic | engine drift | camera measured | move | s |",
         "|---|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
        r["shot"], r["plate"][:26], f(r["asked"]), f(r["plate_pitch"]), f(r["take"]),
        f(r["plate_err"]), f(r["engine_drift"]), r["camera"] or "-", r["move"] or "-", r["duration"] or "-"))
open(os.path.join(ROOT, "angles_and_mass.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\nwritten: angles_and_mass.json and .md")
