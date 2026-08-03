#!/usr/bin/env python3
"""Put one character in many places and see whether they stay the same person.

    python3 studio/_tools/character_demo.py VIRO
    python3 studio/_tools/character_demo.py VIRO --engine qwen     # non-anime
    python3 studio/_tools/character_demo.py VIRO --no-lora         # the control

THE DEMO THE CAST PAGE WAS MISSING. A turnaround shows sixteen views of one portrait,
which proves the re-poser works. It does not prove the character survives being put
somewhere new - and that is the only thing anyone actually wants from a cast.

So: the same character, the same LoRA, across a spread of settings the training set never
contained. If the face and hair hold across a forest, a cathedral and a neon street, the
character is real. If they drift, the identity was never more than a prompt.

Run it with --no-lora to get the control. Without that comparison "he looks consistent"
is an impression rather than a finding.

ENGINES. --engine anime uses the danbooru path and the trained LoRA. --engine qwen uses
prose and photoreal, where the LoRA does NOT apply - a LoRA is a delta on specific
weights and this one was trained on animagine. The qwen pass is therefore a genuine test
of how far the written description alone carries a character, which is worth knowing
precisely because it is the weaker mechanism.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, HOST          # noqa: E402

CAST = os.path.join(STUDIO, "characters")
PLACES = os.path.join(STUDIO, "places")
OUT = os.path.join(STUDIO, "samples", "cast")
SEED = 8080
Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG = ("lowres, worst quality, bad anatomy, bad hands, watermark, text, "
       "multiple views, photorealistic, 3d")

# Fallbacks, used only when studio/places/ is empty. Deliberately far apart - a forest,
# a cathedral and a neon street share nothing, so a character that survives all three is
# surviving on identity rather than on the setting doing the work.
FALLBACK = [
    ("pine_forest",   "dense pine forest, moss covered trunks, low fog, shafts of light through canopy"),
    ("mountain_lake", "still mountain lake at dawn, mist on the water, pine ridge behind"),
    ("neon_street",   "rainy neon backstreet at night, wet asphalt, reflected signs"),
    ("cathedral",     "cathedral nave, stone columns, tall stained glass, dust in the light"),
    ("sky_palace",    "palace terrace above the clouds, open sky on all sides, birds at eye level"),
    ("desert",        "desert dunes at dusk, long shadows, wind-blown sand"),
    ("locker_room",   "locker room interior, benches, hanging jerseys, fluorescent light"),
    ("snowfield",     "open snowfield, bare trees, overcast flat light"),
]


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def places(n):
    out = []
    if os.path.isdir(PLACES):
        for fn in sorted(os.listdir(PLACES)):
            if fn.endswith(".json"):
                try:
                    p = json.load(open(os.path.join(PLACES, fn), encoding="utf-8"))
                    out.append((p["id"], p.get("tags", ""), p.get("prose", "")))
                except Exception:
                    pass
    if not out:
        out = [(i, t, t) for i, t in FALLBACK]
    # spread across the library rather than taking the first n alphabetically, so the
    # sample is not all one family
    if len(out) > n:
        step = len(out) / float(n)
        out = [out[int(i * step)] for i in range(n)]
    return out


def build(card, place_tags, place_prose, engine, lora, strength):
    if engine == "anime":
        wf = load_wf("22_anime_kf_ipadapter.json")
        set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
        set_path(wf, "4.inputs.weight", 0.0)
        wear = (card.get("wear_tags") or [""])[0]
        prompt = ", ".join(x for x in [card.get("tags", ""), "male focus", wear,
                                       "standing, looking at viewer",
                                       place_tags, Q] if x)
        set_path(wf, "5.inputs.text", prompt)
        set_path(wf, "6.inputs.text", NEG)
        set_path(wf, "8.inputs.seed", SEED)
        for n in ("7", "10"):
            set_path(wf, f"{n}.inputs.width", 1024)
            set_path(wf, f"{n}.inputs.height", 1024)
        if lora:
            wf["90"] = {"class_type": "LoraLoaderModelOnly",
                        "inputs": {"model": ["1", 0], "lora_name": lora,
                                   "strength_model": strength}}
            for nid, node in list(wf.items()):
                if nid in ("1", "90") or not isinstance(node, dict):
                    continue
                for k, v in (node.get("inputs") or {}).items():
                    if isinstance(v, list) and len(v) == 2 and v[0] == "1" and v[1] == 0:
                        node["inputs"][k] = ["90", 0]
        return wf, prompt, "11.inputs.filename_prefix"

    wf = load_wf("13_qwen_t2i_styled.json")
    wear = (card.get("wear_tags") or [""])[0]
    prompt = ". ".join(x.strip(" .,") for x in
                       [card.get("prose", card.get("tags", "")), wear,
                        "standing, looking at the camera", place_prose] if x.strip(" .,"))
    set_path(wf, "10.inputs.text", prompt)
    set_path(wf, "11.inputs.text", "lowres, bad anatomy, watermark, text")
    set_path(wf, "12.inputs.width", 1024)
    set_path(wf, "12.inputs.height", 1024)
    set_path(wf, "13.inputs.seed", SEED)
    return wf, prompt, "15.inputs.filename_prefix"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("character")
    ap.add_argument("--engine", default="anime", choices=["anime", "qwen"])
    ap.add_argument("--places", type=int, default=8)
    ap.add_argument("--strength", type=float, default=0.85)
    ap.add_argument("--no-lora", action="store_true")
    a = ap.parse_args()

    p = os.path.join(CAST, a.character + ".json")
    if not os.path.exists(p):
        raise SystemExit(f"unknown character {a.character!r}")
    card = json.load(open(p, encoding="utf-8"))
    lora = None if (a.no_lora or a.engine == "qwen") else card.get("lora")
    if a.engine == "qwen" and card.get("lora"):
        print("note: the LoRA is NOT applied on the qwen path - it is a delta on "
              "animagine weights. This pass tests the written description alone.")
    if a.engine == "anime" and not lora and not a.no_lora:
        print("note: %s has no trained LoRA; this is the description-only case."
              % a.character)

    pl = places(a.places)
    tag = "%s_%s%s" % (a.character.lower(), a.engine, "" if lora else "_nolora")
    print("%s across %d places, engine %s, lora %s"
          % (a.character, len(pl), a.engine, lora or "none"))

    cells = []
    for pid, ptags, pprose in pl:
        wf, prompt, prefix = build(card, ptags, pprose, a.engine, lora, a.strength)
        set_path(wf, prefix, f"claude-generated/studio_cast/demo_{tag}_{pid}")
        try:
            _, outs = run(HOST, wf, quiet=True)
        except Exception as e:
            print("  %-16s FAILED %s" % (pid, str(e)[:80]))
            continue
        if not outs:
            print("  %-16s no output" % pid)
            continue
        loc = ensure_local(outs[0], "/tmp/_cd_%s_%s.png" % (tag, pid), required=False)
        if not loc:
            continue
        cell = "/tmp/_cdc_%s_%s.png" % (tag, pid)
        sh("ffmpeg", "-y", "-v", "error", "-i", loc, "-vf",
           "scale=420:-1,drawtext=text='%s':fontcolor=yellow:fontsize=20:x=7:y=7:"
           "box=1:boxcolor=black@0.8:boxborderw=5" % pid.replace("_", " "), cell)
        if os.path.exists(cell):
            cells.append(cell)
            print("  %-16s ok" % pid, flush=True)

    if not cells:
        raise SystemExit("nothing rendered")
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "%s_demo.jpg" % tag)
    cols = 4
    rows = (len(cells) + cols - 1) // cols
    tmpdir = "/tmp/_cdtile_%s" % tag
    os.system("rm -rf %s && mkdir -p %s" % (tmpdir, tmpdir))
    for i, c in enumerate(cells):
        sh("cp", c, os.path.join(tmpdir, "%02d.png" % i))
    sh("ffmpeg", "-y", "-v", "error", "-pattern_type", "glob",
       "-i", os.path.join(tmpdir, "*.png"), "-filter_complex",
       "tile=%dx%d:margin=5:padding=5:color=0x111111" % (cols, rows),
       "-frames:v", "1", "-q:v", "4", dst)
    print("\n%s  (%.0f KB)" % (dst, os.path.getsize(dst) / 1024))
    print("\nSame character, same seed, %d settings none of which were in the training "
          "set." % len(cells))
    print("Run again with --no-lora for the control - without it, 'looks consistent' is "
          "an impression rather than a finding.")


if __name__ == "__main__":
    main()
