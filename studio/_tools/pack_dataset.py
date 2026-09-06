#!/usr/bin/env python3
"""Build a LoRA training set from a foundry character pack.

The pack already holds what a character LoRA wants: a turnaround, a face turnaround,
expressions and a full body, all of one person, all made from the same description.  What it
does not hold is captions, and captions are the whole game.

THE CAPTION RULE, learned expensively on TERRA and written into train_character.py: whatever
a caption does not NAME gets absorbed into the trigger.  TERRA was captioned "terra, front"
and the trigger came to mean the woman AND her gold dress AND the flat grey wall behind her,
so her costumes would not change and raising her strength greyed out the scenery.  So every
caption here names the trigger, the view, what she is wearing and what is behind her - the
things that must stay changeable.

    python3 make_dataset.py bai-liwen            -> ~/ComfyUI/input/bailiwen_train/
"""
import json
import os
import shutil
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio/studio")
COMFY = os.path.expanduser("~/ComfyUI")
CHARS = os.path.join(ROOT, "foundry", "characters")

VIEW_WORDS = {
    "base_portrait": "a head and shoulders portrait, facing the camera",
    "base_fullbody": "full body, standing, facing the camera",
    "turn_front": "full body, standing, facing the camera",
    "turn_front_three_quarter": "full body, standing, turned three quarters",
    "turn_side": "full body, standing, in profile from the side",
    "turn_back_three_quarter": "full body, standing, seen from behind at an angle",
    "turn_back": "full body, standing, seen from directly behind",
    "face_front": "a close portrait of the face, facing the camera",
    "face_three_quarter": "a close portrait of the face, turned three quarters",
    "face_side": "a close portrait of the face, in profile",
    "expr_neutral": "a close portrait, neutral expression",
    "expr_joy": "a close portrait, smiling",
    "expr_anger": "a close portrait, angry",
    "expr_fear": "a close portrait, afraid",
    "expr_sorrow": "a close portrait, sad",
    "expr_surprise": "a close portrait, surprised",
    "pres_wide": "full body, standing at ease, even daylight",
    "pres_hero": "upper body, dramatic side lighting",
}
SKIP = ("pres_low", "pres_low_full")     # a deliberately odd angle is not a good teacher


def build(cid, trigger=None, extra_background="plain neutral background"):
    d = os.path.join(CHARS, cid)
    a = json.load(open(os.path.join(d, "asset.json"), encoding="utf-8"))
    trigger = trigger or cid.replace("-", "")
    comp = a.get("compiled") or {}
    wear = (comp.get("wear_clause") or "").strip().rstrip(".")
    tags = (comp.get("tags") or "").strip()
    out = os.path.join(COMFY, "input", "%s_train" % trigger)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    n = 0
    for key, view_words in VIEW_WORDS.items():
        src = os.path.join(d, key + ".png")
        if key in SKIP or not os.path.exists(src):
            continue
        shutil.copy2(src, os.path.join(out, "%s_%s.png" % (trigger, key)))
        bits = [trigger, view_words]
        if wear:
            bits.append(wear)
        bits.append(extra_background)
        open(os.path.join(out, "%s_%s.txt" % (trigger, key)), "w", encoding="utf-8").write(
            ", ".join(bits))
        n += 1
    print("%s -> %s" % (cid, out))
    print("  %d image and caption pairs" % n)
    print("  trigger: %r" % trigger)
    print("  a caption reads: %s" % ", ".join([trigger, VIEW_WORDS["turn_front"], wear, extra_background])[:190])
    if not wear:
        print("  ! this pack has no wear clause - whatever it is wearing will be absorbed "
              "into the trigger and will not be changeable later")
    print("  tags on the pack (not used as captions, kept for reference): %s" % tags[:120])
    return out, n


if __name__ == "__main__":
    for cid in sys.argv[1:] or ["bai-liwen"]:
        build(cid)
