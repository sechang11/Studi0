#!/usr/bin/env python3
"""Re-roll ONE beat's LTX clip at a chosen noise seed, leaving the other nineteen alone.

  python3 reclip.py <beat_id> <seed> [<beat_id> <seed> ...]

short.py's clips() takes one film-wide --seed and derives each beat's noise seed as
seed + i*13, and it skips a beat whose clip already exists. So "re-roll beat 6" is only
expressible as "delete beat 6 and re-run the whole film at a seed that also moves any
other beat you happened to delete" - and each LTX generation here costs ~30s against a
shared GPU. This does the one thing that is actually wanted.

TWO CLIPS NEEDED IT, and both failures are the video model filling a room rather than
drifting:

  * ii_decided_the_hall_00 - the keyframe is an empty great hall. By 0.8s TWO MEN IN
    SUITS walk in carrying a table, and by 3.0s they are sitting at it facing each other.
    The whole premise of act two is that we never see who decides; LTX cast them. This is
    the same failure short.py's own LEGACY_HOLD comment records ("'Nobody moves.' drew one
    into an empty corridor") and it is worse here because the shipped establish slice is
    0.12-4.32s, which contains the arrival, the table and the sitting down.

  * iv_chosen_she_asks_00 - hand_reach lands as an anime V-sign with fingers the height
    of her head, from 3.8s, inside the speak slice 0.3-4.62s.

The keyframe is not touched: this re-rolls the video noise only, so the picture that was
chosen from twelve candidates stays chosen.
"""
import json, math, os, shutil, sys

sys.path.insert(0, os.path.expanduser("~/shared/comfy-studio/scripts"))
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
import short                                                    # noqa: E402
from comfy import set_path                                      # noqa: E402
from epic import load_wf, expand, submit, wait_all, COMFY        # noqa: E402

H = os.path.expanduser("~")
OUT = f"{H}/ComfyUI/output/claude-generated/12-shorts/the-coat"
REL = "claude-generated/12-shorts/the-coat"
film = json.load(open(f"{H}/shared/comfy-studio/studio/samples/the_film/"
                      "terra_field_coat.json", encoding="utf-8"))
beats = {b["id"]: b for b in film["beats"]}

args = sys.argv[1:]
pids = []
for bid, seed in zip(args[0::2], args[1::2]):
    b = beats[bid]
    kf = f"{OUT}/keyframes/{bid}_00001_.png"
    staged = f"short_{bid}.png"
    shutil.copy(kf, f"{COMFY}/input/{staged}")
    secs = float(b.get("clip_secs", 4))
    length = max(9, int(math.ceil(secs * short.FPS / 8)) * 8 + 1)
    wf = load_wf("12_ltx23_i2v_audio.json")
    set_path(wf, "8.inputs.image", staged)
    set_path(wf, "10.inputs.text",
             expand(short.motion_of(b), film.get("characters", {})))
    set_path(wf, "20.inputs.width", short.VID[0])
    set_path(wf, "20.inputs.height", short.VID[1])
    set_path(wf, "20.inputs.length", length)
    set_path(wf, "21.inputs.frames_number", length)
    set_path(wf, "32.inputs.noise_seed", int(seed))
    set_path(wf, "43.inputs.filename_prefix", f"{REL}/reclip/{bid}__s{seed}")
    print(f"  > {bid} seed {seed}", flush=True)
    pids.append(submit(wf))
wait_all(pids, "reclip")
print("done")
