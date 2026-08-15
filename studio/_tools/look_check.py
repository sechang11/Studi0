#!/usr/bin/env python3
"""look_check.py - MEASURED evidence for every look card's `grade`.

    python3 studio/_tools/look_check.py [--only ID]

A look has two halves: `tags` (asked of the model - unreliable, see task 8) and `grade`
(an ffmpeg filter string, deterministic - the half that actually works, which is why
make_cut applies it). The grade is measurable exactly: apply it to ONE fixed reference
frame and read what moved.

  mad         mean absolute pixel difference vs the ungraded frame - 0 means the grade
              is inert (a look that changes nothing is a lie).
  luma        mean Y before -> after. A `night`/`low_key` look must go DOWN; a
              `high_key`/`overexposed` look must go UP.
  sat         mean chroma before -> after. `bleach_bypass`/`monochrome`/`noir` must drop
              it; `vivid`/`technicolor` must raise it.
  crushed     fraction of pixels at Y<=16 after - the "night grade crushes dark inserts
              to black" defect (task 26): flag when it exceeds 25%.

VERDICT: MEASURED, note carries the numbers and any expectation the id itself states
that the numbers contradict. status -> weak only when the grade is INERT (mad < 0.5),
malformed (ffmpeg refuses it), or crushes >40% of the frame to black. Reference frame:
the airship-deck isolation plate (bright, full-range) and a dark night stadium plate;
the note reports both so a grade that only misbehaves in the dark is caught.
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
import cards                                        # noqa: E402

REFS = {
    "bright": os.path.join(STUDIO, "samples", "isolation", "places",
                           "clean_airship_deck_0.png"),
}
OUT = os.path.join(STUDIO, "samples", "looks")

WANT_DOWN = ("night", "low_key", "dark", "noir", "moon", "dusk", "shadow", "underexposed",
             "day_for_night", "cold_night")
WANT_UP = ("high_key", "overexposed", "bright", "bleached", "sunlit", "day")
WANT_DESAT = ("bleach", "monochrome", "noir", "sepia", "faded", "washed", "memory", "grey",
              "gray", "desat", "muted", "cold")
WANT_SAT = ("vivid", "technicolor", "saturated", "pop", "neon", "candy", "golden", "warm")


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def stats(path):
    """mean luma, mean saturation, crushed fraction - ONE instrument (PIL over the actual
    pixels). The first version mixed ffmpeg signalstats (which reads a PNG at a different
    range) with a lut pass and printed a crushed number that contradicted its own fail
    verdict. Ground truth is the pixel array."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    hsv = im.convert("HSV")
    y = list(im.convert("L").getdata())
    s = list(hsv.getchannel("S").getdata())
    n = len(y)
    return {"luma": sum(y) / n, "sat": sum(s) / n,
            "crushed": sum(1 for v in y if v <= 16) / n}


def mad(a, b):
    from PIL import Image, ImageChops
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        ib = ib.resize(ia.size)
    d = ImageChops.difference(ia, ib).convert("L")
    px = list(d.getdata())
    return sum(px) / len(px)


def apply(grade, src, dst):
    r = sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vf", grade, "-frames:v", "1", dst)
    return r.returncode == 0 and os.path.exists(dst), (r.stderr or "")[-200:]


def main():
    ap = argparse.ArgumentParser(description="Measure every look's grade on a reference frame.")
    ap.add_argument("--only")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    base = {k: stats(p) for k, p in REFS.items() if os.path.exists(p)}
    if not base:
        print("no reference frame found", file=sys.stderr)
        return 2
    tally = {"ok": 0, "weak": 0, "nograde": 0}
    for cid, card in sorted(cards.load("looks").items()):
        if cid.startswith("_") or (a.only and cid != a.only):
            continue
        grade = str(card.get("grade") or "").strip()
        if not grade:
            cards.stamp("looks", cid, "MEASURED", "look_check: card has no grade string",
                        note="tags-only look; the deterministic half is missing, so the "
                             "look reaches pixels only through the model, which task 8 "
                             "measured as unreliable")
            tally["nograde"] += 1
            print("%-18s no grade" % cid)
            continue
        notes, fails = [], []
        for ref, src in REFS.items():
            if not os.path.exists(src):
                continue
            dst = os.path.join(OUT, "%s__%s.png" % (cid, ref))
            ok, err = apply(grade, src, dst)
            if not ok:
                fails.append("ffmpeg refused the grade: %s" % err.strip()[-120:])
                continue
            after = stats(dst)
            d = mad(src, dst)
            b = base[ref]
            dl = (after["luma"] or 0) - (b["luma"] or 0)
            ds = (after["sat"] or 0) - (b["sat"] or 0)
            notes.append("%s: mad=%.1f luma %.0f->%.0f (%+.0f) sat %.0f->%.0f (%+.0f) "
                         "crushed=%.0f%%" % (ref, d or 0, b["luma"] or 0, after["luma"] or 0,
                                             dl, b["sat"] or 0, after["sat"] or 0, ds,
                                             100 * (after["crushed"] or 0)))
            if d is not None and d < 0.5:
                fails.append("INERT on %s (mad %.2f) - the grade changes nothing" % (ref, d))
            if (after["crushed"] or 0) > 0.40:
                fails.append("crushes %.0f%% of the %s frame to black (task 26 defect)"
                             % (100 * after["crushed"], ref))
            lid = cid.lower()
            if any(w in lid for w in WANT_DOWN) and dl > 5:
                notes.append("EXPECTED darker, got brighter (%+.0f)" % dl)
            if any(w in lid for w in WANT_UP) and dl < -5:
                notes.append("EXPECTED brighter, got darker (%+.0f)" % dl)
            if any(w in lid for w in WANT_DESAT) and ds > 5:
                notes.append("EXPECTED less saturated, got more (%+.0f)" % ds)
            if any(w in lid for w in WANT_SAT) and ds < -5:
                notes.append("EXPECTED more saturated, got less (%+.0f)" % ds)
        note = ("; ".join(fails) + " | " if fails else "grade applies and moves the frame; ") \
            + "; ".join(notes)
        cards.stamp("looks", cid, "MEASURED",
                    "look_check: grade applied to a reference frame (ffmpeg signalstats)",
                    note=note[:300])
        if fails:
            p = os.path.join(STUDIO, "looks", cid + ".json")
            c = json.load(open(p, encoding="utf-8"))
            if c.get("status") == "ready":
                c["status_before_check"] = "ready"
                c["status"] = "weak"
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(c, f, indent=2, ensure_ascii=False)
                    f.write("\n")
            tally["weak"] += 1
        else:
            tally["ok"] += 1
        print("%-18s %s" % (cid, note[:120]))
    print(json.dumps(tally))
    return 0


if __name__ == "__main__":
    sys.exit(main())
