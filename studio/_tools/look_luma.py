#!/usr/bin/env python3
"""What each look actually does to brightness, measured rather than read off the curve.

The delivered slate came in at mean luma 35.6/255 while the keyframes it was built from
average 131.5 - the films are about a quarter as bright as the pictures they came from,
and neither video engine is responsible (LTX loses 1%, Hunyuan none). That leaves the
deterministic post chain, and the biggest lever in it is the per-beat `look` grade.

Reading the curve strings suggests the night family is the culprit - `night` maps mid-grey
0.5 to 0.28 - but reading a filter graph is how this project has been wrong before. So
this MEASURES: one mid-grey ramp and one real keyframe through every look in the library,
luma in and luma out.

    ramp    a synthetic 0-255 gradient. Says what the transfer curve does with no
            content bias at all.
    frame   a real bright keyframe. Says what it does to the actual material.

The number that matters is `keep` - output luma over input luma. A look designed to read
as night SHOULD be well under 1.0, and that is not a bug; the point of the table is to
find looks that fall far outside their own stated intent, and to give the pipeline a
figure it can warn on before twenty films are delivered two stops down.
"""
import glob
import json
import os
import subprocess
import sys

LOOKS = "studio/looks"
TMP = "/tmp/_looklu"
KEY = os.path.expanduser("~/ComfyUI/input/short_06_water.png")


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def luma(path):
    from PIL import Image
    im = Image.open(path).convert("L").resize((256, 144))
    px = list(im.getdata())
    return 255.0 * sum(px) / (len(px) * 255.0)


def graded(src, vf, dst):
    r = sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vf", vf, "-frames:v", "1", dst)
    if not os.path.exists(dst):
        return None, (r.stderr or "").strip()[-160:]
    return luma(dst), None


def main():
    os.makedirs(TMP, exist_ok=True)
    ramp = os.path.join(TMP, "ramp.png")
    sh("ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
       "gradients=s=512x256:c0=black:c1=white:x0=0:y0=0:x1=512:y1=0",
       "-frames:v", "1", ramp)
    if not os.path.exists(ramp):
        sys.exit("could not build the ramp")

    base_ramp, base_frame = luma(ramp), luma(KEY)
    print("reference:  ramp %.1f   keyframe %.1f\n" % (base_ramp, base_frame))

    rows = []
    for p in sorted(glob.glob(os.path.join(LOOKS, "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        lid = d.get("id") or os.path.splitext(os.path.basename(p))[0]
        vf = d.get("grade")
        if not vf:
            print("  %-16s no grade string" % lid)
            continue
        lr, err1 = graded(ramp, vf, os.path.join(TMP, "r_%s.png" % lid))
        lf, err2 = graded(KEY, vf, os.path.join(TMP, "f_%s.png" % lid))
        if lr is None or lf is None:
            print("  %-16s FILTER FAILED: %s" % (lid, err1 or err2))
            rows.append({"look": lid, "ok": False})
            continue
        rows.append({"look": lid, "ok": True,
                     "ramp": round(lr, 1), "frame": round(lf, 1),
                     "keep_ramp": round(lr / base_ramp, 3),
                     "keep_frame": round(lf / base_frame, 3),
                     "intent": d.get("desc") or d.get("what") or ""})

    good = [r for r in rows if r.get("ok")]
    good.sort(key=lambda r: r["keep_frame"])
    print("%-16s %8s %8s %8s %8s" % ("look", "ramp", "frame", "keepR", "keepF"))
    for r in good:
        flag = ""
        if r["keep_frame"] < 0.45:
            flag = "  <- takes the picture below half brightness"
        elif r["keep_frame"] > 1.15:
            flag = "  <- lifts"
        print("%-16s %8.1f %8.1f %8.3f %8.3f%s"
              % (r["look"], r["ramp"], r["frame"], r["keep_ramp"], r["keep_frame"], flag))

    dark = [r for r in good if r["keep_frame"] < 0.45]
    print("\n%d looks measured · %d take a picture below half its brightness: %s"
          % (len(good), len(dark), ", ".join(r["look"] for r in dark) or "none"))
    json.dump(good, open(os.path.join(LOOKS, "_luma.json"), "w"), indent=1)
    print("-> %s/_luma.json" % LOOKS)


if __name__ == "__main__":
    main()
