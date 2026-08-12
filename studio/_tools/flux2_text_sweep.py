#!/usr/bin/env python3
"""studio/_tools/flux2_text_sweep.py - can FLUX.2 actually spell, and what makes it?

    python3 studio/_tools/flux2_text_sweep.py

WHY. Ten flux2 style cards were written on the claim that FLUX.2's strength is typography.
The proofs came back as beautiful physical media carrying GIBBERISH - "VITREQUS SHOP",
"Bagike Menu", "KNACK ENMETHLES". The medium was right and the words were not.

Two candidate causes, and this separates them instead of guessing:

  QUOTED TEXT. Every one of those prompts described lettering without saying what it
  should SAY - "a title line in bold", "a headline". The model was asked to invent words,
  and invented word-shaped noise. The fix, if this is it, is to quote the exact string.

  STEP COUNT. The measured settings were turbo at 4-8 steps. Fine detail is the first
  thing a short schedule loses, and glyphs are fine detail.

Grid: {quoted, unquoted} x {4, 8, 16, 30 steps}, one seed, everything else fixed. The
answer is read off the pixels - a contact sheet - not off a metric, because "did it spell
CLOSED" is a question only looking can settle.
"""
import json, os, sys, time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
OUT = os.path.join(STUDIO, "samples", "flux2_text")

BASE = ("A photograph of a vitreous enamel shop sign screwed to a brick wall. The sign is "
        "deep blue with cream lettering in a bold grotesque face, chipped along the bottom "
        "edge where the steel shows rust through the enamel. Raking afternoon light from "
        "the left, the brick out of focus behind. Shot on 85mm at f2.8, natural colour.")

QUOTED = BASE.replace(
    "cream lettering in a bold grotesque face",
    'cream lettering in a bold grotesque face reading exactly "NIGHT PORTER" on the first '
    'line and "RING TWICE" on the second')

STEPS = [4, 8, 16, 30]
SEED = 5150


def render(prompt, steps, tag):
    from comfy import run                                    # noqa: E402
    from epic import load_wf, ensure_local, HOST             # noqa: E402
    wf = load_wf("40_flux2_t2i.json")
    # BY INPUT KEY, not class name. The first version of this matched "Sampler" for steps
    # and seed; on this graph steps live on Flux2Scheduler and the seed is `noise_seed` on
    # RandomNoise, so NEITHER was ever set and the sweep returned four pixel-identical
    # frames per row while reporting eight successes. Only the embedded PNG metadata
    # differed, which is what made the file hashes look distinct.
    touched = {"steps": 0, "seed": 0}
    for nid, n in wf.items():
        if not isinstance(n, dict):
            continue
        ct, ins = n.get("class_type", ""), n.get("inputs")
        if not isinstance(ins, dict):
            continue
        if ("CLIPTextEncode" in ct or "TextEncode" in ct) and "text" in ins:
            ins["text"] = prompt
        for k in ("noise_seed", "seed"):
            if k in ins:
                ins[k] = SEED
                touched["seed"] += 1
        if "steps" in ins:
            ins["steps"] = steps
            touched["steps"] += 1
        if "width" in ins and "height" in ins:
            ins["width"], ins["height"] = 1024, 1024
        if ct == "SaveImage":
            ins["filename_prefix"] = "claude-generated/flux2text/%s" % tag
    # Refuse to run a sweep whose axis was never applied. A sweep that silently varies
    # nothing is worse than no sweep - it produces a confident answer to a question that
    # was never asked.
    if not touched["steps"] or not touched["seed"]:
        raise SystemExit("the graph exposes no %s input - sweep would be meaningless"
                         % (" and no ".join(k for k, v in touched.items() if not v)))
    t = time.time()
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        return None, 0
    dst = os.path.join(OUT, "%s.png" % tag)
    return ensure_local(outs[0], dst, required=False), time.time() - t


def main():
    # argparse even though there are no options yet. Without it this tool runs its entire
    # 8-render job on ANY argument, including --help - the hazard audit.py flags across
    # ~20 tools here. Adding one more to that pile while fixing the pile is not on.
    import argparse
    argparse.ArgumentParser(
        description="Does FLUX.2 spell? Sweeps quoted vs unquoted text across step "
                    "counts and writes a contact sheet.").parse_args()
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for label, prompt in (("quoted", QUOTED), ("unquoted", BASE)):
        for s in STEPS:
            tag = "%s_s%02d" % (label, s)
            got, secs = render(prompt, s, tag)
            print("  %-14s %5.1fs  %s" % (tag, secs, "ok" if got else "FAILED"))
            rows.append({"cell": tag, "quoted": label == "quoted", "steps": s,
                         "seconds": round(secs, 1), "file": got})
    with open(os.path.join(OUT, "_sweep.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1)

    # Hash the PIXELS, never the file. A PNG embeds the workflow, so changing only the
    # filename_prefix gives every file a different md5 while the image is byte-identical -
    # which is exactly how the first run of this sweep looked like eight distinct results
    # and was really two.
    import hashlib
    from PIL import Image as _I
    seen = {}
    for r in rows:
        if r["file"] and os.path.isfile(r["file"]):
            h = hashlib.md5(_I.open(r["file"]).convert("RGB").tobytes()).hexdigest()[:12]
            r["pixels"] = h
            seen.setdefault(h, []).append(r["cell"])
    dupes = {h: c for h, c in seen.items() if len(c) > 1}
    print("\n  %d distinct images from %d renders" % (len(seen), len(rows)))
    for h, cells in dupes.items():
        print("  IDENTICAL: %s" % ", ".join(cells))

    from PIL import Image, ImageDraw
    cell, cols = 512, len(STEPS)
    sheet = Image.new("RGB", (cols * cell, 2 * cell + 60), (20, 22, 27))
    d = ImageDraw.Draw(sheet)
    for i, r in enumerate(rows):
        if not r["file"] or not os.path.isfile(r["file"]):
            continue
        im = Image.open(r["file"]).convert("RGB")
        im.thumbnail((cell - 8, cell - 8))
        x = (i % cols) * cell + 4
        y = (i // cols) * cell + 34
        sheet.paste(im, (x, y))
        d.text((x + 6, y - 22), r["cell"], fill=(230, 233, 239))
    p = os.path.join(OUT, "_sheet.jpg")
    sheet.save(p, quality=90)
    print("\n  %s" % p)
    print("  Read the SIGN, not the picture. The question is whether it says NIGHT PORTER.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
