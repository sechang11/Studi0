#!/usr/bin/env python3
"""Does captioning the backdrop stop a high LoRA strength from eating the scenery?

THE SECOND SYMPTOM OF THE SAME BUG. "0.85 destroys the setting" is measured twice in this
project - NIKA's sunlit field went grey, TERRA's snow forest collapsed to flat beige - and
was written down as a property of LoRA strength. It is not. Every turnaround view is shot
against the same flat taupe wall, and the original captions named the trigger and the view
and nothing else, so the wall was an unexplained constant and the trigger absorbed it
along with the clothes. Turning the LoRA up turns the memorised wall up. Beige is the
literal colour of the turnaround backdrop.

If that reading is right, a LoRA retrained with "plain flat grey background" in every
caption should hold its setting at 0.85 where the old one could not - because the backdrop
now has its own words to live in and no longer has to hide inside the character.

Two places with strong, unmistakable scenery, two strengths, both LoRAs, one seed.
Read down each column: does the place survive?
"""
import argparse, json, os, subprocess, sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                      # noqa: E402
from epic import load_wf, ensure_local, HOST         # noqa: E402

SEED = 5150
Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG = ("1boy, male focus, masculine, beard, multiple girls, lowres, worst quality, "
       "bad anatomy, bad hands, watermark, text, multiple views")

# The two places the collapse was actually measured in, so this is comparable to the
# earlier finding rather than a fresh unrelated test.
PLACES = [
    ("snow_road", "snow covered mountain road at dusk, bare trees, deep footprints, cold blue light"),
    ("field",     "a wide sunlit meadow at noon, tall grass, wildflowers, distant hills, blue sky"),
]

OUT = os.path.join(ROOT, "studio", "samples", "cast", "terra_costume_fix")

# Per-process scratch. epic.ensure_local() returns early when the destination exists, so
# reusing cell filenames across runs re-tiles the PREVIOUS run's images into a grid that
# looks like a measurement and is not one. See costume_probe.py for the full note.
RUN = os.path.join("/tmp", "_setting_%d" % os.getpid())
os.makedirs(RUN, exist_ok=True)


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def cell(tag, prompt, lora, strength):
    wf = load_wf("22_anime_kf_ipadapter.json")
    set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
    set_path(wf, "4.inputs.weight", 0.0)
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
    set_path(wf, "11.inputs.filename_prefix", f"claude-generated/terra_setting/{tag}")
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        return None
    return ensure_local(outs[0], os.path.join(RUN, f"{tag}.png"), required=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    # Labels follow the actual files. A hardcoded label once put "v2 captioned" on a grid
    # rendered from v3 - the evidence file then argues for the wrong thing forever.
    ap.add_argument("--old-label")
    ap.add_argument("--new-label")
    ap.add_argument("--out", default="setting_grid.jpg")
    a = ap.parse_args()

    with open(os.path.join(ROOT, "studio", "characters", "TERRA.json"), encoding="utf-8") as f:
        c = json.load(f)
    tags, base = c["tags"], c.get("base_tags", "")
    wear = c["costumes"]["default"]["wear_tags"][0]

    def short(fn):
        return fn.replace("character_terra_", "").replace(".safetensors", "")
    ol = a.old_label or short(a.old)
    nl = a.new_label or short(a.new)
    rows = [
        ("%s 0.50" % ol, a.old, 0.50),
        ("%s 0.85" % ol, a.old, 0.85),
        ("%s 0.50" % nl, a.new, 0.50),
        ("%s 0.85" % nl, a.new, 0.85),
    ]

    os.makedirs(OUT, exist_ok=True)
    os.system("rm -rf /tmp/_spg && mkdir -p /tmp/_spg")
    i = 0
    for rlabel, lo, st in rows:
        for pid, ptext in PLACES:
            prompt = ", ".join(x for x in [tags, base, wear,
                                           "standing, full body, looking at viewer",
                                           ptext, Q] if x)
            print("  %-22s %-10s" % (rlabel, pid), flush=True)
            p = cell("%s_%d" % (pid, i), prompt, lo, st)
            if not p:
                print("     FAILED")
                i += 1
                continue
            label = "%s | %s" % (rlabel, pid)
            sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
               "scale=460:-1,drawtext=text='%s':fontcolor=yellow:fontsize=18:x=6:y=6:"
               "box=1:boxcolor=black@0.85:boxborderw=5" % label.replace(":", "\\:"),
               "/tmp/_spg/%02d.png" % i)
            i += 1

    dst = os.path.join(OUT, a.out)
    sh("ffmpeg", "-y", "-v", "error", "-pattern_type", "glob", "-i", "/tmp/_spg/*.png",
       "-filter_complex", "tile=2x%d:margin=6:padding=6:color=0x111111" % len(rows),
       "-frames:v", "1", "-q:v", "3", dst)
    print("\n%s" % dst)
    print("Read rows 2 and 4 against each other. That is the whole question:")
    print("does the captioned LoRA still have a snow road and a meadow at 0.85?")


if __name__ == "__main__":
    main()
