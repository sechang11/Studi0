#!/usr/bin/env python3
"""Does a costume actually REPLACE the outfit the LoRA was trained on?

THE FIXED TEST for wardrobe separability. All four of TERRA's costumes, at wear level 0,
one seed, one place, full body so the whole garment is visible. Read it as a grid: each
ROW is one way of asking, each COLUMN is one costume. The question for every cell is
blunt - has the gold dress gone, or is it still under there?

WHY THE CONTROL ROWS EXIST. "The LoRA memorised the clothes" is a hypothesis with a
competing explanation sitting right next to it: TERRA is a KNOWN character, and the
danbooru tag "terra branford (final fantasy vi)" carries her canonical gold dress in the
base checkpoint whether a LoRA is loaded or not. If the dress persists with NO LoRA at
all, then no amount of retraining will ever fix it and the real fix is to strip the name
on costume shots. Measuring the LoRA without measuring the tag would have blamed the
wrong layer.

  row 1  no LoRA, full tags       does the NAME alone drag the dress in?
  row 2  no LoRA, name stripped   the ceiling - what the costume words do unopposed
  row 3  LoRA, name stripped      the LoRA's own contribution, isolated
  row 4  LoRA, full tags          real usage, both effects together

Run it once per LoRA and tile the results together to compare a retrain against the
original.
"""
import argparse, json, os, subprocess, sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                      # noqa: E402
from epic import load_wf, ensure_local, HOST         # noqa: E402

SEED = 4242          # --seed overrides. A conclusion that only holds at one seed is not
                     # a conclusion; the interesting rows get re-run at a second one.
Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG = ("1boy, male focus, masculine, beard, multiple girls, lowres, worst quality, "
       "bad anatomy, bad hands, watermark, text, multiple views")

# A place the 16-view training set never contained, and one that does not itself imply a
# costume - a throne room argues for the court gown, a battlefield argues for the plate.
# A plain stone courtyard argues for nothing, so whatever is worn is the prompt's doing.
PLACE = "a plain stone courtyard, overcast daylight, flat grey wall behind"
FRAME = "standing, full body visible head to feet, facing the camera"

OUT = os.path.join(ROOT, "studio", "samples", "cast", "terra_costume_fix")

# A FRESH SCRATCH DIRECTORY PER PROCESS, and it is not a tidiness measure.
#
# epic.ensure_local() begins "if os.path.exists(dest): return dest" - a deliberate cache,
# correct for its own purposes. But a probe names its scratch files after the CELL
# (ab_0, ab_1 ...), and those names repeat exactly on the next run. So a second run
# against a different LoRA re-tiles the FIRST run's images and produces a grid that is
# byte-identical to the one before it.
#
# That failure mode reads as "the change did nothing", which is a conclusion a careful
# person would then write down. It nearly was. Anything a probe downloads must go
# somewhere no previous run can have touched.
RUN = os.path.join("/tmp", "_probe_%d" % os.getpid())
os.makedirs(RUN, exist_ok=True)


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def card():
    with open(os.path.join(ROOT, "studio", "characters", "TERRA.json"), encoding="utf-8") as f:
        return json.load(f)


def cell(tag, prompt, lora, strength, seed=SEED):
    wf = load_wf("22_anime_kf_ipadapter.json")
    set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
    set_path(wf, "4.inputs.weight", 0.0)          # no IPAdapter - isolate the weights
    set_path(wf, "5.inputs.text", prompt)
    set_path(wf, "6.inputs.text", NEG)
    set_path(wf, "8.inputs.seed", int(seed))
    for n in ("7", "10"):
        set_path(wf, f"{n}.inputs.width", 832)
        set_path(wf, f"{n}.inputs.height", 1216)   # portrait, so a full body is readable
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
    set_path(wf, "11.inputs.filename_prefix", f"claude-generated/terra_costume/{tag}")
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        return None
    return ensure_local(outs[0], os.path.join(RUN, f"{tag}.png"), required=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lora", help="lora filename to test (default: the card's)")
    ap.add_argument("--strength", type=float, default=0.5)
    ap.add_argument("--out", default="costume_grid.jpg")
    ap.add_argument("--label", default="LoRA")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--rows", default="all",
                    help="all | lora  (lora = just the two LoRA rows, skips the controls)")
    a = ap.parse_args()

    c = card()
    lora = a.lora or c.get("lora")
    tags = c["tags"]
    base = c.get("base_tags", "")
    nameless = ", ".join(x for x in tags.split(", ")
                         if "terra branford" not in x and "final fantasy" not in x)

    costumes = c["costumes"]
    order = ["default", "armour", "court", "field"]

    rows = [
        ("no LoRA  full tags",     tags,     None, 0.0),
        ("no LoRA  NAME STRIPPED", nameless, None, 0.0),
        (f"{a.label}  NAME STRIPPED", nameless, lora, a.strength),
        (f"{a.label}  full tags",     tags,     lora, a.strength),
    ]
    if a.rows == "lora":
        rows = rows[2:]

    os.makedirs(OUT, exist_ok=True)
    os.system("rm -rf /tmp/_cpg && mkdir -p /tmp/_cpg")
    i = 0
    for rlabel, tg, lo, st in rows:
        for cid in order:
            wear = costumes[cid]["wear_tags"][0]
            prompt = ", ".join(x for x in [tg, base, wear, FRAME, PLACE, Q] if x)
            tag = "%s_%s_%d" % (cid, rlabel.split()[0].replace("/", ""), int(st * 100))
            print("  %-22s %-8s" % (rlabel, cid), flush=True)
            p = cell(tag + "_%d" % i, prompt, lo, st, a.seed)
            if not p:
                print("     FAILED")
                i += 1
                continue
            label = "%s | %s" % (rlabel, costumes[cid]["name"])
            sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
               "scale=440:-1,drawtext=text='%s':fontcolor=yellow:fontsize=18:x=6:y=6:"
               "box=1:boxcolor=black@0.85:boxborderw=5" % label.replace(":", "\\:"),
               "/tmp/_cpg/%02d.png" % i)
            i += 1

    dst = os.path.join(OUT, a.out)
    sh("ffmpeg", "-y", "-v", "error", "-pattern_type", "glob", "-i", "/tmp/_cpg/*.png",
       "-filter_complex", "tile=4x%d:margin=6:padding=6:color=0x111111" % len(rows),
       "-frames:v", "1", "-q:v", "3", dst)
    print("\n%s" % dst)
    print("Columns: traveller (the trained outfit), imperial plate, court dress, field coat.")
    print("For each cell ask only: has the gold dress GONE, or is it still under there?")


if __name__ == "__main__":
    main()
