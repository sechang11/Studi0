#!/usr/bin/env python3
"""Does the model already know a named character, or must we build one?

A cast member in this project costs a reference sheet, a 16-view turnaround and a LoRA
training run - roughly twenty minutes of GPU - because VIRO, NIKA and PIP are invented and
nothing in the checkpoint has ever seen them.

A character the model was TRAINED ON is a different problem. animagine-xl-4.0 is an SDXL
finetuned on the danbooru corpus, where well-known game and anime characters are tagged by
name, usually as "character_name (series_name)". If the tag has mass, the character comes
back from the tag alone at full strength, with no sheet, no turnaround and no LoRA - and
more consistently than a trained LoRA, because it is baked into the base weights rather
than patched on top.

So the first question is never "how do we build her", it is "does the checkpoint already
have her". This answers that for any name, in about six seconds a cell.

    python3 studio/_tools/known_char_probe.py "terra branford" --series "final fantasy vi"

FOUR CELLS, because a bare name proves nothing on its own:
  1. the danbooru form           character (series)
  2. the bare name               character
  3. name plus a description     in case the tag is weak and the words carry it
  4. A CONTROL with NO NAME      the same description alone

Cell 4 is the cell that matters and it is the one a careless test omits. If cells 1 and 4
look the same, the NAME did nothing and everything you are seeing came from the adjectives
- which is this project's governing rule (the model renders nouns, not adjectives) applied
to character names. A name only counts as known if it beats its own description.
"""
import argparse, os, subprocess, sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                      # noqa: E402
from epic import load_wf, ensure_local, HOST         # noqa: E402

Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG = "lowres, worst quality, bad anatomy, bad hands, watermark, text, signature, multiple views"
PLACE = "standing, upper body, looking at viewer, plain background"
SEED = 9090


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def cell(tag, prompt, ckpt):
    wf = load_wf("22_anime_kf_ipadapter.json")
    set_path(wf, "1.inputs.ckpt_name", ckpt)
    set_path(wf, "4.inputs.weight", 0.0)
    set_path(wf, "5.inputs.text", ", ".join(x for x in [prompt, PLACE, Q] if x))
    set_path(wf, "6.inputs.text", NEG)
    set_path(wf, "8.inputs.seed", SEED)
    for n in ("7", "10"):
        set_path(wf, f"{n}.inputs.width", 1024)
        set_path(wf, f"{n}.inputs.height", 1024)
    set_path(wf, "11.inputs.filename_prefix", f"claude-generated/known_probe/{tag}")
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        return None
    loc = ensure_local(outs[0], f"/tmp/_kc_{tag}.png", required=False)
    if not loc:
        return None
    out = f"/tmp/kc_{tag}.webp"
    sh("ffmpeg", "-y", "-v", "error", "-i", loc, "-vf", "scale=560:-1", "-quality", "84", out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--series", default="")
    ap.add_argument("--desc", default="",
                    help="a description with NO name in it - this becomes the control")
    ap.add_argument("--ckpt", default="animagine-xl-4.0.safetensors")
    ap.add_argument("--out")
    a = ap.parse_args()

    name = a.name.strip()
    danbooru = f"{name} ({a.series})" if a.series else name
    desc = a.desc.strip()

    tests = [
        ("danbooru", danbooru, "danbooru form: name (series)"),
        ("bare",     name,     "bare name only"),
    ]
    if desc:
        tests.append(("named_desc", f"{danbooru}, {desc}", "name plus description"))
        tests.append(("CONTROL",    desc,                  "DESCRIPTION ONLY - no name"))

    cells = []
    for tag, prompt, label in tests:
        print("  %-11s %s" % (tag, prompt[:90]), flush=True)
        p = cell(tag, prompt, a.ckpt)
        if p:
            cells.append((label, p))

    if not cells:
        raise SystemExit("nothing rendered")

    os.system("rm -rf /tmp/_kcg && mkdir -p /tmp/_kcg")
    for i, (label, p) in enumerate(cells):
        sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
           "scale=540:-1,drawtext=text='%s':fontcolor=yellow:fontsize=20:x=7:y=7:"
           "box=1:boxcolor=black@0.85:boxborderw=6" % label.replace(":", "\\:"),
           "/tmp/_kcg/%02d.png" % i)
    dst = a.out or ("/tmp/known_%s.jpg" % name.replace(" ", "_"))
    sh("ffmpeg", "-y", "-v", "error", "-pattern_type", "glob", "-i", "/tmp/_kcg/*.png",
       "-filter_complex", "tile=%dx1:margin=6:padding=6:color=0x111111" % len(cells),
       "-frames:v", "1", "-q:v", "3", dst)
    print("\n%s" % dst)
    print("Read the LAST cell first. If the control looks like the named cells, the NAME "
          "did nothing and the description is carrying it.")


if __name__ == "__main__":
    main()
