#!/usr/bin/env python3
"""studio/_tools/model_atlas.py - every model ComfyUI knows about, and which ones we have.

    python3 studio/_tools/model_atlas.py            # build + print coverage
    python3 studio/_tools/model_atlas.py --quiet

WHY THIS IS NOT /capabilities OR /encyclopedia. Those two look INWARD - what this box can
do, and which graph does it. This looks OUTWARD: the field of open models, with ours
marked. It answers the question neither of them can, which is "what should I download
next, and what would it get me".

SOURCES, in order of trust:

  ComfyUI-Manager model-list.json   538 entries, each with a type, a base family, a
                                    filename, a size and a download URL. This is the
                                    canonical "what can this program run" list and it
                                    ships with the install, so it is not my recollection.
  the models tree on disk           what is ACTUALLY here, by filename
  studio/models/*.json              our 52 cards, which carry measured status

HAVE IS DECIDED BY FILENAME ON DISK, not by name matching. A list entry called "FLUX.1
[dev] Diffusion Model" and a file called flux1-dev.safetensors have nothing textually in
common, and every id-matching attempt in this project has produced a confident wrong
answer. The filename is the only thing both sides agree on.

WHAT THIS FILE DOES NOT DO is invent release dates. The manager list has no dates, and
guessing them would be exactly the failure this project keeps catching. Dates and the
"what makes it special" line come from a separate authored layer (ATLAS_NOTES), and
anything without one says so rather than making one up.
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
COMFY = os.path.expanduser(os.environ.get("COMFY_ROOT", "~/ComfyUI"))
MANAGER_LIST = os.path.join(COMFY, "custom_nodes", "ComfyUI-Manager", "model-list.json")
OUT = os.path.join(STUDIO, "samples", "_atlas.json")

# The families worth grouping by, in the order a film-maker cares about them. Anything
# whose base is not named here lands in "other" rather than being dropped.
FAMILY = [
    ("image", ["SDXL", "SD1.5", "SD1.x", "SD2.x", "FLUX.1", "FLUX.2", "Qwen-Image",
               "Qwen-Image-Edit", "Stable Cascade", "SD3", "SD3.5", "PixArt", "Kolors",
               "HiDream", "Z-Image", "Illustrious", "Pony", "AuraFlow", "Lumina"]),
    ("video", ["LTX-Video", "LTX-2", "Wan2.1", "Wan2.2", "HunyuanVideo", "Mochi",
               "CogVideoX", "SVD", "AnimateDiff", "animatediff", "Hunyuan Video"]),
    ("audio", ["Stable Audio", "ACE-Step", "AudioLDM", "MusicGen", "Higgs", "IndexTTS",
               "F5-TTS", "VibeVoice", "Chatterbox"]),
    ("3d", ["Hunyuan3D", "TripoSG", "SF3D", "CRM", "Zero123", "TRELLIS"]),
    ("control", ["ControlNet", "T2I-Adapter", "IP-Adapter", "SAM", "Ultralytics",
                 "insightface", "clip_vision"]),
    ("upscale", ["upscale", "TAESD", "ESRGAN", "SeedVR"]),
    ("text", ["t5", "clip", "CLIP", "llm", "LLM"]),
]


def family_of(base, mtype):
    b = str(base or "")
    for fam, keys in FAMILY:
        for k in keys:
            if k.lower() in b.lower():
                return fam
    t = str(mtype or "").lower()
    if t in ("controlnet", "t2i-adapter", "ip-adapter", "ultralytics", "insightface"):
        return "control"
    if t in ("upscale", "taesd"):
        return "upscale"
    if t in ("clip", "clip_vision"):
        return "text"
    if t == "vae":
        return "vae"
    if t == "lora":
        return "lora"
    return "other"


def on_disk():
    """{filename: relative path} for every weights file under the models tree."""
    out = {}
    root = os.path.join(COMFY, "models")
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if fn.lower().endswith((".safetensors", ".ckpt", ".pt", ".pth", ".bin",
                                    ".gguf", ".sft", ".onnx")):
                out.setdefault(fn, os.path.relpath(os.path.join(dirpath, fn), root))
    return out


def our_cards():
    by_file = {}
    for p in glob.glob(os.path.join(STUDIO, "models", "*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if d.get("file"):
            by_file[d["file"]] = d
    return by_file


def main():
    ap = argparse.ArgumentParser(description="Every model ComfyUI knows, and ours.")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(MANAGER_LIST):
        print("ComfyUI-Manager model list not found at %s" % MANAGER_LIST, file=sys.stderr)
        return 2
    raw = json.load(open(MANAGER_LIST, encoding="utf-8"))
    entries = raw.get("models") or raw

    disk, cards = on_disk(), our_cards()
    rows, fams = [], {}
    for e in entries:
        fn = e.get("filename") or ""
        path = disk.get(fn)
        card = cards.get(fn)
        fam = family_of(e.get("base"), e.get("type"))
        rows.append({
            "name": e.get("name"), "type": e.get("type"), "base": e.get("base"),
            "family": fam, "filename": fn, "size": e.get("size"),
            "description": e.get("description"), "reference": e.get("reference"),
            "url": e.get("url"), "save_path": e.get("save_path"),
            "have": bool(path), "path": path,
            "card": card.get("id") if card else None,
            "status": card.get("status") if card else None,
        })
        fams.setdefault(fam, []).append(rows[-1])

    # what we have that the manager list has never heard of - the interesting half
    listed = {r["filename"] for r in rows if r["filename"]}
    extra = []
    for fn, rel in sorted(disk.items()):
        if fn in listed:
            continue
        card = cards.get(fn)
        extra.append({"filename": fn, "path": rel,
                      "card": card.get("id") if card else None,
                      "status": card.get("status") if card else None,
                      "size_gb": card.get("size_gb") if card else None})

    # The authored layer: release dates and what each model is FOR, which the catalogue
    # does not carry. Each note says where its facts came from; a note whose model we
    # cannot find on disk still shows, because "what we do NOT have" is half the point
    # of an atlas.
    notes, prov = [], {}
    np_ = os.path.join(STUDIO, "atlas_notes.json")
    if os.path.exists(np_):
        nd = json.load(open(np_, encoding="utf-8"))
        prov = nd.get("provenance_key") or {}
        # Carried through UNTOUCHED. atlas_notes decides HAVE by naming model cards
        # explicitly; an earlier version of this loop recomputed it by looking for the
        # note's key inside our filenames - the same guess that reported FLUX.2 as not
        # installed - and overwrote the good answer with it.
        for n in nd.get("notes") or []:
            notes.append(dict(n))

    doc = {
        "generated": __import__("time").strftime("%Y-%m-%d %H:%M"),
        "generator": "studio/_tools/model_atlas.py",
        "notes": notes,
        "provenance_key": prov,
        "sources": {
            "catalogue": os.path.relpath(MANAGER_LIST, os.path.dirname(COMFY)),
            "disk": "ComfyUI/models/**",
            "cards": "studio/models/*.json",
        },
        "note": ("The field of open models with ours marked. HAVE is decided by FILENAME "
                 "on disk, never by name matching - a list entry called 'FLUX.1 [dev]' "
                 "and a file called flux1-dev.safetensors share no text, and every "
                 "id-matching attempt in this project has produced a wrong answer. "
                 "Release dates are NOT in the catalogue and are not invented here."),
        "models": rows,
        "not_in_catalogue": extra,
        "totals": {
            "catalogued": len(rows),
            "have": sum(1 for r in rows if r["have"]),
            "carded": sum(1 for r in rows if r["card"]),
            "on_disk_uncatalogued": len(extra),
        },
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(doc, open(OUT, "w", encoding="utf-8"), indent=1)

    if a.quiet:
        return 0
    t = doc["totals"]
    print("catalogue %d models · we have %d · %d of those have a card"
          % (t["catalogued"], t["have"], t["carded"]))
    print("%d weights on disk the catalogue has never heard of\n" % t["on_disk_uncatalogued"])
    print("%-9s %6s %6s   %s" % ("family", "listed", "have", "what we have"))
    print("-" * 78)
    for fam in sorted(fams, key=lambda f: -sum(1 for r in fams[f] if r["have"])):
        got = [r for r in fams[fam] if r["have"]]
        print("%-9s %6d %6d   %s"
              % (fam, len(fams[fam]), len(got),
                 ", ".join(sorted(r["filename"][:26] for r in got))[:44]))
    print("\n-> %s" % OUT)
    return 0


def main_quiet():
    """Rebuild without printing, for the route."""
    import contextlib
    import io as _io
    with contextlib.redirect_stdout(_io.StringIO()):
        sys.argv = [sys.argv[0], "--quiet"]
        return main()


if __name__ == "__main__":
    sys.exit(main())
