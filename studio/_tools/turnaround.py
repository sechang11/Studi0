#!/usr/bin/env python3
"""One picture of a person becomes many consistent views of that same person.

    python3 studio/_tools/turnaround.py VIRO                    # from their sheet
    python3 studio/_tools/turnaround.py VIRO --views 12
    python3 studio/_tools/turnaround.py --image some.png --out /tmp/set

WHY THIS IS THE KEYSTONE

Everything about character consistency in this project has been a workaround for not
having one. Tags describe someone; they do not make the same face twice. IPAdapter
refines a face from a single reference - and a measured weight sweep found the character
was "already recognisable at ZERO", i.e. the single sheet was carrying much less than
assumed. A character that is a PROMPT can never be reliably the same person.

The multiple-angles LoRA re-poses the SAME person rather than generating a new one that
matches the description. That gives two things at once:

  a real reference sheet   many views instead of one, which is a far stronger identity
                           lock for the paths that use a reference
  a training set           20-40 consistent views of one person is exactly what a
                           character LoRA needs, and producing that by hand is the reason
                           character training normally never happens

Views are authored rather than random. A training set wants ANGLES and EXPRESSIONS of a
neutral subject - not costumes, not scenes, not lighting. Anything the set varies that is
not the person is something the LoRA will learn as part of the person.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, COMFY, HOST   # noqa: E402

WF = "32_qwen_turnaround.json"
CAST = os.path.join(STUDIO, "characters")
OUT = os.path.join(STUDIO, "samples", "cast")

# EVERY PROMPT STATES ITS FRAMING, and all but the last two state the same one.
#
# The first version left framing to the model and it drifted: "side view ... full profile"
# was read as FULL BODY, so those two views zoomed out and lost the costume entirely -
# green tunic instead of the teal jersey - while the head-and-shoulders views held
# identity perfectly. Two things varied at once and only one was intended.
#
# That matters more here than in a comparison panel. A LoRA learns whatever the set holds
# CONSTANT as "the character" and whatever it varies as "not the character". A set that is
# half close-up and half full-body teaches a muddle, and the costume changing across the
# set teaches that the costume is optional.
#
# So: framing is written into every line. The two deliberate framing changes are named as
# such and come last, where they are a small minority of the set.
FRAME = "head and shoulders, waist up"
VIEWS = [
    ("front",        f"front view of the same person, facing the camera directly, neutral expression, {FRAME}"),
    ("three_quarter",f"three-quarter view of the same person, head turned slightly to their left, {FRAME}"),
    ("side_left",    f"the same person's head turned to face left, profile of the face, {FRAME}"),
    ("side_right",   f"the same person's head turned to face right, profile of the face, {FRAME}"),
    ("back",         f"the same person seen from behind, back of the head, head turned slightly, {FRAME}"),
    ("looking_up",   f"the same person looking upward, chin raised, neutral expression, {FRAME}"),
    ("looking_down", f"the same person looking downward, chin lowered, eyes cast down, {FRAME}"),
    ("low_angle",    f"the same person seen from a low camera angle looking up at them, neutral expression, {FRAME}"),
    ("high_angle",   f"the same person seen from a high camera angle looking down at them, neutral expression, {FRAME}"),
    ("smiling",      f"the same person smiling, front view, {FRAME}"),
    ("angry",        f"the same person with a hard angry expression, brows drawn down, front view, {FRAME}"),
    ("surprised",    f"the same person surprised, eyes wide, mouth slightly open, front view, {FRAME}"),
    ("shouting",     f"the same person shouting, mouth open wide, front view, {FRAME}"),
    ("eyes_closed",  f"the same person with eyes closed, calm, front view, {FRAME}"),
    # the only two that change framing on purpose, kept to a minority of the set
    ("close",        "an extreme close-up of the same person's face only, front view, neutral expression"),
    ("full_body",    "the same person standing, full body visible head to feet, front view, plain background"),
]


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def stage(path):
    """ComfyUI can only LoadImage from its own input dir."""
    dst = os.path.join(COMFY, "input", "turnaround_src.png")
    if os.path.abspath(path) != os.path.abspath(dst):
        sh("cp", path, dst)
    return "turnaround_src.png"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("character", nargs="?", help="a character id from studio/characters/")
    ap.add_argument("--image", help="use this image instead of the character's sheet")
    ap.add_argument("--out", help="write here instead of samples/cast/<id>/")
    ap.add_argument("--views", type=int, default=len(VIEWS))
    ap.add_argument("--strength", type=float, help="override the angles LoRA strength")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    if a.image:
        src, name = a.image, os.path.splitext(os.path.basename(a.image))[0]
    elif a.character:
        p = os.path.join(CAST, a.character + ".json")
        if not os.path.exists(p):
            have = sorted(f[:-5] for f in os.listdir(CAST) if f.endswith(".json"))
            raise SystemExit(f"unknown character {a.character!r}\n  have: {', '.join(have)}")
        card = json.load(open(p, encoding="utf-8"))
        if not card.get("sheet"):
            raise SystemExit(f"{a.character} has no `sheet` to turn around.\n"
                             f"  Generate one first, or pass --image.")
        src = os.path.join(COMFY, "input", card["sheet"])
        name = a.character
    else:
        raise SystemExit("give a character id or --image")

    if not os.path.isfile(src):
        raise SystemExit(f"source image not found: {src}")

    out = a.out or os.path.join(OUT, name)
    os.makedirs(out, exist_ok=True)
    staged = stage(src)
    views = VIEWS[:max(1, a.views)]
    print("turning around %s from %s" % (name, os.path.basename(src)))
    print("  %d views -> %s" % (len(views), out))

    made = skipped = failed = 0
    for i, (vid, prompt) in enumerate(views):
        dst = os.path.join(out, "%02d_%s.png" % (i, vid))
        if os.path.exists(dst) and not a.force:
            skipped += 1
            continue
        wf = load_wf(WF)
        set_path(wf, "7.inputs.image", staged)
        set_path(wf, "10.inputs.prompt", prompt)
        set_path(wf, "15.inputs.seed", 1100 + i)
        if a.strength is not None:
            set_path(wf, "40.inputs.strength_model", float(a.strength))
        set_path(wf, "17.inputs.filename_prefix",
                 "claude-generated/studio_cast/%s_%02d_%s" % (name, i, vid))
        try:
            _, outs = run(HOST, wf, quiet=True)
        except Exception as e:
            print("  %-14s FAILED %s" % (vid, str(e)[:90]))
            failed += 1
            continue
        if not outs:
            failed += 1
            continue
        if not ensure_local(outs[0], dst, required=False):
            failed += 1
            continue
        made += 1
        print("  %-14s %6.0f KB" % (vid, os.path.getsize(dst) / 1024), flush=True)

    # A caption per image. LoadImageTextDataSetFromFolder pairs <name>.png with
    # <name>.txt, and those captions are what the LoRA trains against.
    #
    # The caption names the TRIGGER (the character id) and the view, and nothing else.
    # Anything written in every caption becomes part of what the trigger means, so
    # describing hair or clothing here would teach the model that those are separate
    # from the character rather than part of it - the opposite of what is wanted.
    if made or skipped:
        for i, (vid, _) in enumerate(views):
            img = os.path.join(out, "%02d_%s.png" % (i, vid))
            if not os.path.exists(img):
                continue
            with open(img[:-4] + ".txt", "w", encoding="utf-8") as f:
                f.write("%s, %s\n" % (name.lower(), vid.replace("_", " ")))

    # Stage a copy where the trainer can actually see it. LoadImageTextDataSetFromFolder
    # offers a dropdown of directories under ComfyUI/input, so a dataset anywhere else is
    # invisible to it no matter how well formed.
    train = os.path.join(COMFY, "input", name.lower() + "_train")
    os.makedirs(train, exist_ok=True)
    n = 0
    for fn in sorted(os.listdir(out)):
        if fn.endswith((".png", ".txt")):
            sh("cp", os.path.join(out, fn), os.path.join(train, fn))
            n += 1
    print("\n%d rendered, %d already there, %d failed" % (made, skipped, failed))
    print("browsable at  %s" % out)
    print("trainable at  %s  (%d files, %d pairs)" % (train, n, n // 2))
    print("\nnext:  python3 studio/_tools/train_character.py %s" % name)


if __name__ == "__main__":
    main()
