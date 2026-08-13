#!/usr/bin/env python3
"""studio/_tools/package_check.py - what makes a card COMPLETE, and which cards are not.

    python3 studio/_tools/package_check.py                 every kind, summary
    python3 studio/_tools/package_check.py --kind characters
    python3 studio/_tools/package_check.py --kind places --short   only what is missing
    python3 studio/_tools/package_check.py --json

A card with one picture is not a card you can use. You cannot tell whether a character
holds at a wide shot, whether a place survives a different style, or whether an emotion
reads on a face you have not already memorised. "It exists" and "it is usable" are
different claims, and only the second is worth anything at render time.

So each KIND has a PACKAGE: the spread that makes it usable, not a frame count. Twenty
frames of the same character in the same framing in the same style is one frame twenty
times. What matters is the number of DISTINCT values along each axis that card has to
survive - which is why every requirement below is a distinct-count, not a total.

    characters  four framings, because identity that only holds in close-up is a portrait
                and not a cast member. Several styles, because a character bound to one
                style cannot appear in your other films. Several places, for the same
                reason. And a reference sheet, which is what holds the face when there is
                no trained LoRA.
    places      clean plates FIRST - frames with nobody in them - because that is the only
                view that shows the place rather than someone standing in it. Then a
                spread of styles, so you know the place is not one look in disguise.
    styles      several frames and at least one plate on a neutral subject, so what you are
                looking at is the style and not the subject wearing it.
    emotions    several frames at purity 0 - no character, no place - because an emotion
                read off a familiar face is a face you recognise, not an expression you
                judged.
    motions     clips, and eventually clips that PASS motion_check. Counting clips that do
                not do what they claim would be counting the wrong thing.

WHAT CANNOT BE MEASURED YET, STATED RATHER THAN QUIETLY DROPPED. Outfits. A character card
carries a five-rung wear ladder, but the RECIPES DO NOT RECORD WHICH RUNG WAS USED - there
is no `wear` field on a rendered frame. So "four outfits" is not checkable today, and the
fix is upstream: roll.py should write the wear rung it chose into the recipe, the same way
it writes framing and look. Until it does, this file refuses to guess.
"""
import argparse, json, os, sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

# The package per kind. Each entry is (axis, how many DISTINCT values, why it matters).
# `frames` is a raw count; `pure` counts frames where this card is alone in the picture.
PACKAGE = {
    "characters": [
        ("frames", 20, "enough to choose from rather than accept"),
        ("framing", 4, "identity that only holds in close-up is a portrait, not a cast member"),
        ("style", 6, "a character bound to one style cannot appear in your other films"),
        ("place", 8, "a character who only works in one room is a prop"),
        ("sheet", 1, "the reference sheet is what holds the face when there is no LoRA"),
    ],
    "places": [
        ("frames", 8, "one angle is a postcard"),
        ("pure", 3, "a clean plate is the only view that shows the place and not a person"),
        ("style", 3, "so you know it is a place and not one look in disguise"),
    ],
    "styles": [
        ("frames", 4, "one frame cannot show what a style does to different subjects"),
        ("pure", 1, "a plate on a neutral subject shows the style rather than the subject"),
    ],
    "emotions": [
        ("frames", 4, "one face is one person's version of the feeling"),
        ("pure", 2, "read off a familiar cast member it is a face you know, not an expression"),
    ],
    "motions": [
        ("frames", 3, "a motion is a claim about movement and needs more than one attempt"),
    ],
    "cameras": [
        ("frames", 3, "same"),
    ],
}


def coverage(kind):
    import library_index as L
    b = L.browse(kind)
    if not b:
        return None
    facet = b["facet"]
    d = L.payload()
    by = {}
    for it in d["items"]:
        v = it.get(facet)
        if v not in (None, ""):
            by.setdefault(str(v), []).append(it)

    rows = []
    for card in b["cards"]:
        its = by.get(card["id"], [])
        have = {"frames": len(its),
                "pure": sum(1 for x in its if (x.get("purity") or {}).get(facet) == 0),
                "sheet": 1 if _has_sheet(kind, card["id"]) else 0}
        for axis in ("framing", "style", "place", "look"):
            have[axis] = len({x.get(axis) for x in its if x.get(axis)})
        missing = []
        for axis, need, why in PACKAGE.get(kind, []):
            got = have.get(axis, 0)
            if got < need:
                missing.append({"axis": axis, "have": got, "need": need, "why": why})
        rows.append({"id": card["id"], "have": have, "missing": missing,
                     "complete": not missing})
    rows.sort(key=lambda r: (r["complete"], -len(r["missing"]), r["id"]))
    return {"kind": kind, "facet": facet, "cards": rows,
            "complete": sum(1 for r in rows if r["complete"]), "total": len(rows),
            "package": [{"axis": a, "need": n, "why": w} for a, n, w in PACKAGE.get(kind, [])]}


def _has_sheet(kind, cid):
    if kind != "characters":
        return True
    p = os.path.join(STUDIO, "characters", cid + ".json")
    try:
        return bool(json.load(open(p, encoding="utf-8")).get("sheet"))
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind")
    ap.add_argument("--short", action="store_true", help="only cards that are incomplete")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    kinds = [a.kind] if a.kind else list(PACKAGE)
    out = []
    for k in kinds:
        c = coverage(k)
        if not c:
            print("  no such kind: %s" % k)
            continue
        out.append(c)
        if a.json:
            continue
        print("\n%s - %d of %d complete" % (k.upper(), c["complete"], c["total"]))
        print("  package: " + ", ".join("%s x%d" % (p["axis"], p["need"])
                                        for p in c["package"]))
        for r in c["cards"]:
            if a.short and r["complete"]:
                continue
            if r["complete"]:
                print("    %-22s complete" % r["id"][:22])
            else:
                gaps = ", ".join("%s %d/%d" % (m["axis"], m["have"], m["need"])
                                 for m in r["missing"])
                print("    %-22s %s" % (r["id"][:22], gaps))
    if a.json:
        print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
