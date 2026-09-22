#!/usr/bin/env python3
"""studio/_tools/casting.py - the casting call: twenty faces, six shots each, one at 4K.

Same identity route as agency.py: the card headshot is generated once, then handed to Flux 2 as
a reference picture for the other five shots, so one picture carries the face rather than a
description trying to. What changes here is the brief. These are meant to stand out, so the
descriptions lean on the features that actually make a face memorable - bone structure, unusual
colouring, pigment, hair - rather than on the word "beautiful", which returns the same
symmetrical airbrushed face every time and is the single fastest way to look generated.

Each character gets a comp card: the six frames a real casting director asks for.

    card       neutral headshot in window light   <- this one is upscaled to 4K
    profile    three-quarter turn
    full       full length, plain wall
    candid     moving, laughing, available light
    editorial  styled, on location
    golden     low sun, hard light

    python3 studio/_tools/casting.py --cards        # the twenty headshots
    python3 studio/_tools/casting.py --shots        # the other five each
    python3 studio/_tools/casting.py --fourk        # upscale every card x4
    python3 studio/_tools/casting.py --sheet        # contact sheet of the twenty
"""
import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COMFY = os.path.expanduser("~/ComfyUI")
COMFY_IN = os.path.join(COMFY, "input")
COMFY_OUT = os.path.join(COMFY, "output")
OUT = os.path.join(ROOT, "studio", "samples", "casting")

REAL = ("Shot on a phone in available light, unretouched: visible skin pores and texture, "
        "natural skin tone variation, stray hairs, slightly off-centre framing, shallow depth "
        "of field, faint sensor noise. Not a studio portrait, no retouching, no beauty filter.")

STRIKING = ("She has the bone structure of a working model and a face that is memorable rather "
            "than conventional, but she is photographed plainly and her skin is real.")

