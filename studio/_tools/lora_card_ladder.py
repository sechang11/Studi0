#!/usr/bin/env python3
"""Give a library card the picture it is missing: a strength ladder, control on the left.

The library already knows how to SHOW a ladder - loras.html has the slot and the caption - and
sixteen of the forty-five cards fill it.  The ones that do not are, almost exactly, the ones a
person would actually cast: the LeBlanc costume, the crown, both LeNga identity runs.  A card
that says "wardrobe identical across 12 poses x 3 seeds" and shows nothing is asking to be
taken on trust, which is the one currency this project does not spend.

`lora_strength_sweep.py` already does this and cannot do it here: it is wired to the anime
checkpoint and to the old cast-card format, and it applies the LoRA to the model only.  Every
card named above is SDXL on RealVisXL, and the LeNga cards exist to prove that training the
TEXT ENCODERS is what turns a lookalike into a likeness - so a model-only ladder would
under-render exactly the thing the card is about.

This one reads the library card instead.  The card already carries everything needed: the
file, the trigger, the base model, the default strength and the range it is honest over.

    python3 lora_card_ladder.py crown-leblanc lenga-costume-lb3 lenga-identity-fb
    python3 lora_card_ladder.py --all-missing        # every ready card with no example
    python3 lora_card_ladder.py crown-leblanc --dry  # say what it would render

WHAT THE LADDER IS FOR.  The leftmost cell is strength 0 - the same seed and the same words
with the LoRA switched off - so the reader can see what the base model does unaided and judge
the rest against it rather than against an idea.  The last cell is the top of the card's own
range, because "at full weight" is the question people actually have.

The scenes are deliberately NOT from any training set, and the background is in frame on
purpose.  A LoRA that memorised its folder gives itself away when asked for somewhere it has
never been, and the cost of pushing strength up shows in the background long before it shows
in the subject.
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
CARDS = os.path.join(STUDIO, "loras")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from epic import COMFY, HOST, submit  # noqa: E402

OUT_DIR = os.path.join(STUDIO, "samples", "loras")
CKPT = {"RealVisXL_V5.0": "RealVisXL_V5.0_fp16.safetensors",
        "animagine-xl-4.0": "animagine-xl-4.0.safetensors",
        "Illustrious-XL-v2.0": "Illustrious-XL-v2.0.safetensors"}

Q = "photograph, natural light, sharp focus, detailed"
NEG = ("lowres, worst quality, bad anatomy, bad hands, extra limbs, deformed, watermark, "
       "signature, text, multiple views, nsfw")

# Neither of these is in anybody's training set, and both put a real background in frame:
# the strength cost shows up behind the subject before it shows up on them.
SCENES = [("market", "standing in a busy outdoor market in daylight, stalls and awnings "
                     "behind, people passing, full body, looking at the camera"),
          ("library", "standing between tall library shelves, warm lamplight, books in "
                      "focus behind, full body, looking at the camera")]

# What the trigger needs around it to make a picture, by what the LoRA is FOR.  An identity
# LoRA is the subject; a costume or an accessory needs somebody to be worn by, and saying so
# is not a thumb on the scale - it is the only way the render is about the garment.
SUBJECT = {"character": "a person",
           "costume": "a woman wearing the outfit",
           "accessory": "a woman wearing it",
           "style": "a person standing outdoors"}


def wait(pid, budget=1800):
    t0 = time.time()
    while time.time() - t0 < budget:
        time.sleep(5)
        try:
            h = json.load(urllib.request.urlopen("http://%s/history/%s" % (HOST, pid), timeout=30))
        except Exception:
            continue
        if h.get(pid):
            return (h[pid].get("status") or {}).get("status_str")
    return "timeout"


def graph(ckpt, lora, strength, pos, neg, seed, prefix):
    """plain SDXL text-to-image, with the LoRA on BOTH the model and the text encoders"""
    g = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ckpt}},
        "5": {"class_type": "EmptyLatentImage",
              "inputs": {"width": 896, "height": 1152, "batch_size": 1}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": pos}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": neg}},
        "6": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "seed": seed, "steps": 26, "cfg": 5.0,
                         "sampler_name": "dpmpp_2m", "scheduler": "karras",
                         "positive": ["3", 0], "negative": ["4", 0],
                         "latent_image": ["5", 0], "denoise": 1.0}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage",
              "inputs": {"images": ["7", 0], "filename_prefix": prefix}},
    }
    if lora and strength > 0:
        g["2"] = {"class_type": "LoraLoader",
                  "inputs": {"model": ["1", 0], "clip": ["1", 1], "lora_name": lora,
                             "strength_model": float(strength),
                             "strength_clip": float(strength)}}
        g["3"]["inputs"]["clip"] = ["2", 1]
        g["4"]["inputs"]["clip"] = ["2", 1]
        g["6"]["inputs"]["model"] = ["2", 0]
    return g


def rungs(card, override=None):
    """0 (the control), then the card's own honest range, ending at its top

    An already-laddered card replays the strengths it was RENDERED at, not the ones it
    currently publishes - narrowing a range on a ladder's evidence must not delete that
    evidence from the ladder."""
    if override:
        return sorted({round(float(v), 2) for v in override} | {0.0})
    if card.get("example_strengths"):
        return [round(float(v), 2) for v in card["example_strengths"]]
    lo, hi = (card.get("strength_range") or [0.5, 1.0])[:2]
    default = float(card.get("strength") or hi)
    out = []
    for v in (0.0, float(lo), default, float(hi)):
        v = round(float(v), 2)
        if v not in out:
            out.append(v)
    return sorted(out)


def prompt_for(card, scene):
    subj = SUBJECT.get(card.get("kind"), "a person")
    return ", ".join([card["trigger"], subj, scene, Q])


def sheet(cells, labels, dest, title):
    """one row per scene, one column per strength, the number written on each column"""
    from PIL import Image, ImageDraw
    cw, ch, pad, head = 384, 494, 4, 42
    rows = len(cells)
    cols = max(len(r) for r in cells)
    W = cols * cw + (cols + 1) * pad
    H = head + rows * ch + (rows + 1) * pad
    im = Image.new("RGB", (W, H), (17, 17, 20))
    d = ImageDraw.Draw(im)
    d.text((pad + 2, 5), title, fill=(210, 210, 216))       # its own line
    for c, lab in enumerate(labels):                        # the numbers sit under it
        x = pad + c * (cw + pad)
        d.text((x + 4, 24), lab, fill=(150, 230, 175) if c else (230, 180, 150))
    for r, row in enumerate(cells):
        for c, p in enumerate(row):
            if not p or not os.path.exists(p):
                continue
            im.paste(Image.open(p).convert("RGB").resize((cw, ch)),
                     (pad + c * (cw + pad), head + pad + r * (ch + pad)))
    im.save(dest, quality=90)
    return dest


def do(card_id, seed, dry, retile=False, strengths=None):
    p = os.path.join(CARDS, "%s.json" % card_id)
    card = json.load(open(p, encoding="utf-8"))
    ckpt = CKPT.get(card.get("base_model"))
    if not ckpt:
        print("%s: no checkpoint known for base_model %r" % (card_id, card.get("base_model")))
        return None
    if not os.path.exists(os.path.expanduser("~/ComfyUI/models/loras/%s" % card["file"])):
        print("%s: %s is not in models/loras" % (card_id, card["file"]))
        return None
    st = rungs(card, strengths)
    print("\n=== %s (%s) ===" % (card_id, card["name"]))
    print("  %s on %s, strengths %s" % (card["file"], ckpt, ", ".join(str(s) for s in st)))
    if dry:
        for _, sc in SCENES:
            print("  would render: %s" % prompt_for(card, sc)[:110])
        return None
    cells = []
    for sname, scene in SCENES:
        row = []
        for s in st:
            pre = "claude-generated/ladder/%s_%s_%03d" % (card_id, sname, int(s * 100))
            if not retile:
                wait(submit(graph(ckpt, card["file"], s, prompt_for(card, scene), NEG, seed, pre)))
            g = sorted(glob.glob(os.path.join(COMFY, "output", pre + "*.png")),
                       key=os.path.getmtime)
            row.append(g[-1] if g else None)
            print("    %-8s %.2f  %s" % (sname, s, "ok" if g else "NO OUTPUT"), flush=True)
        cells.append(row)
    os.makedirs(OUT_DIR, exist_ok=True)
    dest = os.path.join(OUT_DIR, "%s__ladder.jpg" % card_id)
    labels = ["%.2f  (off)" % st[0] if st[0] == 0 else "%.2f" % st[0]] + \
             ["%.2f" % s for s in st[1:]]
    sheet(cells, labels, dest, "%s - %s" % (card["name"], card["file"]))
    card["example"] = "/samples/loras/%s__ladder.jpg" % card_id
    card["example_kind"] = "strength ladder"
    card["example_strengths"] = st          # what it was rendered at, so a re-tile replays it
    card["example_note"] = (
        "Strength ladder, same seed and same words in every cell; only the strength changes. "
        "The leftmost cell has the LoRA switched OFF, so the base model's own answer is the "
        "control. Two scenes neither this LoRA nor any other here was trained on, with the "
        "background in frame - a LoRA that memorised its folder shows it somewhere it has "
        "never been, and the cost of raising strength appears behind the subject first.")
    json.dump(card, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("  -> %s" % dest)
    return dest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cards", nargs="*")
    ap.add_argument("--all-missing", action="store_true",
                    help="every card with status ready and no example")
    ap.add_argument("--seed", type=int, default=7717)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--strengths", nargs="+", type=float,
                    help="sample these rungs instead of the card's range - including one the "
                         "card no longer publishes, because 'we tried it and it did nothing' "
                         "is worth showing")
    ap.add_argument("--retile", action="store_true",
                    help="rebuild the sheet from renders already on disk, paying for nothing")
    a = ap.parse_args()
    ids = list(a.cards)
    if a.all_missing:
        for f in sorted(glob.glob(os.path.join(CARDS, "*.json"))):
            c = json.load(open(f, encoding="utf-8"))
            if c.get("status") == "ready" and not c.get("example") \
                    and c.get("kind") in SUBJECT and c.get("base_model") in CKPT:
                ids.append(c["id"])
    if not ids:
        print("nothing to do")
        sys.exit(0)
    for cid in ids:
        try:
            do(cid, a.seed, a.dry, a.retile, a.strengths)
        except Exception as e:
            print("%s FAILED: %s" % (cid, str(e)[:200]), flush=True)
    print("LADDER DONE", flush=True)
