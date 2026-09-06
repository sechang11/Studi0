#!/usr/bin/env python3
"""How hard should a trained face be applied?

0.85 is in two files in this repo and nobody measured it.  It is the number people put in
tutorials, which is the same standing as a prompt written from memory - exactly the kind of
unmeasured constant this project spends its time replacing.

Two questions, and they are different.  Turned up, does the face get closer to the pack
portrait?  And turned up, does the character stop being able to do anything but the pose it
was trained in - the thing a LoRA is actually infamous for?  The first is the identity score
against the portrait.  The second needs a second reading: the same strength asked for a
distinctly different framing, scored against the portrait too, because a LoRA that has taken
over will drag every request back to the training crop and score suspiciously well while
ignoring what was asked for.

So: for each strength, one close portrait and one three-quarter turn away from camera.  If the
close portrait keeps climbing while the turn stops moving, the extra strength is being spent
on rigidity rather than likeness, and the right number is where the two stop agreeing.

    python3 lora_strength.py terra renji
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
TOOLS = os.path.join(ROOT, "studio", "_tools")
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from comfy import set_path  # noqa: E402
from epic import COMFY, load_wf, submit  # noqa: E402
import headbox as HB  # noqa: E402
import pack_lora as PL  # noqa: E402

CHARS = os.path.join(ROOT, "studio", "foundry", "characters")
PY = os.path.expanduser("~/ComfyUI/venv/bin/python")
STRENGTHS = (0.55, 0.70, 0.85, 1.00)
# the second ask: a framing the training crops did not contain
POSES = {"close": "a close portrait of the face, facing the camera, plain neutral background",
         "turn": "full body, standing, seen from three quarters behind, turned away from the "
                 "camera, looking back over one shoulder, a wide empty street"}


def render(pack, trigger, tags, lora, strength, pose, seed):
    wf = load_wf("22_anime_kf_ipadapter.json")
    ref = "packstr_ref_%s.png" % trigger
    shutil.copy(os.path.join(CHARS, pack, "base_portrait.png"), os.path.join(COMFY, "input", ref))
    set_path(wf, "2.inputs.image", ref)
    set_path(wf, "4.inputs.weight", 0.0)
    set_path(wf, "5.inputs.text", "%s, %s, %s, masterpiece, best quality"
             % (trigger, tags, POSES[pose]))
    set_path(wf, "6.inputs.text", PL.NEG_M if "1girl" in tags else PL.NEG_F)
    for n in ("7", "10"):
        set_path(wf, "%s.inputs.width" % n, 896)
        set_path(wf, "%s.inputs.height" % n, 1152)
    set_path(wf, "8.inputs.seed", seed)
    pre = "claude-generated/packstr/%s_%s_%03d_%d" % (trigger, pose, int(strength * 100), seed)
    set_path(wf, "11.inputs.filename_prefix", pre)
    wf["packlora"] = {"class_type": "LoraLoader",
                      "inputs": {"lora_name": lora, "strength_model": strength,
                                 "strength_clip": strength, "model": ["1", 0], "clip": ["1", 1]}}
    set_path(wf, "3.inputs.model", ["packlora", 0])
    set_path(wf, "5.inputs.clip", ["packlora", 1])
    set_path(wf, "6.inputs.clip", ["packlora", 1])
    PL.wait(submit(wf))
    g = sorted(glob.glob(os.path.join(COMFY, "output", pre + "*.png")), key=os.path.getmtime)
    return g[-1] if g else None


def score_many(pack, files):
    """one identity.py call for the whole sweep - it loads CLIP once"""
    port = os.path.join(CHARS, pack, "base_portrait.png")
    jobs = []
    for tag, p in files.items():
        if not p:
            continue
        try:
            box = HB.head_box(p)
        except Exception:
            box = None
        jobs.append({"id": tag, "portrait": port, "still": p, "box": box, "close": True})
    jp = "/tmp/packstr_%s.json" % pack
    json.dump(jobs, open(jp, "w"))
    r = subprocess.run([PY, os.path.join(TOOLS, "identity.py"), jp], capture_output=True,
                       text=True, cwd=os.path.expanduser("~/ComfyUI"))
    out = {}
    for line in r.stdout.splitlines():
        try:
            d = json.loads(line)
            out[d["id"]] = d.get("start")
        except Exception:
            pass
    return out


def sweep(pack, seeds):
    a = json.load(open(os.path.join(CHARS, pack, "asset.json"), encoding="utf-8"))
    lo = a.get("lora") or {}
    if not lo.get("file"):
        print("%s: no trained face" % pack)
        return None
    trigger = lo.get("trigger") or pack.replace("-", "")
    tags = (a.get("compiled") or {}).get("tags") or "1girl, solo"
    tags = ", ".join(t.strip() for t in tags.split(",")[:6] if t.strip())
    print("\n=== %s ===" % pack, flush=True)
    files = {}
    for st in STRENGTHS:
        for pose in POSES:
            for sd in seeds:
                files["%s|%.2f|%d" % (pose, st, sd)] = render(
                    pack, trigger, tags, lo["file"], st, pose, sd)
    sc = score_many(pack, files)
    rows = []
    print("  %-8s %8s %8s   %s" % ("strength", "close", "turn", ""))
    for st in STRENGTHS:
        got = {}
        for pose in POSES:
            v = [sc[k] for k in sc
                 if k.startswith("%s|%.2f|" % (pose, st)) and sc[k] is not None]
            got[pose] = sum(v) / len(v) if v else None
        rows.append({"strength": st, "close": got["close"], "turn": got["turn"]})
        print("  %-8.2f %8s %8s" % (
            st, ("%.3f" % got["close"]) if got["close"] else "-",
            ("%.3f" % got["turn"]) if got["turn"] else "-"), flush=True)
    return {"pack": pack, "rows": rows}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("packs", nargs="+")
    ap.add_argument("--seeds", type=int, default=2)
    args = ap.parse_args()
    seeds = [4242, 7, 913][:max(1, min(args.seeds, 3))]
    out = []
    for p in args.packs:
        try:
            r = sweep(p, seeds)
            if r:
                out.append(r)
        except Exception as e:
            print("%s FAILED: %s" % (p, str(e)[:200]), flush=True)
    if out:
        json.dump(out, open(os.path.join(ROOT, "studio", "lora_strength.json"), "w"), indent=1)
    print("STRENGTH DONE", flush=True)