# Twenty looks that differ from each other on the axes that actually read at a glance:
# pigment, hair, bone structure, height, and the one unusual feature each is built around.
PEOPLE = [
    ("zaya-okonkwo", "Zaya Okonkwo", "Lagos", "a shaved head and a neck like a column",
     "a 25 year old Nigerian woman with very deep dark brown skin, a closely shaved head, an "
     "unusually long neck, very high sharp cheekbones, a broad nose, full lips and a small gold "
     "septum ring"),
    ("mireia-solans", "Mireia Solans", "Barcelona", "vitiligo mapped across her face",
     "a 27 year old Spanish woman with olive skin and pronounced vitiligo forming pale patches "
     "across one cheek, her jaw and both hands, dark straight hair to her shoulders, dark green "
     "eyes and thick dark brows"),
    ("kestrel-ohaeri", "Kestrel Ohaeri", "London", "albinism against dark brows",
     "a 24 year old Nigerian-British woman with albinism: very pale ivory skin, a large "
     "white-blonde afro, pale grey-blue eyes, unusually dark eyebrows and lashes, broad nose "
     "and full lips"),
    ("yuki-amari", "Yuki Amari", "Osaka", "one amber eye, one grey",
     "a 23 year old Japanese woman with complete heterochromia, one amber-brown eye and one "
     "pale grey, waist-length hair dyed silver-white with dark roots, a very small frame, a "
     "narrow face and a sharp chin"),
    ("farah-ziad", "Farah Ziad", "Cairo", "an aquiline nose and joined brows",
     "a 28 year old Egyptian woman with deep olive skin, a strong aquiline nose, naturally "
     "joined thick black eyebrows, heavy-lidded dark eyes, black curls pulled back, and a "
     "strong square jaw"),
    ("ingrid-halla", "Ingrid Halla", "Reykjavik", "six foot two and all angles",
     "a 25 year old Icelandic woman, very tall with square shoulders and a long neck, a "
     "platinum blonde buzzcut grown out to a soft crop, pale ice-blue eyes, clear pale "
     "skin with light freckles over the nose, high wide cheekbones, a strong straight "
     "jaw and a full mouth"),
    ("nadia-rahimi", "Nadia Rahimi", "Tehran", "copper curls on deep tan",
     "a 26 year old Iranian woman with deep tan skin heavily freckled across the nose and "
     "cheeks, coppery red-brown curls to her shoulders, grey-green eyes, a straight strong "
     "nose and a wide mouth"),
    ("tavita-fetu", "Tavita Fetu", "Auckland", "broad features, long black waves",
     "a 27 year old Samoan woman with warm brown skin, broad strong facial features, a wide "
     "nose, very full lips, dark almond eyes, long thick black wavy hair, and fine dark "
     "geometric tattooing on her forearm"),
    ("runa-eriksdottir", "Runa Eriksdottir", "Copenhagen", "freckles edge to edge",
     "a 24 year old Danish woman with extremely dense freckles covering her whole face and "
     "neck, bright copper-red hair, very pale skin, wide-set pale blue eyes and a noticeable "
     "gap between her front teeth"),
    ("amara-diallo", "Amara Diallo", "Dakar", "a braided crown and amber eyes",
     "a 26 year old Senegalese woman with very deep dark skin, hair in an intricate raised "
     "cornrow crown, striking light amber eyes, an elongated face, high forehead, broad nose "
     "and a long neck"),
    ("ling-wei", "Ling Wei", "Shanghai", "a blunt bob and a razor jaw",
     "a 25 year old Chinese woman with very pale porcelain skin, a blunt jaw-length black bob "
     "with a straight fringe, an extremely sharp defined jawline, narrow monolid eyes, thin "
     "arched brows and a small full mouth"),
    ("soraya-baz", "Soraya Baz", "Marrakesh", "tight coils and a beauty mark",
     "a 28 year old Moroccan woman with medium brown skin, tight black coils cut short, "
     "deep-set very dark eyes, thick brows, a prominent beauty mark above her upper lip on the "
     "left, and a strong square jaw"),
    ("petra-novak", "Petra Novak", "Prague", "androgynous and slicked back",
     "a 29 year old Czech woman with an androgynous face, dark hair slicked straight back, very "
     "sharp high cheekbones, pale skin, thin lips, pale blue eyes and almost invisible brows"),
    ("oyelaran-ade", "Oyelaran Ade", "Salvador", "locs to the waist",
     "a 30 year old Afro-Brazilian woman with very deep dark skin, thick black locs falling to "
     "her waist, a broad flat nose, wide full mouth, round dark eyes and heavy gold ear "
     "jewellery"),
    ("camille-nakamura", "Camille Nakamura", "Paris", "French and Japanese, freckled",
     "a 26 year old French-Japanese woman with light freckled skin, a messy dark brown bob, "
     "hazel eyes with an epicanthic fold, a small straight nose, high cheekbones and a wide "
     "expressive mouth"),
    ("zora-lindqvist", "Zora Lindqvist", "Stockholm", "an enormous afro, pale green eyes",
     "a 25 year old Afro-Swedish woman with light golden-brown skin, a very large round natural "
     "afro, unusual pale green eyes, a small nose, freckles across the bridge and a delicate "
     "narrow jaw"),
    ("inaya-qureshi", "Inaya Qureshi", "Lahore", "hair to the waist, a gold nose chain",
     "a 24 year old Pakistani woman with warm brown skin, extremely long thick glossy black "
     "hair past her waist, very large dark almond eyes with heavy lashes, strong straight brows "
     "and a fine gold nose ring with a chain to her ear"),
    ("marisol-vega", "Marisol Vega", "Oaxaca", "a long braid and a strong profile",
     "a 27 year old Mexican woman with deep brown skin, strong indigenous features, a prominent "
     "straight nose, broad cheekbones, very dark eyes, black hair in one long thick braid, and "
     "a wide full mouth"),
    ("freja-blom", "Freja Blom", "Gothenburg", "almost translucent",
     "a 23 year old Swedish woman who is extremely pale with near-translucent skin, very long "
     "white-blonde straight hair, pale eyebrows and lashes that are almost invisible, and large "
     "pale blue eyes"),
    ("nour-haddad", "Nour Haddad", "Beirut", "grey eyes under heavy brows",
     "a 28 year old Lebanese woman with olive skin, very thick dark brows, unusual light grey "
     "eyes, long dark wavy hair, a strong straight nose and a defined square jaw"),
]

