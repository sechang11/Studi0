#!/usr/bin/env python3
"""Render a showcase image for every scene template.

This is the thing that makes a template picker usable. A name and a list of settings
tells you almost nothing about what you will get; a picture tells you immediately. It is
the same reason a model page on Civitai leads with the image and prints the prompt under
it - and the reason this project renders a comparison panel for every enum value rather
than describing one.

Each template's shots are rendered as keyframes and tiled into one strip, so the card
shows the template's actual ARC rather than a single frame. Roughly 5s of GPU per shot.

    python3 studio/_tools/render_templates.py            # all templates, skip done
    python3 studio/_tools/render_templates.py --force    # re-render everything
    python3 studio/_tools/render_templates.py sports_climax

The subject is held FIXED across every template - same character, same seed - so that
differences between showcase images are differences between TEMPLATES, not lottery. Same
discipline as the capability cards, and the same reason the first camera sweep was
useless until it was swept against a still.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                      # noqa: E402
from epic import load_wf, ensure_local, COMFY, HOST   # noqa: E402

TPL = os.path.join(STUDIO, "templates")
OUT = os.path.join(STUDIO, "samples", "templates")
SEED = 7311                       # fixed: differences must come from the template
Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG = ("lowres, worst quality, bad anatomy, bad hands, watermark, text, "
       "multiple views, photorealistic, 3d, western comic, blurry")
# The same character every capability panel uses, so the whole library is visually
# consistent and a template's look is not confounded by a different face.
SUBJ = ("1boy, solo, male focus, dark red hair, undercut, yellow eyes, "
        "black soccer jersey, silver trim, number 9")


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def keyframe(prompt, tag, ckpt="animagine-xl-4.0.safetensors"):
    wf = load_wf("22_anime_kf_ipadapter.json")
    set_path(wf, "1.inputs.ckpt_name", ckpt)
    set_path(wf, "4.inputs.weight", 0.0)     # no reference: the template is the subject
    set_path(wf, "5.inputs.text", prompt)
    set_path(wf, "8.inputs.seed", SEED)
    set_path(wf, "7.inputs.width", 1344)
    set_path(wf, "7.inputs.height", 768)
    set_path(wf, "10.inputs.width", 1344)
    set_path(wf, "10.inputs.height", 768)
    set_path(wf, "11.inputs.filename_prefix", f"claude-generated/studio_templates/{tag}")
    _, outs = run(HOST, wf, quiet=True)
    return outs[0] if outs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("only", nargs="?")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    if not os.path.isdir(TPL):
        raise SystemExit(f"no templates at {TPL}")
    os.makedirs(OUT, exist_ok=True)

    looks = {}
    for fn in os.listdir(os.path.join(STUDIO, "looks")):
        if fn.endswith(".json"):
            looks[fn[:-5]] = json.load(open(os.path.join(STUDIO, "looks", fn),
                                            encoding="utf-8"))
    emos = {}
    ed = os.path.join(STUDIO, "emotions")
    for fn in os.listdir(ed):
        if fn.endswith(".json"):
            emos[fn[:-5]] = json.load(open(os.path.join(ed, fn), encoding="utf-8"))

    names = sorted(f[:-5] for f in os.listdir(TPL) if f.endswith(".json"))
    if a.only:
        names = [n for n in names if n == a.only or n.startswith(a.only)]

    for name in names:
        dst = os.path.join(OUT, name + ".webp")
        if os.path.exists(dst) and not a.force:
            print("  %-26s skip (exists)" % name)
            continue
        t = json.load(open(os.path.join(TPL, name + ".json"), encoding="utf-8"))
        sets, shots = t.get("sets", {}), t.get("shots", [])
        if not shots:
            print("  %-26s no shots" % name)
            continue

        look = looks.get(sets.get("look", "neutral"), {})
        emo = emos.get(sets.get("emotion", ""), {})
        cells = []
        for i, sh_ in enumerate(shots):
            desc = (sh_.get("desc") or "").strip()
            peopleless = sh_.get("template") in ("establish", "insert", "pillow")
            # Same tag ORDER the compiler uses: identity, face, action, world.
            bits = ([] if peopleless else [SUBJ])
            if not peopleless and emo:
                bits += [emo.get("face", ""), emo.get("eyes", ""), emo.get("mouth", "")]
            bits += [desc, sets.get("place", ""), look.get("tags", ""),
                     "modern sports anime, cel shading, cinematic", Q]
            prompt = ", ".join(x for x in bits if x)
            tag = f"{name}_{i}"
            print("  %-26s shot %d/%d" % (name, i + 1, len(shots)), flush=True)
            try:
                rel = keyframe(prompt, tag)
            except Exception as e:
                print("     FAILED: %s" % str(e)[:120])
                continue
            if not rel:
                continue
            local = ensure_local(rel, f"/tmp/_tpl_{tag}.png", required=False)
            if not local:
                continue
            # Apply the template's own grade, so the showcase shows the colour you will
            # actually get rather than the ungraded keyframe.
            grade = look.get("grade") or "eq=contrast=1.06:saturation=1.12"
            cell = f"/tmp/_tplc_{tag}.png"
            sh("ffmpeg", "-y", "-v", "error", "-i", local, "-vf",
               f"{grade},scale=380:-1", cell)
            if os.path.exists(cell):
                cells.append(cell)

        if not cells:
            print("  %-26s produced nothing" % name)
            continue
        strip = f"/tmp/_tplstrip_{name}.png"
        sh("ffmpeg", "-y", "-v", "error", *sum([["-i", c] for c in cells], []),
           "-filter_complex", f"hstack=inputs={len(cells)}", strip)
        sh("ffmpeg", "-y", "-v", "error", "-i", strip, "-vf", "scale=1200:-1",
           "-quality", "80", dst)
        for c in cells:
            os.remove(c)
        print("  %-26s -> %s (%.0f KB)"
              % (name, os.path.basename(dst), os.path.getsize(dst) / 1024))

    print("\ndone. showcase images in %s" % OUT)


if __name__ == "__main__":
    main()
