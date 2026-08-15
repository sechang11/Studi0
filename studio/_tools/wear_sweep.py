#!/usr/bin/env python3
"""studio/_tools/wear_sweep.py - task 50's measurement: does the wear ladder reach the
pixels above rung 1, and at what LoRA strength?

    python3 studio/_tools/wear_sweep.py --character TERRA [--seeds 2] [--strengths 0.5 0.7]

Grid: rung 0..4 x LoRA strength x seed, ONE place and framing, the anime engine (where
the film measured the failure). Every other variable held. Output: a contact sheet
samples/wear_sweep/<CHAR>.jpg (rows = strength x seed, columns = rung 0..4) with the
rung's wear text printed under it - and each cell's recipe beside its frame so the
library can find them.

Two instruments run before a human looks: frame_check's VLM description per cell
(does it mention torn/rag/dirt/blood/bandage at rungs 3-4 and clean at rung 0?), and
mean pairwise MAD between rungs at the same seed (a ladder that renders identical
frames at every rung is inert). The verdict is written onto the character card as
MEASURED with the numbers; whether the ladder READS is the human's call from the sheet.
"""
import argparse
import json
import os
import re
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
sys.path.insert(0, STUDIO)
sys.path.insert(0, TOOLS)
import cards                                       # noqa: E402

DAMAGE = ("torn", "rag", "ragged", "tattered", "dirt", "dirty", "dust", "dusty", "mud",
          "blood", "bandage", "wrapped", "scuff", "worn", "damaged", "ruined", "split",
          "frayed", "stain", "smudge", "bruise", "wound", "scratched", "battered")
CLEAN = ("clean", "pristine", "neat", "immaculate", "unmarked", "crisp")


def sh(*a, **k):
    return subprocess.run(a, capture_output=True, text=True, **k)


