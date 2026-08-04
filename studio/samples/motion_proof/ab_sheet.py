#!/usr/bin/env python3
"""ab_sheet.py - NEW motion (top row) against the RETIRED CONSTANT (bottom row).

Same keyframe, same seed, same length. The only difference between the two rows of each
sheet is the string at node 10 of the LTX workflow.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
from epic import COMFY                       # noqa: E402

OUT = f"{COMFY}/output/claude-generated/12-shorts/motion-proof"
FILM = json.load(open(os.path.join(ROOT, "studio", "movies", "motion-proof.json"),
                     encoding="utf-8"))
DEST = f"{HERE}/ab"
os.makedirs(DEST, exist_ok=True)
PICKS = [0, 32, 64, 96]


def row(src, dst):
    sel = "+".join("eq(n\\,%d)" % p for p in PICKS)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vf",
                    "select='%s',scale=480:-1,tile=%dx1" % (sel, len(PICKS)),
                    "-frames:v", "1", "-fps_mode", "passthrough", dst], check=True)


for i in [int(x) for x in sys.argv[1:]] or [0, 1, 2, 6, 8, 10]:
    b = FILM["beats"][i]
    new, old = f"{OUT}/clips/{b['id']}_00001_.mp4", f"{OUT}/_old/{b['id']}_00001_.mp4"
    if not (os.path.exists(new) and os.path.exists(old)):
        print("skip", i, b["id"])
        continue
    row(new, f"{HERE}/_rn.png")
    row(old, f"{HERE}/_ro.png")
    short = b["id"].replace("after_the_party_", "")
    dst = f"{DEST}/{i:02d}_{short}.png"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{HERE}/_rn.png",
                    "-i", f"{HERE}/_ro.png", "-filter_complex",
                    "[0:v][1:v]vstack=2", dst], check=True)
    print("%-26s TOP new: %s" % (short, b["motion"]))
    print("%-26s BOT old: Slow deliberate movement only." % "")
print("\n-> %s" % DEST)
