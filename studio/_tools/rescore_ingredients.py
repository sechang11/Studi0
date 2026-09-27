#!/usr/bin/env python3
"""studio/_tools/rescore_ingredients.py - the Ingredients arms scored against the RIGHT yardstick.

The first pass scored every last frame against the cast references - flat studio light on a
grey backdrop - and read 0.3-0.4 for people who are, by eye, unmistakably the cast. §98.5b
already found this: scoring against the neutral reference measures the lighting, not the face
(0.22-0.33 there against 0.75 head to head). So this scores the same frames against the heads
in anchor_010 - the same two people, lit by the same arena - and against each other across
arms, which is how identity was measured in §98.5.

It also drops the plate border band for the sheet-only arms: with no start frame the model
picks its own angle (it looked up at the glass roof), and a band that compares framings, not
rooms, cannot say whether the room is the same. What it reports instead is what a person can
check on the contact sheet: the roof, the lamps, the railings.

    ~/ComfyUI/venv/bin/python3 studio/_tools/rescore_ingredients.py
"""
import glob
import json
import os
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
TOOLS = os.path.join(STUDIO, "_tools")
sys.path.insert(0, TOOLS)
import newmodels_test as nm   # noqa: E402

from PIL import Image          # noqa: E402

FIGHT = os.path.join(STUDIO, "samples", "fight", "ash-court")
OUT = os.path.join(STUDIO, "samples", "newmodels-2026-09-27")


def anchor_heads(work):
    """Head crops of both people in anchor_010 (vesper left, koval right, by the shot's words)."""
    anchor = os.path.join(FIGHT, "anchor_010.png")
    boxes = nm.heads_in(anchor, work)
    im = Image.open(anchor).convert("RGB")
    w, h = im.size
    heads = {}
    for who, side in (("vesper", "left"), ("koval", "right")):
        b = boxes.get(side)
        if not b:
            continue
        x0, y0, x1, y1 = b
        pad = 0.4
        sidepx = max((x1 - x0) * w, (y1 - y0) * h) * (1 + pad)
        cx, cy = (x0 + x1) / 2 * w, (y0 + y1) / 2 * h
        l, t = max(0, cx - sidepx / 2), max(0, cy - sidepx / 2)
        p = os.path.join(work, "_anchorhead_%s.png" % who)
        im.crop((int(l), int(t), int(min(w, l + sidepx)), int(min(h, t + sidepx)))).save(p)
        heads[who] = p
    return heads


def main():
    work = os.path.join(OUT, "_rescore")
    os.makedirs(work, exist_ok=True)
    heads = anchor_heads(work)
    print("anchor heads:", sorted(heads))
    rep = {"yardstick": "heads in anchor_010 (arena-lit), identity.py medium bands: >=0.56 same, 0.46-0.56 uncertain",
           "runs": {}}
    for d in sorted(glob.glob(os.path.join(OUT, "ingredients*"))):
        if not os.path.isdir(d):
            continue
        run = os.path.basename(d)
        rows = []
        for last in sorted(glob.glob(os.path.join(d, "ing_*_last.png"))):
            tag = os.path.basename(last)[4:-9]          # A_s11
            sc = nm.score_pair(last, heads, work, "%s_%s" % (run, tag))
            rows.append({"take": tag, "vesper": sc["vesper"]["score"], "koval": sc["koval"]["score"],
                         "heads_found": sc["_heads_found"]})
            print("  %-22s %-8s vesper %s  koval %s" % (run, tag, sc["vesper"]["score"], sc["koval"]["score"]), flush=True)
        rep["runs"][run] = rows
    # per-arm means, so the table in the playbook can be one line per arm
    means = {}
    for run, rows in rep["runs"].items():
        for r in rows:
            arm = r["take"].split("_")[0]
            for who in ("vesper", "koval"):
                if r[who] is not None:
                    means.setdefault((run, arm, who), []).append(r[who])
    rep["means"] = {"%s %s %s" % k: round(sum(v) / len(v), 3) for k, v in means.items()}
    json.dump(rep, open(os.path.join(OUT, "ingredients_rescored.json"), "w"), indent=1)
    for k in sorted(rep["means"]):
        print("%-40s %.3f" % (k, rep["means"][k]))


if __name__ == "__main__":
    main()
