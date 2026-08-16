#!/usr/bin/env python3
"""studio/_tools/look_sheets.py - grade sheets a human can actually grade.

    python3 studio/_tools/look_sheets.py [--refs N]

THE PROBLEM THIS FIXES, in the user's words: "looks have different shades, not sure what
I'm grading." I showed graded frames with no ungraded reference and no grouping, which
asks someone to judge a colour grade from memory. Nobody can do that.

WHAT THIS MAKES INSTEAD:
  1. per-look strips - UNGRADED reference first, then the same frame graded, on THREE
     different source frames (a bright exterior, a dark night interior, a face). A grade
     that only behaves on one kind of picture is the common failure and it is invisible
     on a single reference.
  2. one contrast sheet per FAMILY (night looks together, bleach/desat together, warm
     together), because a look is chosen against its neighbours - "which of these five
     night grades do I want" is the real question, not "is this one good".
  3. every panel captioned with the measured numbers (luma, saturation, crushed%), so
     the eye and the instrument are on the same page - literally.

Written to samples/looks/sheets/. Nothing is judged here: this tool exists so a judgement
is POSSIBLE.
"""
import argparse
import json
import os
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
sys.path.insert(0, STUDIO)
sys.path.insert(0, TOOLS)
import cards                                   # noqa: E402
import look_check                              # noqa: E402

OUT = os.path.join(STUDIO, "samples", "looks", "sheets")

# Three sources on purpose: a grade that crushes only the dark frame, or only kills skin,
# is invisible on one reference.
SOURCES = {
    "exterior": os.path.join(STUDIO, "samples", "isolation", "places",
                             "clean_airship_deck_0.png"),
    "night": os.path.join(STUDIO, "samples", "isolation", "places",
                          "clean_rooftop_night_0.png"),
    "face": os.path.join(STUDIO, "samples", "isolation", "characters",
                         "char_linruo_0.png"),
}

FAMILIES = {
    "night": ("night", "day_for_night", "moonlit", "sodium", "neon", "storm"),
    "desaturated": ("noir", "bleach", "bleach_bypass", "sepia", "faded_film", "memory"),
    "warm": ("golden", "firelight", "dawn", "sunset", "heat_haze"),
    "clean": ("neutral", "overcast", "fluorescent", "hospital", "cold", "underwater"),
    "stylised": ("dream", "blockbuster"),
}


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def graded(grade, src, dst):
    r = sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vf", grade, "-frames:v", "1", dst)
    return os.path.exists(dst) if r.returncode == 0 else False


def caption(im, text, sub=""):
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    d.rectangle([0, im.size[1] - 34, im.size[0], im.size[1]], fill=(12, 12, 14))
    d.text((6, im.size[1] - 30), text, fill=(245, 240, 210))
    if sub:
        d.text((6, im.size[1] - 16), sub, fill=(150, 190, 220))
    return im


def cell(path, w, label, sub):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    h = int(w * im.size[1] / im.size[0])
    im = im.resize((w, h))
    canvas = Image.new("RGB", (w, h + 34), (12, 12, 14))
    canvas.paste(im, (0, 0))
    return caption(canvas, label, sub)


def main():
    ap = argparse.ArgumentParser(description="Before/after grade sheets, by family.")
    ap.add_argument("--width", type=int, default=300)
    a = ap.parse_args()
    from PIL import Image
    os.makedirs(OUT, exist_ok=True)
    srcs = {k: v for k, v in SOURCES.items() if os.path.exists(v)}
    if not srcs:
        print("no source frames found", file=sys.stderr)
        return 2
    base = {k: look_check.stats(v) for k, v in srcs.items()}
    looks = {cid: c for cid, c in cards.load("looks").items()
             if not cid.startswith("_") and str(c.get("grade") or "").strip()}

    # ---- per-look strips: reference first, then each source graded ------------------
    made = {}
    for cid, c in sorted(looks.items()):
        cells = []
        for name, src in srcs.items():
            b = base[name]
            cells.append(cell(src, a.width, "%s - UNGRADED" % name,
                              "luma %.0f  sat %.0f  crushed %.0f%%"
                              % (b["luma"], b["sat"], 100 * b["crushed"])))
            dst = os.path.join(OUT, "%s__%s.png" % (cid, name))
            if graded(c["grade"], src, dst):
                s = look_check.stats(dst)
                cells.append(cell(dst, a.width, "%s - %s" % (name, cid),
                                  "luma %.0f (%+.0f)  sat %.0f (%+.0f)  crushed %.0f%%"
                                  % (s["luma"], s["luma"] - b["luma"], s["sat"],
                                     s["sat"] - b["sat"], 100 * s["crushed"])))
        if not cells:
            continue
        h = max(im.size[1] for im in cells)
        sheet = Image.new("RGB", (a.width * len(cells), h), (12, 12, 14))
        for i, im in enumerate(cells):
            sheet.paste(im, (i * a.width, 0))
        p = os.path.join(OUT, "%s.jpg" % cid)
        sheet.save(p, quality=90)
        made[cid] = p
    print("per-look strips:", len(made))

    # ---- family sheets: one source, every look in the family, side by side ---------
    for fam, ids in FAMILIES.items():
        have = [i for i in ids if i in looks]
        if not have:
            continue
        for name, src in srcs.items():
            b = base[name]
            cells = [cell(src, a.width, "UNGRADED (%s)" % name,
                          "luma %.0f  sat %.0f  crushed %.0f%%"
                          % (b["luma"], b["sat"], 100 * b["crushed"]))]
            for cid in have:
                dst = os.path.join(OUT, "%s__%s.png" % (cid, name))
                if not os.path.exists(dst):
                    graded(looks[cid]["grade"], src, dst)
                if os.path.exists(dst):
                    s = look_check.stats(dst)
                    cells.append(cell(dst, a.width, cid,
                                      "luma %+.0f  sat %+.0f  crushed %.0f%%"
                                      % (s["luma"] - b["luma"], s["sat"] - b["sat"],
                                         100 * s["crushed"])))
            h = max(im.size[1] for im in cells)
            sheet = Image.new("RGB", (a.width * len(cells), h), (12, 12, 14))
            for i, im in enumerate(cells):
                sheet.paste(im, (i * a.width, 0))
            sheet.save(os.path.join(OUT, "FAMILY_%s__%s.jpg" % (fam, name)), quality=90)
        print("family sheet:", fam, len(have), "looks")
    # tidy the intermediate pngs; the jpgs are the deliverable
    for f in os.listdir(OUT):
        if f.endswith(".png"):
            os.remove(os.path.join(OUT, f))
    print("sheets in", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
