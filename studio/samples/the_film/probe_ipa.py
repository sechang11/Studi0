#!/usr/bin/env python3
"""IPAdapter weight A/B on three character beats of THE COAT.

Pass 1 rendered every beat WITH a character flat, pastel, and wearing a rainbow smear
regardless of the costume asked for, while every beat WITHOUT a character came back
richly painted with its real location. The only thing that differs between those two
groups in short.py's anime path is node 4's IPAdapter weight: 0.6 when b["ref"] is set,
0.0 when it is not.

sheet_anime_terra.png is a single full-body Terra in the canonical yellow-spotted dress
and red cape, standing on a FLAT GREY BACKGROUND. At 0.6 that sheet is injecting its
background and its dress into every character shot in the film - which is why the court
gown and the imperial plate both arrive as the same rainbow.

This renders three beats at four weights against the LoRA (0.5, unchanged) so the choice
is made from pixels. Nothing in studio/movies/ or scripts/ is touched: it calls short.py's
own anime_keyframe() so the graph is byte-identical to the real render apart from node 4.
"""
import json, os, sys

sys.path.insert(0, os.path.expanduser("~/shared/comfy-studio/scripts"))
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
import short                                                    # noqa: E402
from comfy import run, set_path                                 # noqa: E402

FILM = os.path.expanduser(
    "~/shared/comfy-studio/studio/samples/the_film/terra_field_coat.json")
OUT = os.path.expanduser("~/ComfyUI/output/claude-generated/12-shorts/coat-probe")
WANT = ["ii_decided_decided_00",        # court gown, medium, in a great hall
        "iii_the_road_the_ford_00",     # traveller rung 3, the shot that came back broken
        "iv_chosen_she_walks_00"]       # field coat, the shot that half worked
WEIGHTS = [0.0, 0.2, 0.4, 0.6]

film = json.load(open(FILM, encoding="utf-8"))
beats = {b["id"]: b for b in film["beats"]}
os.makedirs(f"{OUT}/keyframes", exist_ok=True)

for w in WEIGHTS:
    f2 = dict(film, ipadapter_weight=w)
    for bid in WANT:
        b = beats[bid]
        tag = f"{bid}__ipa{int(w * 10):02d}"
        if os.path.exists(f"{OUT}/keyframes/{tag}_00001_.png"):
            continue
        wf = short.anime_keyframe(f2, b, OUT, int(b["seed"]))
        set_path(wf, "11.inputs.filename_prefix",
                 f"{OUT.split('output/')[1]}/keyframes/{tag}")
        print(f"  > {tag}", flush=True)
        run(short.HOST, wf, quiet=True)
print("done")
