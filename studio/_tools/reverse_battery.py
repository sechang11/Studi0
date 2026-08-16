#!/usr/bin/env python3
"""studio/_tools/reverse_battery.py - enough reverse-angle samples to confirm (or kill)
the master-frame kit's `edit` arm.

    python3 studio/_tools/reverse_battery.py [--per 3] [--places N] [--characters N]

WHY. One reverse angle is an anecdote. The user's words: "reverse might need more samples
for me to confirm it works." So: several heroes across places AND characters, three
derived angles each, every pair shown hero-then-derived so the question "is this the same
world / the same person" can be answered by looking, not remembering.

THE ANGLES, chosen to be genuinely hard:
  reverse   180 degrees - looking back the way we came. The angle that must invent the
            wall behind the camera, so it is where invention shows.
  profile   90 degrees - a side view. Tests whether layout survives rotation.
  high      the same place from above. Tests whether the model understands the space
            rather than the picture.

MEASURED per pair, so the sheet is not the only evidence: palette distance (mean per-
channel histogram difference - a new WORLD shifts palette, a new ANGLE should not), and
the VLM's own description of the derived frame checked against the source card's nouns
(frame_check). Both go under the panel. The verdict stays the human's.
"""
import argparse
import glob
import json
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
sys.path.insert(0, STUDIO)
sys.path.insert(0, TOOLS)
import cards                                     # noqa: E402
import master_frames as mf                       # noqa: E402
import frame_check as fc                         # noqa: E402

OUT = os.path.join(STUDIO, "samples", "reverse_battery")

ANGLES = {
    "reverse": ("the same {what}, seen from the opposite direction - the camera has "
                "turned 180 degrees and looks back the way it came. Same {what}, same "
                "materials, same lighting, same time of day, same style."),
    "profile": ("the same {what}, seen from the side - the camera has moved 90 degrees. "
                "Same {what}, same materials, same lighting, same style."),
    "high":    ("the same {what}, seen from high above looking down. Same {what}, same "
                "materials, same lighting, same style."),
}


def palette_distance(a, b):
    """Mean absolute difference of 3x64-bin RGB histograms, normalised. Motion-tolerant
    and layout-tolerant: it answers 'is this the same WORLD', not 'is this the same
    picture' - which is exactly the question a reverse angle raises."""
    from PIL import Image
    ha, hb = [], []
    for p, acc in ((a, ha), (b, hb)):
        im = Image.open(p).convert("RGB").resize((256, 256))
        for ch in im.split():
            h = ch.histogram()
            binned = [sum(h[i * 4:(i + 1) * 4]) for i in range(64)]
            tot = sum(binned) or 1
            acc.extend(v / tot for v in binned)
    return round(sum(abs(x - y) for x, y in zip(ha, hb)) / len(ha), 4)


def main():
    ap = argparse.ArgumentParser(description="Reverse/profile/high angles from several heroes.")
    ap.add_argument("--places", type=int, default=3)
    ap.add_argument("--characters", type=int, default=2)
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    jobs = []
    pl = cards.load("places")
    for cid in sorted(pl)[:200]:
        if cid.startswith("_"):
            continue
        f = sorted(glob.glob(os.path.join(STUDIO, "samples", "isolation", "places",
                                          "clean_%s_*.png" % cid)))
        if f and len([j for j in jobs if j[0] == "place"]) < a.places:
            jobs.append(("place", cid, f[0], pl[cid]))
    ch = cards.load("characters")
    for cid in sorted(ch):
        if cid.startswith("_"):
            continue
        f = sorted(glob.glob(os.path.join(STUDIO, "samples", "isolation", "characters",
                                          "*%s_*.png" % cid.lower())))
        if f and len([j for j in jobs if j[0] == "character"]) < a.characters:
            jobs.append(("character", cid, f[0], ch[cid]))

    rows, report = [], []
    for i, (kind, cid, hero, card) in enumerate(jobs):
        what = ("place" if kind == "place" else "person")
        subject = (card.get("name") or cid)
        want = (fc.nouns_of(card.get("name"), card.get("family"),
                            (card.get("tags") or "").split(",")[:6]) if kind == "place"
                else fc.nouns_of((card.get("tags") or "").split(",")[:10],
                                 (card.get("prose") or "")[:200],
                                 "person woman man figure", limit=14))
        row = [("HERO", hero, None, None)]
        for ang, tpl in ANGLES.items():
            dst = os.path.join(OUT, "%s_%s_%s.png" % (kind, cid, ang))
            prompt = tpl.format(what=what) + " Subject: %s." % subject
            if not os.path.exists(dst):
                mf.edit(hero, prompt, dst, seed=a.seed + i * 7)
            if not os.path.exists(dst):
                print("  ! %s %s %s failed" % (kind, cid, ang))
                continue
            desc = fc.describe(dst)
            hits = fc.check(desc, want)
            pd = palette_distance(hero, dst)
            row.append((ang, dst, pd, (hits, desc)))
            report.append({"kind": kind, "id": cid, "angle": ang, "palette_distance": pd,
                           "vlm_hits": hits, "vlm": desc[:300], "file": dst})
            print("%-10s %-22s %-8s palette %.4f  vlm %s"
                  % (kind, cid, ang, pd, ",".join(hits[:4]) or "NO HITS"))
        rows.append((kind, cid, row))

    # contact sheet: one row per hero, hero first then the three angles
    from PIL import Image, ImageDraw
    W = 320
    sheets = []
    for kind, cid, row in rows:
        cells = []
        for ang, path, pd, vlm in row:
            im = Image.open(path).convert("RGB")
            h = int(W * im.size[1] / im.size[0])
            c = Image.new("RGB", (W, h + 40), (12, 12, 14))
            c.paste(im.resize((W, h)), (0, 0))
            d = ImageDraw.Draw(c)
            d.text((6, h + 4), "%s  %s" % (cid, ang), fill=(245, 240, 210))
            if pd is not None:
                seen = "seen: " + (",".join(vlm[0][:3]) if vlm[0] else "NOTHING")
                d.text((6, h + 20), "palette dist %.3f   %s" % (pd, seen[:44]),
                       fill=(150, 200, 220))
            cells.append(c)
        h = max(c.size[1] for c in cells)
        s = Image.new("RGB", (W * len(cells), h), (12, 12, 14))
        for i, c in enumerate(cells):
            s.paste(c, (i * W, 0))
        sheets.append(s)
    if sheets:
        tot_h = sum(s.size[1] for s in sheets)
        big = Image.new("RGB", (max(s.size[0] for s in sheets), tot_h), (12, 12, 14))
        y = 0
        for s in sheets:
            big.paste(s, (0, y))
            y += s.size[1]
        p = os.path.join(OUT, "reverse_battery.jpg")
        big.save(p, quality=88)
        print("sheet:", p)
    json.dump(report, open(os.path.join(OUT, "report.json"), "w"), indent=1)
    if report:
        pds = [r["palette_distance"] for r in report]
        seen = sum(1 for r in report if r["vlm_hits"])
        print("\n%d derived angles: palette distance mean %.4f (max %.4f); VLM still sees "
              "the subject in %d of %d" % (len(report), sum(pds) / len(pds), max(pds),
                                           seen, len(report)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
