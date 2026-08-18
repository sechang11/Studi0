#!/usr/bin/env python3
"""studio/_tools/bright_test.py - can a style string ask for a bright picture and get one?

WHY THIS EXISTS. The delivered slate came back at mean luma 35.6/255 against keyframes
that should have been far brighter, and the first thing said about it was that the films
"all seem to have a darkness to them". Three suspects were eliminated by measurement
tonight:

    the video engines    LTX loses 1% of luma, Hunyuan loses none
    the look grades      the darkest of 25 keeps 60%; none halves a picture
    the night grade      not enabled on any short - every beat carries look: None

That leaves the style string, and the delivered films point somewhere specific:

    ad-lumen-lamp    "clean modern product photography, soft diffused daylight"    31.9
    sup-protein      "warm documentary photography, morning kitchen light"         35.6
    hook-garden      "natural light landscape photography, soft golden hour"       34.6
    v2 paperlight    "clean product photography, seamless WHITE BACKGROUND"        78.9
    v2 morning-oat   "bright natural daylight photography, WHITE KITCHEN"          66.7

Every string that ASKS for light with adjectives - diffused, natural, golden, soft - got a
dark picture. The two that NAME a white object got a bright one. That is this project's
governing law showing up in a new place: the model renders nouns, not adjectives. It has
already been proven for look, wear and mood, and this is the same shape.

BUT FIVE DELIVERED FILMS ARE NOT AN EXPERIMENT - they differ in subject, seed and content,
and brightness could just as easily be following what is IN the shot. A white studio
background is a bright object; a kitchen at dawn is not. So this renders one subject, one
seed, one resolution, and varies only the lighting language.

    bare          no lighting language at all - the baseline
    adj_bright    adjectives asking for light, the phrasing the dark films used
    adj_dark      adjectives asking for dark - the control that proves the axis works
    noun_bright   named bright OBJECTS and surfaces, no lighting adjectives
    noun_both     named bright objects AND the bright adjectives

If adj_bright lands near bare and noun_bright lands well above it, the rule holds and the
fix is to rewrite the style library in nouns. If adj_bright works, the darkness came from
somewhere else and this file should say so.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
COMFY_OUT = os.path.expanduser("~/ComfyUI/output")

SUBJECT = "a canvas backpack standing on a wooden table in a room"

# Only the lighting language changes. The subject clause above is byte-identical in all
# five, so any difference in luma is the language and not the scene.
VARIANTS = [
    ("bare", ""),
    ("adj_bright", ", soft diffused daylight, bright, airy, well lit, natural light"),
    ("adj_dark", ", dramatic contrast, moody practical lighting, rich shadows, low key"),
    ("noun_bright", ", white walls, a white tabletop, a large window filling the wall "
                    "behind, white curtains, sunlight falling across the floor"),
    ("noun_both", ", white walls, a white tabletop, a large window filling the wall "
                  "behind, white curtains, sunlight falling across the floor, soft "
                  "diffused daylight, bright, airy"),
]


def sh(*a, **kw):
    return subprocess.run(a, capture_output=True, text=True, **kw)


def luma(path):
    from PIL import Image
    im = Image.open(path).convert("L").resize((256, 144))
    px = list(im.getdata())
    return 255.0 * sum(px) / (len(px) * 255.0)


def render(text, seed, prefix):
    r = sh(sys.executable, os.path.join(ROOT, "scripts", "comfy.py"), "run",
           os.path.join(ROOT, "workflows", "01_qwen_t2i_turbo.json"),
           "-s", "10.inputs.text=%s" % text,
           "-s", "13.inputs.seed=%d" % seed,
           "-s", "15.inputs.filename_prefix=%s" % prefix, cwd=ROOT)
    m = re.search(r"-> (\S+\.png)", r.stdout or "")
    if not m:
        print("      FAILED: %s" % ((r.stderr or r.stdout or "").strip()[-200:]))
        return None
    return os.path.join(COMFY_OUT, m.group(1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="42,1234,7701")
    ap.add_argument("--out", default=os.path.expanduser("~/shared/AB/brightness"))
    a = ap.parse_args()
    seeds = [int(s) for s in a.seeds.split(",") if s.strip()]
    os.makedirs(a.out, exist_ok=True)

    rows = []
    for vid, tail in VARIANTS:
        for seed in seeds:
            p = render(SUBJECT + tail, seed, "claude-generated/bt_%s_%d" % (vid, seed))
            if not p or not os.path.exists(p):
                continue
            keep = os.path.join(a.out, "%s_%d.png" % (vid, seed))
            sh("cp", p, keep)
            y = luma(keep)
            rows.append({"variant": vid, "seed": seed, "luma": round(y, 1)})
            print("  %-12s seed %-5d luma %.1f" % (vid, seed, y))

    json.dump(rows, open(os.path.join(a.out, "results.json"), "w"), indent=1)

    print("\n%-12s %8s %8s   %s" % ("variant", "mean", "n", "vs bare"))
    means = {}
    for vid, _t in VARIANTS:
        got = [r["luma"] for r in rows if r["variant"] == vid]
        if got:
            means[vid] = sum(got) / len(got)
    base = means.get("bare")
    for vid, _t in VARIANTS:
        if vid not in means:
            continue
        delta = ("%+.1f" % (means[vid] - base)) if base else "--"
        print("%-12s %8.1f %8d   %s" % (vid, means[vid], len(seeds), delta))

    if base and "adj_bright" in means and "noun_bright" in means:
        adj = means["adj_bright"] - base
        noun = means["noun_bright"] - base
        print("\nadjectives moved brightness %+.1f · named objects moved it %+.1f" % (adj, noun))
        if noun > adj * 2 and noun > 8:
            print("THE RULE HOLDS: naming bright objects lights a shot; asking for light "
                  "with adjectives does much less. Style strings should be written in "
                  "nouns.")
        elif adj > 8:
            print("THE RULE DOES NOT HOLD HERE: the adjectives worked. The delivered "
                  "slate's darkness came from something else and this file is the "
                  "evidence against the easy answer.")
        else:
            print("INCONCLUSIVE: neither phrasing moved brightness much on this subject. "
                  "Do not write a house rule from this.")
    print("\nimages: %s" % a.out)


if __name__ == "__main__":
    main()
