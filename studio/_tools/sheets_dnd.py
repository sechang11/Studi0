#!/usr/bin/env python3
"""Render the five reference sheets THE SALT ROAD needs, then report what landed.

    python3 sheets_dnd.py            # render all five
    python3 sheets_dnd.py --only BRENNA

A sheet is how epic.py holds a face across a hundred shots: it is fed to the keyframe
stage as an IPAdapter reference, so whatever is IN the sheet is what the film inherits.
That cuts both ways and this project has been bitten by it before - a reference sheet
imports its STYLE and its MEDIUM along with its face, so a sheet drawn in the wrong idiom
quietly restyles the entire film.

So every sheet here is rendered in the exact style string the film will use, and on the
same engine, rather than in whatever looks nicest on its own.

Framing is a bust-to-waist portrait on a plain backdrop. NOT a turnaround: an uncaptioned
turnaround backdrop once got absorbed into a trigger word and dragged its taupe background
into every later render.
"""
import argparse, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/k4shix/shared/comfy-studio"
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, HOST, COMFY   # noqa: E402

STYLE = ("dark fantasy tabletop illustration, painted in gouache and ink, heavy shadow, "
         "warm lamplight against cold stone, muted earth palette with one accent colour, "
         "detailed faces, painterly brushwork, the look of a roleplaying rulebook plate")

NEG = ("photograph, 3d render, cgi, plastic, blurry, lowres, watermark, text, signature, "
       "extra fingers, deformed hands, multiple heads, duplicate, frame, border")

CAST = {
    "BRENNA": (
        "a human woman sellsword in her late thirties, broad shouldered and weathered, "
        "short dark hair cut rough, a pale scar through her left eyebrow, battered iron "
        "ring-mail over a dark red gambeson, a plain longsword at her hip, "
        "calm level stare, unimpressed"),
    "MIRIEL": (
        "a young elf wizard, slight and narrow shouldered, long straight silver-blond hair, "
        "very pale grey eyes, ink stains on her fingers, a travelling coat of faded blue "
        "wool over a scholar's tunic, a leather satchel of scrolls, curious and alert"),
    "DURGAN": (
        "an old dwarf cleric, thick grey beard braided with iron rings, deep lines around "
        "the eyes, a dented steel breastplate over brown robes, a battered warhammer, "
        "a tarnished holy symbol of a setting sun on a chain, tired and patient"),
    "SKIVV": (
        "a halfling rogue, small and wiry, a mess of curly ginger hair, a crooked grin, "
        "freckles, a patched green cloak over dark leathers, many small pouches, "
        "a thin dagger held loosely, cheerful and entirely untrustworthy"),
    "VESSARAX": (
        "an enormous ancient green dragon, moss-dark scales dulled with age, one eye milky "
        "and blind, a heavy iron collar and broken chain around the neck, folded tattered "
        "wings, lying in darkness, immense and weary and watchful"),
}


def render(name, desc, seed):
    wf = load_wf("13_qwen_t2i_styled.json")
    prompt = "%s. %s. Bust portrait, centred, plain dark stone backdrop, even light." % (
        desc, STYLE)
    set_path(wf, "10.inputs.text", prompt)
    set_path(wf, "11.inputs.text", NEG)
    set_path(wf, "12.inputs.width", 1024)
    set_path(wf, "12.inputs.height", 1344)
    set_path(wf, "13.inputs.seed", seed)
    set_path(wf, "7.inputs.strength_model", 0.0)     # words only, no style LoRA
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/sheets/%s" % name.lower())
    t0 = time.time()
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        return None, 0
    dest = os.path.join(COMFY, "input", "sheet_dnd_%s.png" % name.lower())
    got = ensure_local(outs[0], dest, required=True)
    return got, round(time.time() - t0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--seed", type=int, default=7311)
    a = ap.parse_args()
    todo = {a.only: CAST[a.only]} if a.only else CAST
    for i, (name, desc) in enumerate(todo.items()):
        p, secs = render(name, desc, a.seed + i * 17)
        print("%-9s %-58s %ss" % (name, (p or "FAILED")[-58:], secs))


if __name__ == "__main__":
    main()
