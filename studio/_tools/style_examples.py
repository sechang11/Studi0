#!/usr/bin/env python3
"""Render every style on the engine it routes to, so a style can be chosen by looking.

    python3 studio/_tools/style_examples.py
    python3 studio/_tools/style_examples.py --family anime
    python3 studio/_tools/style_examples.py photorealistic

THE WHOLE LIBRARY SHIPPED `untested`. 64 cards were authored without a single render, and
every strength rating on them is a prediction from documented behaviour. This is the tool
that turns them into findings. Until it has run on a card, that card is someone's opinion.

ISOLATION. One subject, one seed, one setting, for all 64. Only the style changes. That is
the entire discipline here and this project has broken it repeatedly - 133 of 134 capability
cards varied the subject alongside the variable and so demonstrated nothing. A grid where
each cell has a different person in a different place cannot tell you what a style does.

The subject is deliberately chosen to expose style rather than flatter it: a single figure,
mid-shot, with a FACE (where rendering idiom shows first), a GARMENT with folds (where line
and shading show), and a receding street (where depth handling and palette show). A
landscape would hide all three.

ENGINE. Each card names the model that can render it at all, and this dispatches on that
field rather than on a flag - which is the point of `engine` existing. anime -> animagine
reading tags, qwen -> Qwen-Image reading prose. `either` renders BOTH, because for those
cards the interesting fact is the difference.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, HOST          # noqa: E402

STYLES = os.path.join(STUDIO, "styles")
OUT = os.path.join(STUDIO, "samples", "styles")
SEED = 5150

# The held-constant subject. Same content on both paths, in each engine's dialect, so an
# anime card and a qwen card are still showing the same scene.
SUBJ_TAGS  = ("1girl, solo, upper body, long dark hair, red scarf, wool coat, "
              "standing, looking at viewer, city street, buildings, overcast")
SUBJ_PROSE = ("a young woman in a wool coat and red scarf standing on a city street, "
              "buildings receding behind her, overcast daylight, facing the camera")
Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG_BASE = "lowres, worst quality, bad anatomy, bad hands, watermark, text, signature"


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def build(st, engine):
    """Subject first, style appended. Tag order is load-bearing in this project - the
    earlier and more specific tag wins - so the subject anchors the frame and the style
    modifies it, not the reverse."""
    neg = NEG_BASE
    if st.get("negative_add"):
        neg = neg + ", " + st["negative_add"]
    if engine == "anime":
        wf = load_wf("22_anime_kf_ipadapter.json")
        set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
        set_path(wf, "4.inputs.weight", 0.0)
        parts = [SUBJ_TAGS]
        if st.get("tags"):
            parts.append(st["tags"])
        parts.append(Q)
        set_path(wf, "5.inputs.text", ", ".join(parts))
        set_path(wf, "6.inputs.text", neg)
        set_path(wf, "8.inputs.seed", SEED)
        for n in ("7", "10"):
            set_path(wf, "%s.inputs.width" % n, 1024)
            set_path(wf, "%s.inputs.height" % n, 1024)
        return wf, "11.inputs.filename_prefix"
    wf = load_wf("13_qwen_t2i_styled.json")
    prose = SUBJ_PROSE
    if st.get("prose"):
        prose = prose + ". " + st["prose"]
    set_path(wf, "10.inputs.text", prose)
    set_path(wf, "11.inputs.text", neg)
    set_path(wf, "12.inputs.width", 1024)
    set_path(wf, "12.inputs.height", 1024)
    set_path(wf, "13.inputs.seed", SEED)
    return wf, "15.inputs.filename_prefix"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("only", nargs="?")
    ap.add_argument("--family")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--all-engines", action="store_true",
                    help="render every style on BOTH engines regardless of its "
                         "engine field, so the routing can be decided from pixels "
                         "rather than from the card's claim")
    a = ap.parse_args()

    names = sorted(f[:-5] for f in os.listdir(STYLES) if f.endswith(".json"))
    if a.only:
        names = [n for n in names if n == a.only or n.startswith(a.only)]
    os.makedirs(OUT, exist_ok=True)

    made = skipped = failed = 0
    for name in names:
        p = os.path.join(STYLES, name + ".json")
        st = json.load(open(p, encoding="utf-8"))
        if a.family and st.get("family") != a.family:
            continue
        want = (["anime", "qwen"] if (a.all_engines or st.get("engine") == "either")
                else [st.get("engine", "qwen")])
        for eng in want:
            dst = os.path.join(OUT, "%s__%s.webp" % (name, eng))
            if os.path.exists(dst) and not a.force:
                skipped += 1
                continue
            wf, prefix = build(st, eng)
            set_path(wf, prefix, "claude-generated/studio_styles/%s_%s" % (name, eng))
            try:
                _, outs = run(HOST, wf, quiet=True)
            except Exception as e:
                print("  %-26s %-5s FAILED %s" % (name, eng, str(e)[:60]), flush=True)
                failed += 1
                continue
            if not outs:
                print("  %-26s %-5s no output" % (name, eng), flush=True)
                failed += 1
                continue
            loc = ensure_local(outs[0], "/tmp/_st_%s_%s.png" % (name, eng), required=False)
            if not loc:
                failed += 1
                continue
            sh("ffmpeg", "-y", "-v", "error", "-i", loc, "-vf", "scale=680:-1",
               "-quality", "80", dst)
            try:
                os.remove(loc)
            except OSError:
                pass
            if os.path.exists(dst):
                made += 1
                print("  %-26s %-5s %5.0f KB" % (name, eng, os.path.getsize(dst) / 1024),
                      flush=True)
            else:
                failed += 1
        ex = {}
        for eng in ("anime", "qwen"):
            f = os.path.join(OUT, "%s__%s.webp" % (name, eng))
            if os.path.exists(f):
                ex[eng] = "/samples/styles/%s__%s.webp" % (name, eng)
        if ex:
            st["examples"] = ex
            # serve.py's library() looks for samples/<group>/<id>.<ext> exactly, so the
            # per-engine filenames are invisible to it. Give it the routed engine's pass
            # under the plain name as the card thumbnail.
            plain = os.path.join(OUT, name + ".webp")
            first = ex.get(st.get("engine")) or ex.get("anime") or ex.get("qwen")
            srcf = os.path.join(OUT, os.path.basename(first))
            if os.path.exists(srcf) and not os.path.exists(plain):
                sh("cp", srcf, plain)
            json.dump(st, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
            open(p, "a").write("\n")

    print("\n%d rendered, %d already there, %d failed" % (made, skipped, failed))
    print("\nNOW LOOK AT THEM. Every card still says status=untested and that is correct "
          "until someone has compared these against the plain subject and against each "
          "other. A render is not a verification.")


if __name__ == "__main__":
    main()
