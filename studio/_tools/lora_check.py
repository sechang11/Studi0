#!/usr/bin/env python3
"""Does the character LoRA actually work? Render with and without it and look.

    python3 studio/_tools/lora_check.py VIRO
    python3 studio/_tools/lora_check.py VIRO --strength 0.8 --prompt "walking through rain"

A loss curve cannot tell you whether a character LoRA is good. The two ways it fails are
both invisible in a number and both obvious in a picture:

  OVERFIT      it reproduces the training images. Ask for the character on a rooftop and
               you get the training portrait again, same pose, same crop, background
               ignored.
  UNDERTRAINED it changes nothing. The with/without pair is the same picture.

So this renders the SAME prompt at the SAME seed with and without the LoRA, tiles them,
and leaves the judgement to eyes. It also renders a prompt the character was never
trained in - a new setting - because reproducing the training set is exactly the failure
mode a same-setting test would hide.
"""
import argparse, time, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, COMFY, HOST   # noqa: E402

WF = "22_anime_kf_ipadapter.json"
CAST = os.path.join(STUDIO, "characters")
OUT = os.path.join(STUDIO, "samples", "cast")
SEED = 5150
Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG = ("lowres, worst quality, bad anatomy, bad hands, watermark, text, "
       "multiple views, photorealistic, 3d")

# Deliberately NOT a setting from the training set. If the LoRA has memorised rather than
# learned, a familiar setting hides it and an unfamiliar one exposes it immediately.
DEFAULT_SCENE = "standing on a rainy city street at night, neon signs, looking at the camera"


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def build(lora, strength, prompt, tag):
    wf = load_wf(WF)
    set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
    set_path(wf, "4.inputs.weight", 0.0)          # no IPAdapter: isolate the LoRA
    set_path(wf, "5.inputs.text", prompt)
    set_path(wf, "6.inputs.text", NEG)
    set_path(wf, "8.inputs.seed", SEED)
    set_path(wf, "7.inputs.width", 1024)
    set_path(wf, "7.inputs.height", 1024)
    set_path(wf, "10.inputs.width", 1024)
    set_path(wf, "10.inputs.height", 1024)
    set_path(wf, "11.inputs.filename_prefix", f"claude-generated/studio_cast/check_{tag}")
    if lora:
        # insert a LoraLoaderModelOnly between the checkpoint and whatever consumed its
        # MODEL output, so the graph stays valid whatever node order the base uses
        wf["90"] = {"class_type": "LoraLoaderModelOnly",
                    "inputs": {"model": ["1", 0], "lora_name": lora,
                               "strength_model": float(strength)}}
        for nid, node in wf.items():
            if nid in ("1", "90") or not isinstance(node, dict):
                continue
            for k, v in (node.get("inputs") or {}).items():
                if isinstance(v, list) and len(v) == 2 and v[0] == "1" and v[1] == 0:
                    node["inputs"][k] = ["90", 0]
    return wf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("character")
    ap.add_argument("--strength", type=float, default=0.9)
    ap.add_argument("--prompt", default=DEFAULT_SCENE)
    a = ap.parse_args()

    p = os.path.join(CAST, a.character + ".json")
    if not os.path.exists(p):
        raise SystemExit(f"unknown character {a.character!r}")
    card = json.load(open(p, encoding="utf-8"))
    lora = card.get("lora")
    if not lora:
        raise SystemExit(f"{a.character} has no trained LoRA yet.\n"
                         f"  python3 studio/_tools/train_character.py {a.character}")

    trigger = a.character.lower()
    # The subject tags come from the CARD, not from a hardcoded 1boy. This was written
    # against a male character and the hardcode was never noticed, so checking a woman
    # rendered a man: both panels came back as somebody else and the comparison said
    # nothing at all. A check that silently tests the wrong subject is worse than no
    # check, because it produces a confident-looking answer.
    subject = ""
    for key in ("tags", "base_tags"):
        v = card.get(key)
        if isinstance(v, list):
            v = ", ".join(str(x) for x in v)
        if v:
            subject = v
            break
    if not subject:
        subject = "1girl, solo" if "girl" in str(card.get("desc", "")).lower() \
            else "1boy, solo"
    prompt = f"{trigger}, {subject}, {a.prompt}, {Q}"
    print("character : %s" % a.character)
    print("lora      : %s at %.2f" % (lora, a.strength))
    print("prompt    : %s" % prompt)
    print("scene is deliberately NOT from the training set")

    cells = []
    for lbl, use in (("without LoRA", None), ("with %s" % trigger, lora)):
        tag = a.character.lower() + ("_with" if use else "_without")
        try:
            _, outs = run(HOST, build(use, a.strength, prompt, tag), quiet=True)
        except Exception as e:
            print("  %-14s FAILED %s" % (lbl, str(e)[:100]))
            return
        if not outs:
            print("  %-14s no output" % lbl)
            return
        # ensure_local returns early if the destination already exists - correct for a
        # render cache, wrong here. With a fixed /tmp name, the SECOND check of a
        # character silently re-tiled the FIRST check's images: the prompt was fixed, the
        # renders were new and correct on the server, and the comparison still showed the
        # old pair. In a tool whose entire job is to show what actually happened, that is
        # the worst possible bug. Fetch to a fresh path every time.
        dest = "/tmp/_lc_%s_%d.png" % (tag, int(time.time() * 1000) % 10 ** 8)
        loc = ensure_local(outs[0], dest, required=False)
        if not loc:
            return
        cell = dest.replace("/_lc_", "/_lcc_")
        sh("ffmpeg", "-y", "-v", "error", "-i", loc, "-vf",
           "scale=520:-1,drawtext=text='%s':fontcolor=yellow:fontsize=22:x=8:y=8:"
           "box=1:boxcolor=black@0.8:boxborderw=5" % lbl, cell)
        cells.append(cell)
        print("  %-14s ok" % lbl)

    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "%s_loracheck.jpg" % a.character.lower())
    sh("ffmpeg", "-y", "-v", "error", "-i", cells[0], "-i", cells[1],
       "-filter_complex", "hstack=inputs=2", "-q:v", "4", dst)
    print("\n%s  (%.0f KB)" % (dst, os.path.getsize(dst) / 1024))
    print("\nLOOK AT IT. Same seed, same prompt, only the LoRA differs.")
    print("  identical            -> undertrained, the LoRA is doing nothing")
    print("  the training portrait-> overfit, it memorised instead of learning")
    print("  same person, new scene -> it worked")


if __name__ == "__main__":
    main()
