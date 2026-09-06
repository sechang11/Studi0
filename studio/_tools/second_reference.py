#!/usr/bin/env python3
"""Does the adoption verdict depend on which picture of the character it is compared against?

Looking at the renders: on Terra and the shrine keeper the number and the eye agree, and the
shrine keeper's reference-path render is a plainly younger person wearing the same glasses -
exactly the failure a trained face should fix, and it did.  On jin the number says tie (0.842
to 0.834, declined) and the eye says the LoRA is closer: the reference path made a rounder,
younger, softer character while the LoRA kept the face structure, the green eyes and the teal
in the hair.

One confound is cheap to test.  Every verdict this block was scored against a single picture -
`base_portrait.png` - and a pack has several views.  If the ordering between the two routes
holds against a second view, the gate's verdicts stand and jin is simply close.  If it flips,
then some of these decisions were made about a camera angle rather than about a face.

No GPU: the renders already exist, this only scores them again.
"""
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
TOOLS = os.path.join(ROOT, "studio", "_tools")
sys.path.insert(0, TOOLS)
import headbox as HB  # noqa: E402

PY = os.path.expanduser("~/ComfyUI/venv/bin/python")
CHARS = os.path.join(ROOT, "studio", "foundry", "characters")
OUT = os.path.expanduser("~/ComfyUI/output/claude-generated/packlora")
# preference order for a second opinion: a front face beats a turnaround beats anything
SECOND = ("face_front", "turn_front", "base_fullbody", "expr_neutral", "face_three_quarter")

PACKS = {"bai-liwen": "bailiwen", "renji": "renji", "terra": "terra", "jin": "jin",
         "jin-elder": "jinelder", "the-ferryman": "theferryman",
         "old-shrine-keeper": "oldshrinekeeper", "kite-seller": "kiteseller"}


def views(pack):
    d = os.path.join(CHARS, pack)
    have = {os.path.splitext(os.path.basename(p))[0]: p for p in glob.glob(os.path.join(d, "*.png"))}
    for k in SECOND:
        if k in have:
            return k, have[k]
    return None, None


def main():
    jobs, seen = [], {}
    for pack, trig in PACKS.items():
        name, ref = views(pack)
        if not ref:
            continue
        for route in ("ipa", "lora"):
            p = os.path.join(OUT, "%s_%s_00001_.png" % (trig, route))
            if not os.path.exists(p):
                continue
            # deliberately no head box: these renders are close portraits, and headbox
            # refuses a figure that touches the top of the frame rather than returning a
            # forehead.  The whole frame IS the head crop here.
            box = None
            jid = "%s|%s" % (pack, route)
            jobs.append({"id": jid, "portrait": ref, "still": p, "box": box, "close": True})
            seen[pack] = name
    jp = "/tmp/second_ref.json"
    json.dump(jobs, open(jp, "w"))
    r = subprocess.run([PY, os.path.join(TOOLS, "identity.py"), jp], capture_output=True,
                       text=True, cwd=os.path.expanduser("~/ComfyUI"))
    sc = {}
    for line in r.stdout.splitlines():
        try:
            d = json.loads(line)
            sc[d["id"]] = d.get("start")
        except Exception:
            pass
    print("%-18s %-14s %9s %9s   %s" % ("pack", "second view", "reference", "LoRA", "says"))
    rows = []
    for pack in sorted(seen):
        a, b = sc.get("%s|ipa" % pack), sc.get("%s|lora" % pack)
        if a is None or b is None:
            print("%-18s %-14s %9s %9s   could not score" % (pack, seen[pack], "-", "-"))
            continue
        rows.append({"pack": pack, "view": seen[pack], "reference": round(a, 3),
                     "lora": round(b, 3), "lora_wins": b > a})
        print("%-18s %-14s %9.3f %9.3f   %s"
              % (pack, seen[pack], a, b, "the LoRA" if b > a else "the reference path"))
    if rows:
        json.dump(rows, open(os.path.join(ROOT, "studio", "pack_lora_second_view.json"), "w"),
                  indent=1)
    print("SECOND VIEW DONE")


if __name__ == "__main__":
    main()
