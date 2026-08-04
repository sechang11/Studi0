#!/usr/bin/env python3
"""Same seed, same prompt, one row per scene, one column per LoRA strength. Then LOOK.

    python3 studio/_tools/lora_strength_sweep.py NIKA
    python3 studio/_tools/lora_strength_sweep.py NIKA --strengths 0 0.5 0.85 1.0

WHY NOT lora_check.py

lora_check.py renders exactly two cells, with and without, at ONE strength - and line 93
hard-codes the subject:

    prompt = f"{trigger}, 1boy, solo, {a.prompt}, {Q}"

so it cannot describe a girl or a child at all. character_demo.py has the same bug from
the other end: line 89 splices the literal string "male focus" into every prompt and never
reads `base_tags`. Both tools predate the existence of a non-male card. This one builds
the subject from the card - tags, then base_tags, then the clean garment - in the order
compose.py:1479-1490 uses.

WHY A STRENGTH SWEEP AND NOT A SINGLE NUMBER

Strength is a measured tradeoff in this project, not a dial to max: a character LoRA at
0.85 turned a neon street into an interior, which is why 0.5 was sampled. The failure is
invisible at the character and obvious at the background, so the background has to be in
frame and has to be the same background across the row. Every cell in a row shares a seed
and a prompt; only strength changes.

Both scenes are deliberately NOT from the training set. The training set is sixteen
head-and-shoulders views on a plain background; if the LoRA has memorised rather than
learned, an unfamiliar full-scene prompt exposes it and a portrait prompt would hide it.

READ THE OUTPUT:
  all columns identical          -> undertrained, the LoRA is doing nothing
  the training portrait returns  -> overfit, it memorised the set
  background flattens as strength rises -> the documented 0.85 cost, pick a lower column
  same person, scene intact      -> it worked at that strength
"""
import argparse, json, os, subprocess, sys

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
Q = "masterpiece, best quality, very aesthetic, absurdres"

# No sex terms in here at all. The stock node-6 negative carries "1girl, girl, female,
# feminine, breasts", which is why it is replaced wholesale rather than appended to.
NEG_BASE = ("lowres, worst quality, bad anatomy, bad hands, extra limbs, watermark, "
            "signature, text, multiple views, photorealistic, 3d, western comic")
NEG_MALE = "1girl, female, feminine, breasts"
NEG_FEMALE = "1boy, male focus, masculine, beard, facial hair"
NEG_CHILD = "adult, mature male, muscular, tall"

SCENES = [
    ("neon street", "standing on a rainy city street at night, neon signs, wet asphalt, "
                    "reflections, crowd behind, looking at the viewer"),
    ("sunlit field", "standing in a sunlit grass field, big sky, distant trees, "
                     "daylight, wind, looking at the viewer"),
]


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def negative_for(card):
    t = (card.get("tags", "") + " " + card.get("base_tags", "")).lower()
    parts = [NEG_FEMALE if "1girl" in t else NEG_MALE]
    if "child" in t:
        parts.append(NEG_CHILD)
    parts.append(NEG_BASE)
    return ", ".join(parts)


def positive_for(card, cid, scene):
    """identity -> base -> garment in its clean state -> world. The project's tag order."""
    bits = [cid.lower()]                       # the trigger word turnaround.py captions with
    bits.append(card.get("tags", "").strip())
    if card.get("base_tags"):
        bits.append(card["base_tags"].strip())
    wear = card.get("wear_tags") or []
    if wear:
        bits.append(wear[0].strip())
    bits.append(scene)
    bits.append(Q)
    return ", ".join(b for b in bits if b)


def build(card, cid, scene, lora, strength, seed):
    wf = load_wf(WF)
    set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
    set_path(wf, "4.inputs.weight", 0.0)       # no IPAdapter: isolate the LoRA
    set_path(wf, "5.inputs.text", positive_for(card, cid, scene))
    set_path(wf, "6.inputs.text", negative_for(card))
    set_path(wf, "8.inputs.seed", seed)
    for n in ("7", "10"):
        set_path(wf, "%s.inputs.width" % n, 1024)
        set_path(wf, "%s.inputs.height" % n, 1024)
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
    return wf


def label(src, dst, text, size=512):
    sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vf",
       "scale=%d:%d,drawtext=text='%s':fontcolor=yellow:fontsize=24:x=10:y=10:"
       "box=1:boxcolor=black@0.85:boxborderw=6" % (size, size, text.replace("'", "")), dst)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("character")
    ap.add_argument("--strengths", type=float, nargs="+", default=[0.0, 0.5, 0.85])
    ap.add_argument("--seed", type=int, default=5150)
    a = ap.parse_args()

    p = os.path.join(CAST, a.character + ".json")
    if not os.path.exists(p):
        raise SystemExit("unknown character %r" % a.character)
    card = json.load(open(p, encoding="utf-8"))
    lora = card.get("lora")
    if not lora:
        raise SystemExit("%s has no trained LoRA yet." % a.character)

    print("character : %s" % a.character)
    print("lora      : %s" % lora)
    print("strengths : %s   (0.0 is the control, same seed)" % a.strengths)
    print("negative  : %s" % negative_for(card)[:100])

    rows = []
    for si, (sname, scene) in enumerate(SCENES):
        seed = a.seed + si * 101
        cells = []
        for st in a.strengths:
            tag = "%s_s%s_%d" % (a.character.lower(), str(st).replace(".", ""), si)
            wf = build(card, a.character, scene, lora, st, seed)
            set_path(wf, "11.inputs.filename_prefix",
                     "claude-generated/studio_cast/sweep_%s" % tag)
            try:
                _, outs = run(HOST, wf, quiet=True)
            except Exception as e:
                print("  %-14s %.2f FAILED %s" % (sname, st, str(e)[:70]))
                return
            if not outs:
                print("  %-14s %.2f no output" % (sname, st))
                return
            loc = ensure_local(outs[0], "/tmp/_sw_%s.png" % tag, required=False)
            if not loc:
                return
            txt = "%s | %s" % (sname, "NO LORA (control)" if st == 0 else "strength %.2f" % st)
            cells.append(label(loc, "/tmp/_swc_%s.png" % tag, txt))
            print("  %-14s %.2f ok" % (sname, st))
        row = "/tmp/_swrow_%d.png" % si
        sh("ffmpeg", "-y", "-v", "error", *sum((["-i", c] for c in cells), []),
           "-filter_complex", "hstack=inputs=%d" % len(cells), row)
        rows.append(row)

    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "%s_sweep.jpg" % a.character.lower())
    sh("ffmpeg", "-y", "-v", "error", *sum((["-i", r] for r in rows), []),
       "-filter_complex", "vstack=inputs=%d" % len(rows), "-q:v", "3", dst)
    print("\n%s  (%.0f KB)" % (dst, os.path.getsize(dst) / 1024.0))
    print("LOOK AT IT. Columns share a seed and a prompt; only strength differs.")


if __name__ == "__main__":
    main()
