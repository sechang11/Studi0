#!/usr/bin/env python3
"""Render every place, on both engines, so a setting can be chosen by looking.

    python3 studio/_tools/place_examples.py                 # both engines, all places
    python3 studio/_tools/place_examples.py --engine qwen   # the non-anime pass
    python3 studio/_tools/place_examples.py pine_forest

Two passes, because the project has two image families and until now only one of them
has ever been used for anything:

  anime   animagine-xl-4.0 reading the place's `tags` (danbooru)
  qwen    Qwen-Image 2512 reading the place's `prose` (a sentence)

They want opposite prompt formats - feeding one the other's returns abstract colour
shapes - which is exactly why each place card carries both, and why the honest way to
choose between them is to see the same location rendered by each.

NO PEOPLE. A place card is about the place. Adding a figure means every comparison is
half about the figure, and the whole point is to answer "what does this location look
like" without anything else competing for the frame.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, HOST          # noqa: E402

PLACES = os.path.join(STUDIO, "places")
OUT = os.path.join(STUDIO, "samples", "places")
SEED = 3300
Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG_ANIME = ("1girl, 1boy, person, people, lowres, worst quality, watermark, text, "
             "signature, blurry")
NEG_QWEN = "people, figures, lowres, watermark, text, blurry"


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def build(place, engine):
    if engine == "anime":
        wf = load_wf("22_anime_kf_ipadapter.json")
        set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
        set_path(wf, "4.inputs.weight", 0.0)
        set_path(wf, "5.inputs.text",
                 "no humans, scenery, %s, %s" % (place["tags"], Q))
        set_path(wf, "6.inputs.text", NEG_ANIME)
        set_path(wf, "8.inputs.seed", SEED)
        for n in ("7", "10"):
            set_path(wf, "%s.inputs.width" % n, 1216)
            set_path(wf, "%s.inputs.height" % n, 704)
        return wf, "11.inputs.filename_prefix"
    wf = load_wf("13_qwen_t2i_styled.json")
    set_path(wf, "10.inputs.text", place.get("prose") or place["tags"])
    set_path(wf, "11.inputs.text", NEG_QWEN)
    set_path(wf, "12.inputs.width", 1216)
    set_path(wf, "12.inputs.height", 704)
    set_path(wf, "13.inputs.seed", SEED)
    return wf, "15.inputs.filename_prefix"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("only", nargs="?")
    ap.add_argument("--engine", choices=["anime", "qwen", "both"], default="both")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    names = sorted(f[:-5] for f in os.listdir(PLACES) if f.endswith(".json"))
    if a.only:
        names = [n for n in names if n == a.only or n.startswith(a.only)]
    engines = ["anime", "qwen"] if a.engine == "both" else [a.engine]
    os.makedirs(OUT, exist_ok=True)

    made = skipped = failed = 0
    for name in names:
        place = json.load(open(os.path.join(PLACES, name + ".json"), encoding="utf-8"))
        for eng in engines:
            dst = os.path.join(OUT, "%s__%s.webp" % (name, eng))
            if os.path.exists(dst) and not a.force:
                skipped += 1
                continue
            wf, prefix = build(place, eng)
            set_path(wf, prefix, "claude-generated/studio_places/%s_%s" % (name, eng))
            try:
                _, outs = run(HOST, wf, quiet=True)
            except Exception as e:
                print("  %-24s %-6s FAILED %s" % (name, eng, str(e)[:70]))
                failed += 1
                continue
            if not outs:
                failed += 1
                continue
            loc = ensure_local(outs[0], "/tmp/_pl_%s_%s.png" % (name, eng), required=False)
            if not loc:
                failed += 1
                continue
            sh("ffmpeg", "-y", "-v", "error", "-i", loc, "-vf", "scale=760:-1",
               "-quality", "80", dst)
            try:
                os.remove(loc)
            except OSError:
                pass
            if os.path.exists(dst):
                made += 1
                print("  %-24s %-6s %5.0f KB" % (name, eng, os.path.getsize(dst) / 1024),
                      flush=True)
            else:
                failed += 1
        # stamp whatever now exists onto the card, so the page needs no naming convention
        ex = {}
        for eng in ("anime", "qwen"):
            f = os.path.join(OUT, "%s__%s.webp" % (name, eng))
            if os.path.exists(f):
                ex[eng] = "/samples/places/%s__%s.webp" % (name, eng)
        if ex:
            place["examples"] = ex
            # serve.py's library() looks for samples/<group>/<id>.<ext> exactly, so the
            # per-engine names are invisible to it. Give it the anime pass under the
            # plain name as the card thumbnail.
            plain = os.path.join(OUT, name + ".webp")
            first = ex.get("anime") or ex.get("qwen")
            srcf = os.path.join(OUT, os.path.basename(first))
            if os.path.exists(srcf) and not os.path.exists(plain):
                sh("cp", srcf, plain)
            with open(os.path.join(PLACES, name + ".json"), "w", encoding="utf-8") as f:
                json.dump(place, f, indent=2, ensure_ascii=False)
                f.write("\n")

    print("\n%d rendered, %d already there, %d failed" % (made, skipped, failed))


if __name__ == "__main__":
    main()
