#!/usr/bin/env python3
"""Second re-roll pass: six more seeds for the six beats that failed all six of the first.

Five of these six are the film's "no humans" object inserts, and they share one failure:
the shot line names an object that never arrives. Six seeds each produced a gauntlet 0/6,
a sash 1/6 (a red band, arguably), a coat on a rail 0/6, and a pair of hands 0/6. The
sixth, the closing moor, fails differently - the author's free-text place dropped the
moorland card's `no trees`, and the model gave a wood 6/6.

More seeds is the only lever I own here: the prompt lives in the .movie, which is not
mine to edit. Twelve candidates is enough to say whether the object is a coin flip or is
absent from the distribution, which is the difference between "re-roll it" and "rewrite
the shot line", and that is the answer the author needs.
"""
import json, os, sys

sys.path.insert(0, os.path.expanduser("~/shared/comfy-studio/scripts"))
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
import short                                                    # noqa: E402
from comfy import run, set_path                                 # noqa: E402
sys.path.insert(0, os.path.expanduser("~/shared/comfy-studio/studio/samples/the_film"))
import reroll                                                   # noqa: E402

WANT = ["i_issued_dressed_00", "i_issued_dressed_02", "i_issued_the_gauntlet_00",
        "iii_the_road_the_sash_00", "iv_chosen_the_rail_00",
        "iv_chosen_the_moor_again_00"]

for bid in WANT:
    b = reroll.beats[bid]
    d = f"{reroll.ROLLS}/{bid}"
    s0 = int(b["seed"])
    for k in range(6, 12):
        if os.path.exists(f"{d}/c{k}_00001_.png"):
            continue
        s = (s0 * 32749 + k * 15485863) % 4294967291
        wf = short.anime_keyframe(reroll.film, dict(b, seed=s), reroll.ROLLS, s)
        set_path(wf, "11.inputs.filename_prefix", f"{d.split('output/')[1]}/c{k}")
        run(short.HOST, wf, quiet=True)
    ins, fc = [], []
    for i, k in enumerate(range(6, 12)):
        ins += ["-i", f"{d}/c{k}_00001_.png"]
        fc.append(f"[{i}:v]scale=620:-2,drawtext=text={k}:fontsize=44:fontcolor=yellow:"
                  f"box=1:boxcolor=black:x=8:y=8[v{i}]")
    fc += ["[v0][v1][v2]hstack=3[r0]", "[v3][v4][v5]hstack=3[r1]", "[r0][r1]vstack=2"]
    short.sh("ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(fc),
             "-q:v", "3", f"{reroll.SHEETS}/{bid}__b.jpg")
    print(f"  sheet2 {bid}", flush=True)
print("done")