# (key, whether it is the reference card, what the frame shows)
SHOTS = [
    ("card", True,
     "Head and shoulders, square to the camera, indoors beside a large window on an overcast "
     "day, flat soft daylight, neutral expression, wearing a plain grey t-shirt, plain pale "
     "wall behind her."),
    ("profile", False,
     "Turned three-quarters away and looking back past her shoulder, same plain wall, same flat "
     "window light, so the jaw and cheekbone read clearly."),
    ("full", False,
     "Standing full length against a plain concrete wall in daylight, arms relaxed at her "
     "sides, flat shoes, plain black vest and straight trousers, the whole body in frame."),
    ("candid", False,
     "Caught mid-laugh turning towards the camera on a street in the afternoon, slight motion "
     "blur, hair moving, out of focus shopfronts behind her."),
    ("editorial", False,
     "Standing in a bare room with a tall window and worn floorboards, wearing a simple long "
     "dark coat, one hand in a pocket, late afternoon light falling across the floor and up one "
     "side of her."),
    ("golden", False,
     "Outdoors at golden hour with low sun raking hard across her face from one side, eyes "
     "half-closed against the light, hair lit from behind."),
]

T2I_WF = "workflows/26_flux2_t2i.json"
REF_WF = "workflows/68_flux2_ref.json"
UP_WF = "workflows/69_esrgan_upscale.json"
W, H = 1024, 1280


def sh(*a, **kw):
    return subprocess.run(a, capture_output=True, text=True, **kw)


def run_wf(wf, sets, label=""):
    cmd = [sys.executable, os.path.join(ROOT, "scripts", "comfy.py"), "run", os.path.join(ROOT, wf)]
    for k, v in sets:
        cmd += ["-s", "%s=%s" % (k, v)]
    t0 = time.time()
    r = sh(*cmd, cwd=ROOT)
    m = re.search(r"-> (\S+\.png)", r.stdout or "")
    if not m:
        print("      FAILED %s: %s" % (label, ((r.stderr or r.stdout or "").strip()[-260:])))
        return None, time.time() - t0
    return os.path.join(COMFY_OUT, m.group(1)), time.time() - t0


def cards(seed=4242):
    os.makedirs(OUT, exist_ok=True)
    _, _, what = SHOTS[0][0], SHOTS[0][1], SHOTS[0][2]
    for i, (slug, name, city, hook, look) in enumerate(PEOPLE):
        d = os.path.join(OUT, slug)
        os.makedirs(d, exist_ok=True)
        dest = os.path.join(d, "1_card.png")
        if os.path.exists(dest):
            print("  %-20s card exists" % name)
            continue
        prompt = "Photo of %s. %s %s %s" % (look, what, STRIKING, REAL)
        src, secs = run_wf(T2I_WF, [
            ("6.inputs.text", prompt), ("9.inputs.width", W), ("9.inputs.height", H),
            ("12.inputs.width", W), ("12.inputs.height", H),
            ("11.inputs.noise_seed", seed + i * 101),
            ("15.inputs.filename_prefix", "claude-generated/casting/%s_card" % slug)], slug)
        if not src:
            continue
        shutil.copy(src, dest)
        shutil.copy(src, os.path.join(COMFY_IN, "cast_%s.png" % slug))
        print("  %-20s card  %5.1fs" % (name, secs))


