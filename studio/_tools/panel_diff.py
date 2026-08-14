#!/usr/bin/env python3
"""Which variables actually change the picture?

The card system's whole purpose is to answer that, and the pass meant to answer it
never ran. But the cheapest and most valuable half of the answer needs no human eye
at all: if every option of a variable renders the same image, the knob is INERT and
no amount of looking will make it useful. Knowing which knobs are inert saves renders.

Every panel of a card is generated with an identical subject sentence and an identical
seed (9001); only the option clause changes. So the pairwise difference between panels
IS the effect size of that variable, measured rather than asserted.

    python3 studio/_tools/panel_diff.py            # all cards -> studio/panel_effects.json

Reported per card:
    spread   mean pairwise mean-absolute-pixel difference across all option pairs
    weakest  the most similar pair, i.e. the two options most likely redundant
    dupes    pairs below DUPE - options that will render as the same picture

Calibration, from panels already inspected by eye:
    shot.size            spread 40+   obviously different pictures
    a control vs its own option        typically 15-30
    two phrasings of one idea          under 8
"""
import json, os, sys
from itertools import combinations
from PIL import Image, ImageChops

import argparse
argparse.ArgumentParser(description='panel diff').parse_args()
# ^ the CLI contract: --help exits HERE, before any work below runs.
HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
CARDS = os.path.join(STUDIO, "cards")

DUPE = 8.0        # below this, two options are the same picture
INERT = 6.0       # below this on average, the whole variable does nothing
THUMB = (160, 90)  # compare small: we want gross composition, not JPEG noise
LAYOUT = (16, 9)   # compare TINY: only gross layout survives at this size

# A card is only evidence if the panels differ BECAUSE OF the variable. They are all
# generated with one subject sentence and one seed (9001) and only the option clause
# changes - but changing any token shifts SDXL's conditioning enough to recompose the
# shot. Verified: grade.grain_size's four panels (fine/normal/coarse/clumpy) are four
# unrelated portraits at different framings with no visible grain difference at all.
#
# So measure two things and compare them:
#   detail  difference at 160x90 - the variable's effect PLUS any recomposition
#   layout  difference at 16x9  - only gross composition survives this
#
# High layout difference means the panels are different PICTURES, not the same picture
# with the variable changed. For a gross variable (shot size, framing) that is correct
# and expected. For a subtle one (grain, vignette, bokeh, line colour) it means the card
# is showing you noise and cannot support its own claim.
RECOMPOSED = 18.0


def load(path):
    im = Image.open(path).convert("RGB")
    return im.resize(THUMB), im.resize(LAYOUT)


def mad(a, b):
    if a.size != b.size:
        b = b.resize(a.size)
    d = ImageChops.difference(a, b)
    h = d.histogram()
    # mean absolute difference across all three channels
    tot = n = 0
    for ch in range(3):
        band = h[ch * 256:(ch + 1) * 256]
        for v, cnt in enumerate(band):
            tot += v * cnt
            n += cnt
    return tot / max(n, 1)


def main():
    out = {}
    for fn in sorted(os.listdir(CARDS)):
        if not fn.endswith(".json"):
            continue
        card = json.load(open(os.path.join(CARDS, fn), encoding="utf-8"))
        panels = [p for p in (card.get("panels") or []) if p.get("sample")]
        det, lay, labels = [], [], []
        for p in panels:
            rel = p["sample"].split("/samples/")[-1]
            fp = os.path.join(STUDIO, "samples", *rel.split("/"))
            if os.path.isfile(fp):
                try:
                    d, l = load(fp)
                    det.append(d)
                    lay.append(l)
                    labels.append(str(p.get("value")))
                except Exception:
                    pass
        if len(det) < 2:
            continue
        pairs, lpairs = [], []
        for (i, j) in combinations(range(len(det)), 2):
            pairs.append((mad(det[i], det[j]), labels[i], labels[j]))
            lpairs.append(mad(lay[i], lay[j]))
        pairs.sort()
        spread = sum(p[0] for p in pairs) / len(pairs)
        layout = sum(lpairs) / len(lpairs)
        dupes = [{"a": a, "b": b, "diff": round(d, 2)} for d, a, b in pairs if d < DUPE]
        rec = {
            "variable": card.get("variable", fn[:-5]),
            "panels": len(det),
            "spread": round(spread, 2),
            "layout_spread": round(layout, 2),
            "weakest_pair": {"a": pairs[0][1], "b": pairs[0][2], "diff": round(pairs[0][0], 2)},
            "strongest_pair": {"a": pairs[-1][1], "b": pairs[-1][2], "diff": round(pairs[-1][0], 2)},
            "dupe_pairs": dupes,
            "class": ("INERT" if spread < INERT else
                      "RECOMPOSED" if layout >= RECOMPOSED else
                      "HAS-DUPES" if dupes else "DISTINCT"),
            # NOT a quality verdict. It answers one question: do these panels differ
            # only in the variable, or are they different pictures? Different pictures
            # is CORRECT for a variable whose effect IS composition (shot size, framing,
            # distance) and WRONG for one whose effect is not (grain, vignette, line
            # colour, hue). Deciding which needs to know what the variable means.
            "isolates_variable": layout < RECOMPOSED and spread >= INERT,
        }
        out[fn[:-5]] = rec

    dst = os.path.join(STUDIO, "panel_effects.json")
    json.dump(out, open(dst, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    by = {}
    for k, v in out.items():
        by.setdefault(v["class"], []).append((v["layout_spread"], k, v["panels"], v["spread"]))
    print("%d cards measured -> %s\n" % (len(out), dst))
    print("layout_spread is the giveaway: how different the panels are as gross COMPOSITION.")
    print("High = the option clause re-rolled the shot, so the card shows recomposition")
    print("noise rather than the variable. Correct for shot size; fatal for grain.\n")
    for cls in ("INERT", "RECOMPOSED", "HAS-DUPES", "DISTINCT"):
        rows = sorted(by.get(cls, []), reverse=(cls == "RECOMPOSED"))
        print("=== %s : %d cards ===" % (cls, len(rows)))
        for lay, k, n, sp in rows[:14]:
            print("  layout %6.2f  detail %6.2f  %-32s %2d panels" % (lay, sp, k, n))
        if len(rows) > 14:
            print("  ... %d more" % (len(rows) - 14))
        print()
    ok = sum(1 for v in out.values() if v["trustworthy"])
    print("TRUSTWORTHY: %d of %d cards (%.0f%%)" % (ok, len(out), 100.0 * ok / len(out)))


if __name__ == "__main__":
    main()
