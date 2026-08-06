#!/usr/bin/env python3
"""The picture cut of THE COAT: every beat sliced and graded exactly as short.py would,
concatenated in beat order, no audio.

short.py's `cut` stage cannot run yet - the voice and music stages have not been rendered
into this film's output tree, and dialogue and score are a different task. But the picture
is finished, and a picture cut is the only artefact that answers the question the whole
render exists to answer: does it hold together when you watch it.

It uses short.py's own expand_template() and make_cut(), so the slice points, the per-beat
`look` grade and the camera fx are byte-identical to what the finished film will carry. The
only thing missing is sound and the vertical composite.
"""
import json, os, subprocess, sys

sys.path.insert(0, os.path.expanduser("~/shared/comfy-studio/scripts"))
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
import short                                                     # noqa: E402
from scene_templates import expand as expand_template            # noqa: E402

H = os.path.expanduser("~")
OUT = f"{H}/ComfyUI/output/claude-generated/12-shorts/the-coat"
WORK = f"{OUT}/_work/picture"
D = f"{H}/shared/comfy-studio/studio/samples/the_film"
os.makedirs(WORK, exist_ok=True)
film = json.load(open(f"{D}/terra_field_coat.json", encoding="utf-8"))

MOVES = ("punch", "push", "pull", "pan_l", "pan_r", "tilt_u", "tilt_d", "handheld")
pieces, t = [], 0.0
for i, b in enumerate(film["beats"], 1):
    src = f"{OUT}/clips/{b['id']}_00001_.mp4"
    cuts, _ = expand_template(b, float(b.get("clip_secs", 4)))
    cam = b.get("camera")
    for ci, c in enumerate(cuts):
        if cam:
            c = dict(c, fx=[f for f in c["fx"] if f not in MOVES]
                         + ([] if cam == "static" else [cam]))
        p = f"{WORK}/{len(pieces):04d}_{b['id']}_{ci}.mp4"
        short.make_cut(src, float(c["at"]), float(c["len"]), c.get("fx", []), p,
                       seed=len(pieces), grade=b.get("grade"))
        pieces.append(p)
        t += short.dur(p)
    print(f"{i:2d} {b['id']:32s} {len(cuts)} shot(s)  running {t:5.1f}s", flush=True)

lst = f"{WORK}/list.txt"
with open(lst, "w", encoding="utf-8") as f:
    for p in pieces:
        f.write(f"file '{p}'\n")
final = f"{D}/THE_COAT_picture.mp4"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                "-i", lst, "-c", "copy", final], check=True)
print(f"\n{len(pieces)} shots, {short.dur(final):.1f}s -> {final}")
