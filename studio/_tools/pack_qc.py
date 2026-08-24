#!/usr/bin/env python3
"""pack_qc.py - does a character pack actually contain what it claims?

    python3 studio/_tools/pack_qc.py                 every foundry character
    python3 studio/_tools/pack_qc.py bai-liwen       one of them
    python3 studio/_tools/pack_qc.py --json

pack_report() counts files, and a count cannot see the failure this project keeps
producing: a step that runs, writes its output, and changes nothing. Bai Liwen's
first pack was 19 of 19 with six expressions that were all the same neutral face
and three presentation shots that were one framing.

So this measures DISTINCTNESS. Views that must differ from each other are compared
pairwise; views that must hold still are compared too, in the other direction.

    expressions   must differ from expr_neutral - a joy that matches neutral is
                  not a joy, it is the reference winning over the instruction
    presentation  must differ from each other - three identical hero shots are
                  one shot rendered three times
    turnarounds   must differ from turn_front, or the camera never moved
    face views    must be TIGHTER than the body views - a "face turnaround" that
                  is another full body is mislabelled, not missing

The distance is a downscaled greyscale mean-absolute difference: crude, fast, and
sufficient to separate "a different expression" from "the same picture again".
Thresholds are stated, not tuned to make a pack pass.
"""
import argparse, json, os, sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(TOOLS))
FOUNDRY = os.path.join(ROOT, "studio", "foundry", "characters")

# a pair whose distance falls below this did not actually change
MIN_DIFFER = 0.055          # "these two must not be the same picture"
MIN_TURN = 0.070            # the camera moved, so more should have changed

# Expressions are judged on the MOUTH, which is where expression actually lives,
# and which separates the styles far better than the whole frame. Measured across
# one photoreal and one anime pack, neutral vs each of five expressions:
#     region   photoreal        anime
#     whole    0.048 - 0.077    0.095 - 0.166
#     face     0.045 - 0.100    0.145 - 0.232
#     mouth    0.058 - 0.109    0.179 - 0.248     <- widest floor
# A photoreal face expresses with far fewer pixels than a cel face, so a
# whole-frame threshold set on anime cries wolf on every photoreal pack - and a
# check that cries wolf is ignored within a day. Two identical frames score 0.0,
# so 0.050 still catches the real failure this exists for.
MIN_EXPR = 0.050


def _load(path, size=96, region=None):
    """region='mouth' crops to where expression actually lives.

    Expressions are judged on the FACE, not the frame. A photoreal pack keeps a
    real background across every view, so a genuine smile moves a small fraction
    of the pixels and a whole-frame distance reads it as "nothing changed" -
    measured, on two packs whose expressions were plainly correct by eye. An
    anime pack has a near-blank ground, which is why this only showed up here.
    """
    from PIL import Image
    im = Image.open(path).convert("L")
    if region == "mouth":
        W, H = im.size
        im = im.crop((int(W * 0.32), int(H * 0.28), int(W * 0.68), int(H * 0.60)))
    im = im.resize((size, size))
    return list(im.tobytes())


def _dist(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / (255.0 * len(a))


def check(cid, verbose=True):
    d = os.path.join(FOUNDRY, cid)
    ap = os.path.join(d, "asset.json")
    if not os.path.isfile(ap):
        return {"id": cid, "error": "no such character"}
    have, faces = {}, {}
    for fn in os.listdir(d):
        if fn.endswith(".png"):
            try:
                have[fn[:-4]] = _load(os.path.join(d, fn))
                faces[fn[:-4]] = _load(os.path.join(d, fn), region="mouth")
            except Exception:
                pass
    issues = []

    def cmp(a, b, floor, why, src=None):
        src = src if src is not None else have
        if a not in src or b not in src:
            return None
        dd = _dist(src[a], src[b])
        if dd < floor:
            issues.append({"pair": [a, b], "distance": round(dd, 4),
                           "floor": floor, "why": why})
        return dd

    for k in [k for k in have if k.startswith("expr_") and k != "expr_neutral"]:
        cmp(k, "expr_neutral", MIN_EXPR,
            "the expression did not move the face - the identity reference is "
            "outweighing the instruction", src=faces)

    pres = sorted(k for k in have if k.startswith("pres_"))
    for i in range(len(pres)):
        for j in range(i + 1, len(pres)):
            cmp(pres[i], pres[j], MIN_DIFFER,
                "two presentation shots are the same picture - lighting and "
                "framing did not vary")

    for k in [k for k in have if k.startswith("turn_") and k != "turn_front"]:
        cmp(k, "turn_front", MIN_TURN, "the camera did not move")

    res = {"id": cid, "images": len(have), "issues": issues,
           "clean": not issues}
    if verbose:
        mark = "ok  " if res["clean"] else "BAD "
        print("%s %-16s %2d images, %d issue(s)"
              % (mark, cid, len(have), len(issues)))
        for it in issues:
            print("      %-34s d=%.3f < %.3f" % (" vs ".join(it["pair"]),
                                                 it["distance"], it["floor"]))
            print("      %s" % it["why"])
    return res


def main():
    ap = argparse.ArgumentParser(description="Check a character pack for views "
                                             "that did not actually change.")
    ap.add_argument("character", nargs="*")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    ids = a.character or sorted(x for x in os.listdir(FOUNDRY)
                                if os.path.isdir(os.path.join(FOUNDRY, x)))
    out = [check(c, verbose=not a.json) for c in ids]
    if a.json:
        print(json.dumps(out, indent=1))
        return
    bad = [o for o in out if o.get("issues")]
    print()
    print("%d checked, %d with issues" % (len(out), len(bad)))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
