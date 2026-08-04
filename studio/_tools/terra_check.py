#!/usr/bin/env python3
"""Did training TERRA buy anything the danbooru tag was not already giving us?

For an INVENTED character the LoRA question is simple: without it there is no character at
all. TERRA is different. She is provenance=known_partial - the tag
"terra branford (final fantasy vi)" already reaches the right palette and silhouette on its
own, measured before she was ever built. So the honest question is not "does the LoRA work"
but "does the LoRA beat the tag", and a sweep that only compares LoRA-on against nothing
would answer the wrong one.

Four columns per place, all at one seed, in places the 16-view training set never contained:

  1  TAG ONLY, no LoRA          the real control - what she cost before today
  2  LoRA 0.50 + tag            the measured-safe strength for every other cast member
  3  LoRA 0.85 + tag            the old default, measured to destroy NIKA's setting
  4  LoRA 0.50, NAME REMOVED    the payoff cell

Column 4 is the one that decides whether she is a cast member or a prompt trick. If the
LoRA carries her with the danbooru name stripped out of the prompt, she belongs to this
project and can be put in any scene like VIRO or NIKA. If she collapses without the name,
the trained weights are riding on the tag and she is not really ours.
"""
import json, os, subprocess, sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                      # noqa: E402
from epic import load_wf, ensure_local, HOST         # noqa: E402

SEED = 5150
Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG = ("1boy, male focus, masculine, beard, multiple girls, lowres, worst quality, "
       "bad anatomy, bad hands, watermark, text, multiple views")

# Places the turnaround never saw - it was all plain-background studio views.
PLACES = [
    ("throne_room", "ornate stone throne room, tall stained glass windows, banners, torchlight"),
    ("snow_road",   "snow covered mountain road at dusk, bare trees, deep footprints, cold blue light"),
]


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def card():
    with open(os.path.join(ROOT, "studio", "characters", "TERRA.json"), encoding="utf-8") as f:
        return json.load(f)


def cell(tag, prompt, lora, strength):
    wf = load_wf("22_anime_kf_ipadapter.json")
    set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
    set_path(wf, "4.inputs.weight", 0.0)          # no IPAdapter - isolate the LoRA
    set_path(wf, "5.inputs.text", prompt)
    set_path(wf, "6.inputs.text", NEG)
    set_path(wf, "8.inputs.seed", SEED)
    for n in ("7", "10"):
        set_path(wf, f"{n}.inputs.width", 1024)
        set_path(wf, f"{n}.inputs.height", 1024)
    if lora and strength > 0:
        wf["90"] = {"class_type": "LoraLoaderModelOnly",
                    "inputs": {"model": ["1", 0], "lora_name": lora,
                               "strength_model": float(strength)}}
        for nid, node in list(wf.items()):
            if nid in ("1", "90") or not isinstance(node, dict):
                continue
            for k, v in (node.get("inputs") or {}).items():
                if isinstance(v, list) and len(v) == 2 and v[0] == "1" and v[1] == 0:
                    node["inputs"][k] = ["90", 0]
    set_path(wf, "11.inputs.filename_prefix", f"claude-generated/terra_check/{tag}")
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        return None
    loc = ensure_local(outs[0], f"/tmp/_tc_{tag}.png", required=False)
    if not loc:
        return None
    out = f"/tmp/tc_{tag}.webp"
    sh("ffmpeg", "-y", "-v", "error", "-i", loc, "-vf", "scale=520:-1", "-quality", "84", out)
    return out


def main():
    c = card()
    lora = c.get("lora")
    if not lora:
        raise SystemExit("TERRA has no trained lora on her card")
    tags = c["tags"]
    base = c.get("base_tags", "")
    wear = (c.get("wear_tags") or [""])[0]
    # Column 4 strips the danbooru name and the series, leaving only generic scaffolding.
    nameless = ", ".join(x for x in tags.split(", ")
                         if "terra branford" not in x and "final fantasy" not in x)

    rows = []
    for pid, ptext in PLACES:
        cols = []
        for label, tg, st in (
            ("tag only  no LoRA",      tags,     0.0),
            ("LoRA 0.50 + tag",        tags,     0.50),
            ("LoRA 0.85 + tag",        tags,     0.85),
            ("LoRA 0.50  NAME REMOVED", nameless, 0.50),
        ):
            prompt = ", ".join(x for x in [tg, base, wear, "standing, looking at viewer",
                                           ptext, Q] if x)
            tag = f"{pid}_{label.split()[0]}{int(st*100)}{'_nn' if tg is nameless else ''}"
            print("  %-14s %-26s" % (pid, label), flush=True)
            p = cell(tag, prompt, lora, st)
            if p:
                cols.append((f"{pid} | {label}", p))
        rows.append(cols)

    os.system("rm -rf /tmp/_tcg && mkdir -p /tmp/_tcg")
    i = 0
    for cols in rows:
        for label, p in cols:
            sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
               "scale=500:-1,drawtext=text='%s':fontcolor=yellow:fontsize=19:x=6:y=6:"
               "box=1:boxcolor=black@0.85:boxborderw=5" % label.replace(":", "\\:"),
               "/tmp/_tcg/%02d.png" % i)
            i += 1
    dst = os.path.join(ROOT, "studio", "samples", "cast", "terra_lora_check.jpg")
    sh("ffmpeg", "-y", "-v", "error", "-pattern_type", "glob", "-i", "/tmp/_tcg/*.png",
       "-filter_complex", "tile=4x%d:margin=6:padding=6:color=0x111111" % len(rows),
       "-frames:v", "1", "-q:v", "3", dst)
    print("\n%s" % dst)
    print("Read column 1 against column 2 - that is whether training bought anything.")
    print("Then read column 4 - that is whether she is a cast member or a prompt trick.")


if __name__ == "__main__":
    main()