def shots(seed=8100, who=None):
    for i, (slug, name, city, hook, look) in enumerate(PEOPLE):
        if who and slug != who:
            continue
        d = os.path.join(OUT, slug)
        ref = "cast_%s.png" % slug
        card = os.path.join(d, "1_card.png")
        if not os.path.exists(card):
            print("  %-20s no card yet" % name)
            continue
        if not os.path.exists(os.path.join(COMFY_IN, ref)):
            shutil.copy(card, os.path.join(COMFY_IN, ref))
        for j, (key, is_card, what) in enumerate(SHOTS):
            if is_card:
                continue
            dest = os.path.join(d, "%d_%s.png" % (j + 1, key))
            if os.path.exists(dest):
                continue
            prompt = ("Photo of the same woman as in the reference images: %s. %s Keep her face, "
                      "bone structure, colouring and hair exactly as in the references. %s"
                      % (look, what, REAL))
            src, secs = run_wf(REF_WF, [
                ("42.inputs.image", ref), ("46.inputs.image", ref),
                ("sg1_6.inputs.text", prompt),
                ("sg1_25.inputs.noise_seed", seed + i * 31 + j * 7),
                ("sg1_95.inputs.value", "true"),
                ("9.inputs.filename_prefix", "claude-generated/casting/%s_%s" % (slug, key))],
                "%s/%s" % (slug, key))
            if src:
                shutil.copy(src, dest)
                print("  %-20s %-10s %5.1fs" % (name, key, secs))


def fourk():
    """The card, x4 through RealESRGAN: 1024x1280 becomes 4096x5120."""
    from PIL import Image
    for slug, name, _, _, _ in PEOPLE:
        d = os.path.join(OUT, slug)
        card = os.path.join(d, "1_card.png")
        dest = os.path.join(d, "1_card_4k.png")
        if not os.path.exists(card) or os.path.exists(dest):
            continue
        staged = "cast_%s.png" % slug
        shutil.copy(card, os.path.join(COMFY_IN, staged))
        src, secs = run_wf(UP_WF, [
            ("1.inputs.image", staged),
            ("4.inputs.filename_prefix", "claude-generated/casting/%s_4k" % slug)], slug)
        if not src:
            continue
        shutil.copy(src, dest)
        print("  %-20s 4K %5.1fs  %s" % (name, secs, "x".join(map(str, Image.open(dest).size))))


def sheet():
    from PIL import Image, ImageDraw
    cw, ch, cols, head = 300, 375, 5, 20
    items = [(s, n) for s, n, _, _, _ in PEOPLE
             if os.path.exists(os.path.join(OUT, s, "1_card.png"))]
    if not items:
        return
    rows = (len(items) + cols - 1) // cols
    S = Image.new("RGB", (cw * cols, (ch + head) * rows), (20, 19, 18))
    dr = ImageDraw.Draw(S)
    for i, (slug, name) in enumerate(items):
        im = Image.open(os.path.join(OUT, slug, "1_card.png")).convert("RGB")
        w, h = im.size
        sc = min(cw / w, ch / h)
        im = im.resize((max(1, int(w * sc)), max(1, int(h * sc))), Image.LANCZOS)
        x, y = (i % cols) * cw, (i // cols) * (ch + head)
        S.paste(im, (x + (cw - im.size[0]) // 2, y + head))
        dr.text((x + 5, y + 4), name, fill=(238, 233, 225))
    p = os.path.join(OUT, "_casting_sheet.jpg")
    S.save(p, quality=85)
    print("  %d cards -> %s" % (len(items), p))


def main():
    ap = argparse.ArgumentParser()
    for f in ("cards", "shots", "fourk", "sheet"):
        ap.add_argument("--" + f, action="store_true")
    ap.add_argument("--who", default=None)
    a = ap.parse_args()
    if a.cards:
        cards()
    if a.shots:
        shots(who=a.who)
    if a.fourk:
        fourk()
    if a.sheet:
        sheet()
    if not any((a.cards, a.shots, a.fourk, a.sheet)):
        ap.print_help()


if __name__ == "__main__":
    main()
