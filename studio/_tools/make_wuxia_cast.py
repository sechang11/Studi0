#!/usr/bin/env python3
"""Author the two wuxia leads and render their reference sheets.

    python3 studio/_tools/make_wuxia_cast.py

WHY CARDS AND SHEETS FIRST. The wuxia style routes to the ANIME engine, which is the one
engine on this box where a trained character LoRA actually attaches - so the full identity
ladder is available: sheet, turnaround, dataset, weights. Two hours of output with nothing
holding the face would be two hours of people who merely resemble each other.

Both characters are invented. No real person, living or otherwise, is named, referenced or
used as a likeness source anywhere in this file.

TAGS, NOT PROSE. This engine reads danbooru tags. Base tags carry what never changes about
the person - that is the identity. Wear tags are a separate ladder so a costume can change
without the face changing with it.
"""
import json, os, sys, time

import argparse
argparse.ArgumentParser(description='make wuxia cast').parse_args()
# ^ the CLI contract: --help exits HERE, before any work below runs.
TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, HOST, COMFY   # noqa: E402

QUALITY = "masterpiece, best quality, very aesthetic, absurdres"
NEG = ("lowres, worst quality, bad anatomy, bad hands, missing fingers, extra digits, "
       "watermark, signature, text, jpeg artifacts, 2girls, 2boys, multiple views, "
       "duplicate, blurry")

CAST = {
    "LIWEN": {
        "name": "Bai Liwen",
        "desc": "A young swordswoman of the Cloud Terrace school. Quick, watchful, and "
                "better at the sword than at saying so.",
        "base_tags": ("1girl, solo, east asian, young woman, long black hair, "
                      "very long hair, straight hair, hair ornament, jade hairpin, "
                      "brown eyes, pale skin, slender, delicate features, beautiful"),
        "wear": ("white and jade-green hanfu, flowing silk sleeves, wide sash, "
                 "layered robes, straight sword at the hip"),
    },
    "SHEN": {
        "name": "Shen Yuan",
        "desc": "A wandering swordsman with a debt he does not discuss. Calm, dry, and "
                "slower to draw than anyone expects.",
        "base_tags": ("1boy, solo, east asian, young man, black hair, long hair, "
                      "high ponytail, dark eyes, sharp features, tall, lean, handsome"),
        "wear": ("dark blue and black hanfu, travelling robes, leather belt, "
                 "arm wraps, jian sword across the back"),
    },
}

WUXIA = ("wuxia, chinese clothes, flowing silk, misty mountains, jade, vermilion, "
         "ethereal")


def sheet(cid, c, seed):
    """A bust portrait on a plain backdrop - the identity anchor everything else reads."""
    tags = "%s, %s, %s, upper body, looking at viewer, plain grey background, %s" % (
        c["base_tags"], c["wear"], WUXIA, QUALITY)
    wf = load_wf("22_anime_kf_ipadapter.json")
    set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
    set_path(wf, "4.inputs.weight", 0.0)          # no reference yet; this IS the reference
    set_path(wf, "5.inputs.text", tags)
    set_path(wf, "6.inputs.text", NEG)
    set_path(wf, "8.inputs.seed", seed)
    for n in ("7", "10"):
        set_path(wf, "%s.inputs.width" % n, 1024)
        set_path(wf, "%s.inputs.height" % n, 1344)
    set_path(wf, "11.inputs.filename_prefix", "claude-generated/wuxia/%s" % cid.lower())
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        return None
    dst = os.path.join(COMFY, "input", "sheet_%s.png" % cid.lower())
    return ensure_local(outs[0], dst, required=False)


def main():
    for i, (cid, c) in enumerate(CAST.items()):
        got = sheet(cid, c, 8800 + i * 31)
        card = {
            "id": cid, "name": c["name"], "status": "ready",
            "desc": c["desc"],
            "prose": c["desc"],
            # Identity: what never changes. The engine reads these tags directly.
            "tags": c["base_tags"],
            "base_tags": c["base_tags"],
            # Wardrobe is a separate ladder so a costume can change without the face
            # changing with it. Rung 0 is clean; the rest are damage states.
            "wear_tags": [
                c["wear"] + ", clean and unmarked",
                c["wear"] + ", travel dust on the hem",
                c["wear"] + ", torn sleeve, dirt on the knee",
                c["wear"] + ", robes cut open at the shoulder, sash used as a bandage",
                c["wear"] + ", robes in rags, blood dried at the temple",
            ],
            "sheet": ("sheet_%s.png" % cid.lower()) if got else None,
            "provenance": "invented",
            "provenance_note": (
                "Invented for the wuxia set. No real person is referenced or used as a "
                "likeness source. Tags are authored for the anime engine, which is where "
                "the wuxia style card routes."),
            "note": ("Sheet rendered on animagine at 1024x1344. Identity ladder: sheet "
                     "done, turnaround and LoRA next. Nothing measured yet."),
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        p = os.path.join(STUDIO, "characters", "%s.json" % cid)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(card, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print("  %-7s %s" % (cid, got or "SHEET FAILED"))


if __name__ == "__main__":
    main()
