#!/usr/bin/env python3
"""Render a reference sheet for a bare character card on the ILLUSTRATION engine.

    python3 studio/_tools/make_anime_sheet.py NIKA BRACK PIP MANAGER
    python3 studio/_tools/make_anime_sheet.py NIKA --force --seed 4400

WHY THIS EXISTS

cast.html:155, compose.py:1134 and compile.py:675 all tell you to fix a missing sheet by
running `python3 scripts/make_sheets.py`. That command cannot be followed: make_sheets.py
takes a FILM as a required positional and reads the film's `designs` block, so run against
a bare character card it dies in argparse. There was no tool that sheets a character.

make_sheets.py is also a QWEN tool - it renders through 13_qwen_t2i_styled.json. A sheet
imports its STYLE into everything downstream as forcefully as it imports identity, which
is a measured fact in this project: sheet_viro.png produced a comic illustration in four
of four cells despite the prompt asking for a photograph. So an anime character needs an
anime sheet, and rendering one through a qwen workflow would poison every render that
references it. This uses 22_anime_kf_ipadapter.json - animagine-xl-4.0, the same engine
the anime keyframes render on.

THE NEGATIVE PROMPT IS THE POINT OF THIS FILE

Node 6 of 22_anime_kf_ipadapter.json hard-codes:

    1girl, girl, female, feminine, breasts, motion blur, ... , multiple boys, ...

That negative was written for two male footballers and is baked into the workflow. It is
not reachable from a character card or a film: compose.py assembles a negative and
returns it, but scripts/short.py plumbs no negative input on either keyframe workflow
(compose.py:71-73, 1836-1841). A female character rendered through the stock graph is
fought by her own negative prompt in the strongest position there is.

base_tags fixes slot 2 of the POSITIVE. It does nothing about this. Both halves are
needed, and only one of them lives on the card. This tool supplies the other half when
rendering the sheet; the film pipeline still cannot, which is a defect to fix in short.py
and is deliberately NOT worked around here.

IPAdapter sits at weight 0.0 - there is no reference yet, that is the whole point. That is
the same thing short.py does for a sheet-less character (short.py:305-306), so the graph
shape is one the project already renders through.
"""
import argparse, glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, COMFY, HOST   # noqa: E402

WF = "22_anime_kf_ipadapter.json"
CAST = os.path.join(STUDIO, "characters")
LATENT = (1024, 1024)      # SDXL native. animagine-xl-4.0 is an SDXL checkpoint.
SHEET = (1328, 1328)       # what make_sheets.py emits, kept the same on purpose.

Q = "masterpiece, best quality, very aesthetic, absurdres"

# Everything in the stock node-6 negative EXCEPT the sex terms, which are re-added per
# character below. "multiple views" stays: a sheet is ONE clean portrait, because
# turnaround.py generates the other fifteen and a sheet that is already a contact sheet
# gives the angles LoRA several faces to choose from.
NEG_BASE = ("motion blur, blurry, overexposed, washed out, white background, "
            "photorealistic, 3d, western comic, multiple views, lowres, worst quality, "
            "bad anatomy, bad hands, extra limbs, watermark, signature, text")

# The sex/age negative, chosen from the card rather than hard-coded to "not a girl".
NEG_MALE = "1girl, female, feminine, breasts, multiple boys"
NEG_FEMALE = "1boy, male focus, masculine, beard, facial hair, multiple girls"
NEG_CHILD = "adult, mature male, muscular, beard, facial hair, tall"


def negative_for(card):
    tags = (card.get("tags", "") + " " + card.get("base_tags", "")).lower()
    parts = []
    if "1girl" in tags:
        parts.append(NEG_FEMALE)
    else:
        parts.append(NEG_MALE)
    if "child" in tags:
        parts.append(NEG_CHILD)
    parts.append(NEG_BASE)
    return ", ".join(parts)


def positive_for(card):
    """Slot order is load-bearing: identity, then base, then the garment in its CLEAN
    state, then the sheet's own framing. Same order compose.py:1479-1490 assembles."""
    bits = [card.get("tags", "").strip()]
    if card.get("base_tags"):
        bits.append(card["base_tags"].strip())
    wear = card.get("wear_tags") or []
    if wear:
        bits.append(wear[0].strip())
    bits.append("character reference sheet, single character, solo, neutral expression, "
                "facing the camera, even soft lighting, plain flat grey background, "
                "upper body")
    bits.append(Q)
    return ", ".join(b for b in bits if b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("characters", nargs="+")
    ap.add_argument("--seed", type=int, default=4400)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--steps", type=int, default=32)
    ap.add_argument("--cfg", type=float, default=5.0)
    a = ap.parse_args()

    for i, cid in enumerate(a.characters):
        p = os.path.join(CAST, cid + ".json")
        if not os.path.exists(p):
            raise SystemExit("unknown character %r" % cid)
        card = json.load(open(p, encoding="utf-8"))
        name = card.get("sheet") or ("sheet_anime_%s.png" % cid.lower())
        dest = os.path.join(COMFY, "input", name)
        if os.path.exists(dest) and not a.force:
            print("  = %s (exists)" % name)
            continue

        wf = load_wf(WF)
        set_path(wf, "4.inputs.weight", 0.0)          # no reference yet - that is the point
        set_path(wf, "5.inputs.text", positive_for(card))
        set_path(wf, "6.inputs.text", negative_for(card))
        set_path(wf, "7.inputs.width", LATENT[0])
        set_path(wf, "7.inputs.height", LATENT[1])
        set_path(wf, "8.inputs.seed", a.seed + i * 17)
        set_path(wf, "8.inputs.steps", a.steps)
        set_path(wf, "8.inputs.cfg", a.cfg)
        set_path(wf, "10.inputs.width", SHEET[0])
        set_path(wf, "10.inputs.height", SHEET[1])
        set_path(wf, "11.inputs.filename_prefix", "claude-generated/sheets/%s" % cid)

        print("  > %s" % name, flush=True)
        print("      POS %s" % positive_for(card)[:120])
        print("      NEG %s" % negative_for(card)[:120])
        # Same stale-file dance make_sheets.py documents: ComfyUI derives its _0000N_
        # counter from what is already in the output dir, so a leftover makes the new
        # render land on _00002_ while we fetch _00001_.
        for stale in glob.glob("%s/output/claude-generated/sheets/%s_*.png" % (COMFY, cid)):
            os.remove(stale)
        if os.path.exists(dest):
            os.remove(dest)
        run(HOST, wf, quiet=True)
        ensure_local("claude-generated/sheets/%s_00001_.png" % cid, dest, required=True)
        print("    -> %s" % dest)

    print("\nsheets ready. Turn them around with studio/_tools/turnaround.py <ID>.")


if __name__ == "__main__":
    main()