def main():
    ap = argparse.ArgumentParser(description="Wear ladder x LoRA strength x seed sweep.")
    ap.add_argument("--character", default="TERRA")
    ap.add_argument("--place", default="desert_dunes")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--strengths", type=float, nargs="+", default=[0.5, 0.7])
    ap.add_argument("--engine", default="anime")
    a = ap.parse_args()
    out = os.path.join(STUDIO, "samples", "wear_sweep")
    os.makedirs(out, exist_ok=True)
    card = cards.load("characters").get(a.character)
    if not card:
        print("no such character", file=sys.stderr)
        return 2
    ladder = card.get("wear_tags") or []
    cells = {}
    for si in range(a.seeds):
        seed = 5000 + si * 101
        for st in a.strengths:
            for rung in range(min(5, len(ladder))):
                r = sh(sys.executable, os.path.join(TOOLS, "roll.py"), "image",
                       "--character", a.character, "--engine", a.engine,
                       "--place", a.place, "--wear", str(rung), "--seed", str(seed))
                job = (r.stdout or "").strip()
                if not job:
                    print("roll refused rung %d: %s" % (rung, (r.stderr or "")[-160:]))
                    continue
                j = json.loads(job)
                j["character_lora_strength"] = st
                j["seed"] = seed                    # same noise across rungs
                j["id"] = "wear_%s_s%d_l%s_r%d" % (a.character.lower(), seed,
                                                   str(st).replace(".", ""), rung)
                r2 = sh(sys.executable, os.path.join(TOOLS, "render_job.py"),
                        "--out", out, input=json.dumps(j))
                res = (r2.stdout or "").strip().splitlines()
                v = json.loads(res[-1]) if res else {}
                if v.get("ok") and v.get("file"):
                    cells[(seed, st, rung)] = v["file"]
                    print("seed %d lora %.1f rung %d ok" % (seed, st, rung))
                else:
                    print("seed %d lora %.1f rung %d FAILED %s"
                          % (seed, st, rung, (v.get("error") or v.get("why") or "")[:80]))
    if not cells:
        return 1

    # instrument 1: VLM description per cell
    try:
        import frame_check as fc
        vlm = {k: fc.describe(p) for k, p in cells.items()}
    except Exception as e:                                             # noqa: BLE001
        print("VLM unavailable: %s" % e)
        vlm = {}
    # instrument 2: MAD between adjacent rungs at the same seed/strength
    from PIL import Image, ImageChops
    def mad(pa, pb):
        ia, ib = Image.open(pa).convert("RGB"), Image.open(pb).convert("RGB")
        ib = ib.resize(ia.size)
        d = ImageChops.difference(ia, ib).convert("L")
        px = list(d.getdata())
        return sum(px) / len(px)
    rows = []
    summary = {"damage_words_at_rung": {}, "clean_words_at_rung": {}, "mad_vs_rung0": {}}
    for si in range(a.seeds):
        seed = 5000 + si * 101
        for st in a.strengths:
            row = [cells.get((seed, st, r)) for r in range(5)]
            rows.append((seed, st, row))
            for r in range(5):
                p = cells.get((seed, st, r))
                if not p:
                    continue
                d = (vlm.get((seed, st, r)) or "").lower()
                summary["damage_words_at_rung"].setdefault(r, []).append(
                    sum(1 for w in DAMAGE if w in d))
                summary["clean_words_at_rung"].setdefault(r, []).append(
                    sum(1 for w in CLEAN if w in d))
                if r and cells.get((seed, st, 0)):
                    summary["mad_vs_rung0"].setdefault(r, []).append(
                        round(mad(cells[(seed, st, 0)], p), 1))

    # contact sheet with captions
    W = 300
    from PIL import ImageDraw
    sheet_w = W * 5
    sheet_h = sum(int(W * Image.open(next(p for p in row if p)).size[1]
                          / Image.open(next(p for p in row if p)).size[0]) + 44
                  for _, _, row in rows if any(row))
    sheet = Image.new("RGB", (sheet_w, sheet_h), (18, 18, 20))
    draw = ImageDraw.Draw(sheet)
    y = 0
    for seed, st, row in rows:
        if not any(row):
            continue
        h = None
        for r, p in enumerate(row):
            if not p:
                continue
            im = Image.open(p).convert("RGB")
            h = int(W * im.size[1] / im.size[0])
            sheet.paste(im.resize((W, h)), (r * W, y))
            draw.text((r * W + 6, y + h + 4), "rung %d  seed %d  lora %.1f" % (r, seed, st),
                      fill=(240, 240, 200))
            draw.text((r * W + 6, y + h + 20), (ladder[r][:48] if r < len(ladder) else ""),
                      fill=(180, 200, 220))
        y += (h or 0) + 44
    sheet_path = os.path.join(out, "%s.jpg" % a.character)
    sheet.save(sheet_path, quality=88)

    avg = lambda xs: round(sum(xs) / len(xs), 2) if xs else None
    rep = {r: {"damage_words": avg(summary["damage_words_at_rung"].get(r, [])),
               "clean_words": avg(summary["clean_words_at_rung"].get(r, [])),
               "mad_vs_rung0": avg(summary["mad_vs_rung0"].get(r, []))}
           for r in range(5)}
    json.dump({"character": a.character, "cells": {"%s|%s|%s" % k: v for k, v in
                                                     cells.items()},
               "vlm": {"%s|%s|%s" % k: v for k, v in vlm.items()},
               "per_rung": rep, "sheet": sheet_path},
              open(os.path.join(out, "%s.json" % a.character), "w"), indent=1)
    note = "; ".join("rung %d: damage-words %s clean-words %s mad-vs-0 %s"
                     % (r, rep[r]["damage_words"], rep[r]["clean_words"],
                        rep[r]["mad_vs_rung0"]) for r in range(5))
    cards.stamp("characters", a.character, "MEASURED",
                "wear_sweep: rungs 0-4 x LoRA %s x %d seeds on %s; VLM damage-word count "
                "+ MAD vs rung 0; sheet %s" % (a.strengths, a.seeds, a.engine,
                                               os.path.relpath(sheet_path, STUDIO)),
                note=note[:300])
    print(json.dumps(rep, indent=1))
    print("sheet:", sheet_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
