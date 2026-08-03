#!/usr/bin/env python3
"""Render a with/without pair for every glossary tag.

    python3 studio/_tools/tag_examples.py              # all tags, skip done
    python3 studio/_tools/tag_examples.py cel_shading
    python3 studio/_tools/tag_examples.py --force

A definition tells you what a word means. It cannot tell you what THIS model does with it,
and that is the only thing that matters when you are writing a prompt. So every tag gets
one image without it and one with it, identical in every other respect - same base
prompt, same seed, same sampler - tiled side by side and labelled.

WHY THE PAIR AND NOT A GALLERY OF TAGGED IMAGES

Because "here is a picture that used cel shading" teaches nothing. You cannot tell which
part of it came from the tag. Holding everything else still is the ONLY way the
difference is attributable, and this project has twice proved the cost of not doing it -
133 of 134 capability cards vary composition between options and prove nothing, and the
first camera sweep was worthless because the clip's own content moved more than the
camera did.

NEGATIVE-ONLY TAGS are rendered the other way round: the pair is negative-absent vs
negative-present, because putting them in the positive is the mistake the card exists to
warn about.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                      # noqa: E402
from epic import load_wf, ensure_local, HOST         # noqa: E402

TAGS = os.path.join(STUDIO, "tags")
OUT = os.path.join(STUDIO, "samples", "tags")
WF = "22_anime_kf_ipadapter.json"
CKPT = "animagine-xl-4.0.safetensors"
SEED = 4242
STEPS, CFG = 28, 5.0

# A deliberately PLAIN base. It has a person, a garment, a background and a light source,
# so most tags have something to act on - but it names no style, no lens and no mood, so
# whatever changes between the two panels came from the tag under test.
BASE = ("1boy, solo, male focus, short dark hair, plain jacket, standing, "
        "city street, daytime")
NEG = "lowres, worst quality, bad anatomy, bad hands, watermark, text"


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def render(prompt, neg, tag_out):
    wf = load_wf(WF)
    set_path(wf, "1.inputs.ckpt_name", CKPT)
    set_path(wf, "4.inputs.weight", 0.0)
    set_path(wf, "5.inputs.text", prompt)
    set_path(wf, "8.inputs.seed", SEED)
    set_path(wf, "8.inputs.steps", STEPS)
    set_path(wf, "8.inputs.cfg", CFG)
    set_path(wf, "7.inputs.width", 1024)
    set_path(wf, "7.inputs.height", 576)
    set_path(wf, "10.inputs.width", 1024)
    set_path(wf, "10.inputs.height", 576)
    # the negative lives on node 6 in this graph; fall back silently if it moves
    try:
        set_path(wf, "6.inputs.text", neg)
    except Exception:
        pass
    set_path(wf, "11.inputs.filename_prefix", f"claude-generated/studio_tags/{tag_out}")
    _, outs = run(HOST, wf, quiet=True)
    return outs[0] if outs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("only", nargs="?")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if not os.path.isdir(TAGS):
        raise SystemExit(f"no glossary at {TAGS}")
    os.makedirs(OUT, exist_ok=True)

    names = sorted(f[:-5] for f in os.listdir(TAGS) if f.endswith(".json"))
    if a.only:
        names = [n for n in names if n == a.only or n.startswith(a.only)]

    made = skipped = failed = 0
    for name in names:
        dst = os.path.join(OUT, name + ".webp")
        if os.path.exists(dst) and not a.force:
            skipped += 1
            continue
        t = json.load(open(os.path.join(TAGS, name + ".json"), encoding="utf-8"))
        term = t.get("term", name.replace("_", " "))
        neg_only = bool(t.get("negative_instead"))

        if neg_only:
            a_prompt, a_neg, a_lbl = BASE, NEG, "not in negative"
            b_prompt, b_neg, b_lbl = BASE, NEG + ", " + term, "in negative"
        else:
            a_prompt, a_neg, a_lbl = BASE, NEG, "without"
            b_prompt, b_neg, b_lbl = BASE + ", " + term, NEG, "with " + term

        cells = []
        for i, (pr, ng, lbl) in enumerate(((a_prompt, a_neg, a_lbl),
                                           (b_prompt, b_neg, b_lbl))):
            try:
                rel = render(pr, ng, f"{name}_{i}")
            except Exception as e:
                print("  %-26s FAILED: %s" % (name, str(e)[:90]))
                rel = None
            if not rel:
                break
            loc = ensure_local(rel, f"/tmp/_tag_{name}_{i}.png", required=False)
            if not loc:
                break
            cell = f"/tmp/_tagc_{name}_{i}.png"
            sh("ffmpeg", "-y", "-v", "error", "-i", loc, "-vf",
               "scale=480:-1,drawtext=text='%s':fontcolor=yellow:fontsize=21:x=8:y=8:"
               "box=1:boxcolor=black@0.8:boxborderw=5" % lbl.replace("'", ""), cell)
            if os.path.exists(cell):
                cells.append(cell)
        if len(cells) != 2:
            failed += 1
            continue
        sh("ffmpeg", "-y", "-v", "error", "-i", cells[0], "-i", cells[1],
           "-filter_complex", "hstack=inputs=2", "-quality", "82", dst)
        for c in cells:
            os.remove(c)
        if not os.path.exists(dst):
            failed += 1
            continue
        # stamp the path onto the card so the page needs no naming convention
        t["example"] = f"/samples/tags/{name}.webp"
        t["example_base"] = BASE
        # Say what the pair does NOT prove. Same seed, same sampler, one clause added -
        # and the composition still moves, because adding any clause re-rolls SDXL's
        # conditioning. So the pair is honest about STYLE and not about framing. This is
        # the same limitation that makes 133 of 134 capability cards show four unrelated
        # portraits, and pretending otherwise here would repeat it.
        t["read_it_as"] = ("Compare the SHADING, colour and line - not the pose or "
                           "framing. Adding any clause re-rolls the model's conditioning, "
                           "so composition moves between the two panels even at a fixed "
                           "seed. An img2img pass from one fixed base image would isolate "
                           "the tag properly; that is not built yet.")
        with open(os.path.join(TAGS, name + ".json"), "w", encoding="utf-8") as f:
            json.dump(t, f, indent=2, ensure_ascii=False)
            f.write("\n")
        made += 1
        print("  %-26s %s  %5.1f KB" % (name, "negative-pair" if neg_only else "pair",
                                        os.path.getsize(dst) / 1024), flush=True)

    print("\n%d rendered, %d already present, %d failed" % (made, skipped, failed))


if __name__ == "__main__":
    main()
