#!/usr/bin/env python3
"""Caption a training set the way the caption rule says to.

A caption is a subtraction: whatever it names stays separable, whatever it omits is welded
onto the trigger.  A character pack that never specified clothing has no words for what its
figure is wearing, so those words have to be found - and the studio has a vision model.

The ask is deliberately narrow.  It must NOT describe the face, hair, build or age: those are
the things that should become the trigger.  It describes only the garments and the ground
behind them, which are the things a director will want to change later.

    python3 caption_wear.py bailiwen_train
"""
import glob
import os
import re
import shutil
import sys
import time

ROOT = os.path.expanduser("~/shared/comfy-studio")
sys.path.insert(0, os.path.join(ROOT, "studio", "_tools"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from epic import COMFY, HOST, load_wf, run  # noqa: E402
from comfy import set_path  # noqa: E402

WEAR_ASK = (
    "List only the CLOTHING this figure is wearing and the BACKGROUND behind them. "
    "Do not mention their face, hair, eyes, skin, age, build, sex or expression. "
    "Answer as a short comma-separated list of noun phrases and nothing else, "
    "for example: 'a white linen shirt, dark trousers, a plain grey studio background'.")

BANNED = re.compile(r"\b(hair|eyes?|face|facial|skin|young|woman|man|girl|boy|female|male|"
                    r"slender|slim|build|expression|smil\w*|age|twenties|teen\w*|pale|"
                    r"fair|complexion|figure|person|individual|character)\b", re.I)


def ask(staged, prompt):
    wf = load_wf("30_vision_caption.json")
    set_path(wf, "2.inputs.image", staged)
    set_path(wf, "3.inputs.prompt", prompt)
    stamp = "wear_%d" % (time.time() * 1000 % 10 ** 8)
    wf["90"] = {"class_type": "SaveText",
                "inputs": {"text": ["3", 0], "filename_prefix": stamp, "format": "txt"}}
    run(HOST, wf, quiet=True)
    hits = sorted(glob.glob(os.path.join(COMFY, "output", "**", stamp + "*"), recursive=True))
    return open(hits[-1], encoding="utf-8", errors="replace").read().strip() if hits else ""


def clean(text):
    """keep the phrases that are about clothes and ground, drop anything about the person"""
    text = re.sub(r"^[^:]{0,60}:", "", text.strip(), count=1)          # a preamble
    text = text.replace("\n", ", ")
    parts = [p.strip(" .;-") for p in text.split(",")]
    keep = []
    for p in parts:
        if not p or len(p) > 60:
            continue
        if BANNED.search(p):
            continue
        p = re.sub(r"^(and|with|wearing)\s+", "", p, flags=re.I).strip()
        if p and p.lower() not in [k.lower() for k in keep]:
            keep.append(p)
    return ", ".join(keep[:6])


def caption_set(folder, trigger=None):
    d = os.path.join(COMFY, "input", folder)
    trigger = trigger or folder.replace("_train", "")
    pngs = sorted(f for f in os.listdir(d) if f.endswith(".png"))
    print("%s: %d images" % (folder, len(pngs)), flush=True)
    for i, fn in enumerate(pngs):
        view = ""
        txt_p = os.path.join(d, fn[:-4] + ".txt")
        if os.path.exists(txt_p):
            old = open(txt_p, encoding="utf-8").read()
            bits = [b.strip() for b in old.split(",")]
            view = ", ".join(b for b in bits[1:] if b and "background" not in b.lower())
        staged = re.sub(r"[^A-Za-z0-9._-]", "_", "wearcap_%s" % fn)
        shutil.copy(os.path.join(d, fn), os.path.join(COMFY, "input", staged))
        try:
            wear = clean(ask(staged, WEAR_ASK))
        except Exception as e:
            print("  ! %s: %s" % (fn, str(e)[:70]), flush=True)
            wear = ""
        cap = ", ".join([x for x in (trigger, view, wear) if x])
        open(txt_p, "w", encoding="utf-8").write(cap)
        print("  %-40s %s" % (fn[:40], cap[:110]), flush=True)
    return d


if __name__ == "__main__":
    for folder in sys.argv[1:] or ["bailiwen_train"]:
        caption_set(folder)
