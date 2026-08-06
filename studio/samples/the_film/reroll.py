#!/usr/bin/env python3
"""Render N seed candidates per beat of THE COAT, contact-sheet them, promote the pick.

  python3 reroll.py roll  [beat_id ...]   # render candidates + build one sheet per beat
  python3 reroll.py pick  <beat_id> <n>   # promote candidate n into the real keyframe dir

WHY A RIG AND NOT --seed. short.py skips a beat whose keyframe already exists and takes
one film-wide --seed, so "re-roll beat 13 only" is not expressible: you would delete the
file and re-run the whole film at a seed that also moves the nineteen beats you were
happy with. A keyframe on this box costs 3-4 seconds. At that price the right unit of
work is the BEAT, six ways, looked at, one promoted.

IPADAPTER IS OFF HERE and that is the whole reason pass 2 exists. Measured on this box
across three beats at 0.0 / 0.2 / 0.4 / 0.6 against an unchanged LoRA at 0.5:
sheet_anime_terra.png is one full-body Terra in her canonical yellow-spotted dress on a
FLAT GREY FIELD, and short.py feeds it to node 4 at 0.6 on every beat that has a
character. It was injecting its own background and its own dress into every character
shot in the film - the castle great hall bleached to a white corridor, the court gown and
the imperial plate both arriving as the same rainbow smear, her green hair going teal.
Every beat with NO character got weight 0.0 and came back richly painted, which is what
made the split visible: the film had two looks and the divider was whether she was in it.

The LoRA (0.5) and the danbooru name carry identity on their own. TERRA's own
realism_verdict already recommends IPAdapter 0.0; this is that, measured on this film.
"""
import json, os, shutil, sys

sys.path.insert(0, os.path.expanduser("~/shared/comfy-studio/scripts"))
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
import short                                                    # noqa: E402
from comfy import run, set_path                                 # noqa: E402

HOME = os.path.expanduser("~")
FILM = f"{HOME}/shared/comfy-studio/studio/samples/the_film/terra_field_coat.json"
ROLLS = f"{HOME}/ComfyUI/output/claude-generated/12-shorts/coat-rolls"
REAL = f"{HOME}/ComfyUI/output/claude-generated/12-shorts/the-coat/keyframes"
SHEETS = f"{HOME}/shared/comfy-studio/studio/samples/the_film/sheets"
N = 6

film = json.load(open(FILM, encoding="utf-8"))
film["ipadapter_weight"] = 0.0
order = [b["id"] for b in film["beats"]]
beats = {b["id"]: b for b in film["beats"]}


def seeds_for(b):
    """Candidate 0 is always the seed the compiler chose, so the authored take competes."""
    s0 = int(b["seed"])
    return [s0] + [(s0 * 7919 + k * 104729) % 4294967291 for k in range(1, N)]


def roll(ids):
    os.makedirs(SHEETS, exist_ok=True)
    for bid in ids:
        b = beats[bid]
        d = f"{ROLLS}/{bid}"
        os.makedirs(d, exist_ok=True)
        for k, s in enumerate(seeds_for(b)):
            if os.path.exists(f"{d}/c{k}_00001_.png"):
                continue
            wf = short.anime_keyframe(film, dict(b, seed=s), ROLLS, s)
            set_path(wf, "11.inputs.filename_prefix",
                     f"{d.split('output/')[1]}/c{k}")
            run(short.HOST, wf, quiet=True)
        sheet(bid)
        print(f"  sheet {bid}", flush=True)


def sheet(bid):
    d = f"{ROLLS}/{bid}"
    ins, fc = [], []
    for k in range(N):
        ins += ["-i", f"{d}/c{k}_00001_.png"]
        fc.append(f"[{k}:v]scale=620:-2,drawtext=text={k}:fontsize=44:fontcolor=yellow:"
                  f"box=1:boxcolor=black:x=8:y=8[v{k}]")
    fc.append("[v0][v1][v2]hstack=3[r0]")
    fc.append("[v3][v4][v5]hstack=3[r1]")
    fc.append("[r0][r1]vstack=2")
    short.sh("ffmpeg", "-y", "-v", "error", *ins,
             "-filter_complex", ";".join(fc), "-q:v", "3", f"{SHEETS}/{bid}.jpg")


def pick(bid, k):
    src = f"{ROLLS}/{bid}/c{int(k)}_00001_.png"
    if not os.path.exists(src):
        sys.exit(f"no candidate {k} for {bid}")
    os.makedirs(REAL, exist_ok=True)
    shutil.copy(src, f"{REAL}/{bid}_00001_.png")
    print(f"{bid} <- c{k}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "roll":
        roll(sys.argv[2:] or order)
    elif cmd == "pick":
        for pair in sys.argv[2:]:
            b, k = pair.rsplit(":", 1)
            pick(b, k)
    else:
        sys.exit(__doc__)
