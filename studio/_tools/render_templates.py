#!/usr/bin/env python3
"""Render each template's showcase strip, THROUGH THE LAYER RESOLVER.

    python3 studio/_tools/render_templates.py              # all, skip ones already done
    python3 studio/_tools/render_templates.py --force
    python3 studio/_tools/render_templates.py photographic_   # prefix match
    python3 studio/_tools/render_templates.py --engine qwen   # only the photographic set
    python3 studio/_tools/render_templates.py --dry           # print prompts, render nothing

A template is the fastest path into this app - the wizard opens on a gallery of them and
one click pre-fills every variable - so its picture has to be the real thing.

Each template's shots are rendered as keyframes and tiled into one strip, so the card shows
the template's ARC rather than a single frame. Roughly 5s of GPU per shot.

WHY THIS WAS REWRITTEN. The previous version hardcoded animagine-xl-4.0 as the checkpoint
and pasted the literal string "modern sports anime, cel shading, cinematic" onto the end of
every prompt. That was fine when all 20 templates were one anime look. It stopped being
fine the moment templates started naming a STYLE: it would have rendered all 62 new cards -
including the 17 photographic ones written for Qwen - on the anime model with cel-shading
tags appended after each style's own tags. The gallery would have come back a single look
again, and it would have looked like success.

The same bug had already been found one layer up, in the wizard: applyTemplate() left the
default house tags in place, so a watercolour template compiled to
"...wet-on-wet, bleeding colours, soft edges, paper texture, modern sports anime, cel
shading, cinematic". Cel shading is the exact opposite of wet-on-wet, and it landed last.

So this now goes through studio/compose.py's resolve() - the same function compile.py and
POST /api/compose use. One resolver, three consumers. A thumbnail that disagrees with what
the film renders is worse than no thumbnail, because it is a promise the app cannot keep.

ENGINE ROUTING IS THE POINT. resolve() returns the engine the style demands, and this
dispatches on it: anime to animagine reading danbooru tags, qwen to Qwen-Image reading
prose, with the style LoRA loaded when the resolver says one applies. Qwen cannot be
steered off photography by prompt at any cfg, so a photographic template rendered on the
anime path is not merely off-style, it is a different medium.

ISOLATION. The subject is held FIXED across every template - same character description,
same seed - so differences between showcase images are differences between TEMPLATES rather
than lottery. Same discipline as the capability cards.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, STUDIO)
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, HOST          # noqa: E402
import compose                                        # noqa: E402

TPL = os.path.join(STUDIO, "templates")
OUT = os.path.join(STUDIO, "samples", "templates")
SEED = 7700

# The held-constant subject, in each engine's dialect. A template is about the SHAPE of a
# scene, not about who is in it, so the person must not vary between cards.
SUBJ_TAGS = "1boy, solo, short dark hair, plain jacket"
SUBJ_PROSE = "a young man in a plain jacket"
Q = "masterpiece, best quality, very aesthetic, absurdres"

# Shot templates that are deliberately empty of people. A place card also carries
# "no humans, scenery" for these, and putting a figure in an establishing shot defeats it.
PEOPLELESS = ("establish", "insert", "pillow")

GROUPS = ("styles", "places", "looks", "characters", "loras", "emotions", "cues",
          "weather", "lighting", "wear", "cameras", "transitions", "shots", "templates")


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def load_libs():
    libs = {}
    for g in GROUPS:
        d = os.path.join(STUDIO, g)
        libs[g] = {}
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(d, fn), encoding="utf-8") as f:
                    libs[g][fn[:-5]] = json.load(f)
            except Exception:
                pass
    return libs


def keyframe(r, tag, peopleless):
    """Render one resolved shot on whichever engine the resolver chose."""
    prompt, neg = r["prompt"], r.get("negative") or ""
    if r["engine"] == "qwen":
        wf = load_wf("13_qwen_t2i_styled.json")
        body = prompt if peopleless else (SUBJ_PROSE + ". " + prompt)
        set_path(wf, "10.inputs.text", body)
        set_path(wf, "11.inputs.text", neg)
        set_path(wf, "12.inputs.width", 1344)
        set_path(wf, "12.inputs.height", 768)
        set_path(wf, "13.inputs.seed", SEED)
        # Node 7 is the style-LoRA slot and now defaults to strength 0. Load only what the
        # resolver actually resolved - it has already refused any LoRA on the wrong base.
        if r.get("style_lora") and r.get("style_lora_active"):
            set_path(wf, "7.inputs.lora_name", r["style_lora"])
            set_path(wf, "7.inputs.strength_model", float(r.get("style_lora_strength") or 1.0))
        else:
            set_path(wf, "7.inputs.strength_model", 0.0)
        prefix, node = "15.inputs.filename_prefix", None
    else:
        wf = load_wf("22_anime_kf_ipadapter.json")
        set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
        set_path(wf, "4.inputs.weight", 0.0)
        body = prompt if peopleless else (SUBJ_TAGS + ", " + prompt)
        if Q not in body:
            body = body + ", " + Q
        set_path(wf, "5.inputs.text", body)
        set_path(wf, "6.inputs.text", neg or "lowres, worst quality, bad anatomy, watermark, text")
        set_path(wf, "8.inputs.seed", SEED)
        for n in ("7", "10"):
            set_path(wf, f"{n}.inputs.width", 1344)
            set_path(wf, f"{n}.inputs.height", 768)
        prefix, node = "11.inputs.filename_prefix", None
    set_path(wf, prefix, f"claude-generated/studio_templates/{tag}")
    _, outs = run(HOST, wf, quiet=True)
    return outs[0] if outs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("only", nargs="?")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--engine", choices=["anime", "qwen"])
    ap.add_argument("--dry", action="store_true",
                    help="resolve and print, render nothing - use to sanity-check routing")
    a = ap.parse_args()

    if not os.path.isdir(TPL):
        raise SystemExit(f"no templates at {TPL}")
    os.makedirs(OUT, exist_ok=True)
    libs = load_libs()

    names = sorted(f[:-5] for f in os.listdir(TPL) if f.endswith(".json"))
    if a.only:
        names = [n for n in names if n == a.only or n.startswith(a.only)]

    made = skipped = failed = 0
    routed = {}
    for name in names:
        t = json.load(open(os.path.join(TPL, name + ".json"), encoding="utf-8"))
        sets, shots = t.get("sets", {}), t.get("shots", [])
        if not shots:
            print("  %-34s no shots" % name)
            continue

        # Resolve once up front just to learn the engine, so --engine can filter without
        # paying for a render, and so the routing is visible in the log.
        head = compose.resolve(libs, {"style": sets.get("style"),
                                      "place": sets.get("place"),
                                      "look": sets.get("look")})
        eng = head["engine"]
        routed[eng] = routed.get(eng, 0) + 1
        if a.engine and eng != a.engine:
            continue

        dst = os.path.join(OUT, name + ".webp")
        if os.path.exists(dst) and not a.force:
            skipped += 1
            continue

        look = libs["looks"].get(sets.get("look", ""), {})
        cells = []
        for i, sh_ in enumerate(shots):
            peopleless = sh_.get("template") in PEOPLELESS
            sel = {
                "style":     sets.get("style"),
                "place":     sets.get("place"),
                "look":      sets.get("look"),
                "wear":      sets.get("wear"),
                "lighting":  sets.get("lighting"),
                "weather":   sets.get("weather"),
                "emotion":   None if peopleless else sets.get("emotion"),
                "desc":      (sh_.get("desc") or "").strip(),
                "template":  sh_.get("template"),
                "camera":    sh_.get("camera") or sets.get("camera"),
                "style_lora": sets.get("style_lora"),
            }
            r = compose.resolve(libs, sel)
            errs = [c for c in r.get("conflicts", []) if c.get("severity") == "error"]
            if errs:
                print("  %-34s shot %d ERROR: %s" % (name, i + 1, errs[0]["message"][:70]))
            if a.dry:
                print("  %-34s %-5s shot %d: %s" % (name, r["engine"], i + 1, r["prompt"][:110]))
                continue
            tag = f"{name}_{i}"
            print("  %-34s %-5s shot %d/%d" % (name, r["engine"], i + 1, len(shots)), flush=True)
            try:
                rel = keyframe(r, tag, peopleless)
            except Exception as e:
                print("     FAILED: %s" % str(e)[:110])
                continue
            if not rel:
                continue
            local = ensure_local(rel, f"/tmp/_tpl_{tag}.png", required=False)
            if not local:
                continue
            # The template's own grade, so the showcase shows the colour you will actually
            # get. Looks are deterministic ffmpeg, applied after generation - not prompt.
            grade = look.get("grade") or "eq=contrast=1.06:saturation=1.12"
            cell = f"/tmp/_tplc_{tag}.png"
            sh("ffmpeg", "-y", "-v", "error", "-i", local, "-vf", f"{grade},scale=380:-1", cell)
            try:
                os.remove(local)
            except OSError:
                pass
            if os.path.exists(cell):
                cells.append(cell)

        if a.dry:
            continue
        if not cells:
            print("  %-34s produced nothing" % name)
            failed += 1
            continue
        strip = f"/tmp/_tplstrip_{name}.png"
        sh("ffmpeg", "-y", "-v", "error", *sum([["-i", c] for c in cells], []),
           "-filter_complex", f"hstack=inputs={len(cells)}", strip)
        sh("ffmpeg", "-y", "-v", "error", "-i", strip, "-vf", "scale=1200:-1",
           "-quality", "84", dst)
        for c in cells:
            try:
                os.remove(c)
            except OSError:
                pass
        if os.path.exists(dst):
            made += 1
            print("  %-34s -> %.0f KB" % (name, os.path.getsize(dst) / 1024))
        else:
            failed += 1

    print("\n%d rendered, %d already there, %d failed" % (made, skipped, failed))
    print("engine routing across the whole set: %s" % routed)
    if routed.get("qwen"):
        print("The photographic templates went to Qwen. Before this rewrite every one of "
              "them would have been rendered on animagine with cel-shading tags appended.")


if __name__ == "__main__":
    main()
