#!/usr/bin/env python3
"""Does a character survive on the QWEN engine, and can you restyle them?

    python3 studio/_tools/qwen_character.py              # every stage, in model order
    python3 studio/_tools/qwen_character.py --stage A B  # only these
    python3 studio/_tools/qwen_character.py --sheets     # rebuild contact sheets only

THE QUESTION THIS ANSWERS

VIRO has a trained character LoRA. It is an ANIMAGINE LoRA, and this project has already
proved from pixels that a LoRA is a delta on specific weights - animagine's does nothing on
Qwen. So on the qwen engine there is no trained identity mechanism at all, and the honest
question is what is left: a written description, a reference sheet through Qwen-Image-Edit,
the multiple-angles LoRA, Relight, and a qwen-native style LoRA.

Nobody had rendered any of it. The resolver already tells users the qwen reference lock is
"weaker than IPAdapter"; this tool exists to find out how much weaker, from pixels.

WHAT IS HELD CONSTANT AND WHY

Framing is written into every prompt ("waist-up photograph"). The turnaround tool learned
this the hard way: when framing is left to the model it drifts, and then two things vary at
once and you cannot attribute the difference. Same for the garment - it is stated in every
cell, so that when a face changes it is the FACE that changed and not the outfit doing the
recognising for you.

Seed is fixed per PLACE, so arm A and arm B1 and arm B2 for the same place all sample the
same noise. The only difference between those cells is the mechanism under test.

THE FOUR IDENTITY ARMS ARE A LADDER, ONE VARIABLE PER RUNG

    A     no reference at all, description only        the control
    B1    reference = the sheet the films actually use, literal "image 1" phrasing
    B2    reference = a style-matched photographic sheet, literal "image 1" phrasing
    B3    reference = the same photographic sheet, the phrasing short.py actually emits

    A  -> B2   is the value of having a reference at all
    B1 -> B2   is the cost of the sheet being a different STYLE from the target
    B2 -> B3   is the cost of the prompt phrasing, which workflow 23 warns about and
               scripts/short.py does not follow

CONTACT SHEETS COME IN PAIRS. A full-frame grid shows whether the scene worked; a
face-crop grid shows whether the PERSON held. Identity has to be judged on the face crop,
because at full-frame a matching jersey reads as a matching character and it is not.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, COMFY, HOST   # noqa: E402

from PIL import Image, ImageDraw, ImageFont           # noqa: E402

OUT = os.path.join(STUDIO, "samples", "qwen_character")

T2I = "13_qwen_t2i_styled.json"        # Qwen-Image 2512, no reference
REF = "14_qwen_edit_ref.json"          # Qwen-Image-Edit 2511, reference images
ANG = "32_qwen_turnaround.json"        # 2511 + multiple-angles LoRA
EDT = "03_qwen_image_edit.json"        # Qwen-Image-Edit 2509, base for Relight

L_ILLUS   = "illustration-1.0-qwen-image.safetensors"
L_RELIGHT = "Qwen-Image-Edit-2509-Relight.safetensors"
L_LIGHT09 = "Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors"

# VIRO, read off studio/characters/VIRO.json. `prose` is the field the qwen engine uses;
# `tags` is danbooru and means nothing to a photographic model.
PROSE = ("a young man with long dark brown curly hair tied in a ponytail, "
         "brown eyes, a small gold ear stud")
WEAR = "wearing a teal soccer jersey with orange trim and the number 7"
FRAME = "waist-up photograph"

# Four places the sheet has never seen. Concrete nouns, not adjectives - this project has
# measured that a place card with ~11 concrete nouns survives a style that would otherwise
# replace it, while three loose tags do not.
PLACES = [
    ("night_street", "on a rain-soaked city street at night, wet asphalt reflecting red "
                     "and green neon signs, parked cars, a bus shelter, puddles"),
    ("kitchen",      "in a bright domestic kitchen, white tiled wall, wooden worktop, a "
                     "steel kettle, a bowl of lemons, morning light from a window"),
    ("beach",        "on a windswept pebble beach under a grey overcast sky, breaking "
                     "waves, a wooden groyne, gulls, driftwood"),
    ("library",      "in a wood-panelled library, tall shelves of old books, a brass "
                     "reading lamp, a rolling ladder, warm lamplight"),
]

SEED = 4400
W, H = 1152, 1440          # 4:5. A waist-up figure at 16:9 puts the face on ~90px of
                           # height, which is too small to judge identity from.

SHEET_PHOTO = "qc_viro_photo_sheet.png"     # built by stage `sheet`, lands in ComfyUI/input
SHEET_FILM = "sheet_viro.png"               # what films reference today

# Six views for the angles stage. Framing is stated in every one, for the reason in the
# module docstring.
VIEWS = [
    ("front",         "front view of the same person, facing the camera directly, neutral expression, head and shoulders"),
    ("three_quarter", "three-quarter view of the same person, head turned slightly to their left, head and shoulders"),
    ("side_left",     "the same person's head turned to face left, profile of the face, head and shoulders"),
    ("back",          "the same person seen from behind, back of the head, head and shoulders"),
    ("looking_up",    "the same person looking upward, chin raised, neutral expression, head and shoulders"),
    ("low_angle",     "the same person seen from a low camera angle looking up at them, head and shoulders"),
]

LIGHTS = [
    ("golden_hour", "Relight the photograph: warm low golden-hour sunlight raking in from "
                    "the left, long soft shadows, amber highlights on the face. Keep the "
                    "person, pose and background exactly the same."),
    ("hard_top",    "Relight the photograph: harsh hard overhead light from directly above, "
                    "deep shadows in the eye sockets and under the chin, high contrast. "
                    "Keep the person, pose and background exactly the same."),
    ("blue_rim",    "Relight the photograph: cool blue backlight rimming the head and "
                    "shoulders from behind, dim cold ambient fill on the face. Keep the "
                    "person, pose and background exactly the same."),
]


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def font(sz):
    for p in ("/usr/share/fonts/google-carlito-fonts/Carlito-Bold.ttf",
              "/usr/share/fonts/adwaita-sans-fonts/AdwaitaSans-Regular.ttf",
              "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def stage_img(path, name):
    """LoadImage only reads from ComfyUI/input, so anything referenced must live there."""
    dst = os.path.join(COMFY, "input", name)
    if os.path.abspath(path) != os.path.abspath(dst):
        sh("cp", path, dst)
    return name


def fetch(outs, dst):
    if not outs:
        return False
    return bool(ensure_local(outs[0], dst, required=False))


def do(wf, dst, label):
    """Render one cell. Returns True if a file landed."""
    if os.path.exists(dst):
        print("  %-30s = exists" % label)
        return True
    try:
        _, outs = run(HOST, wf, quiet=True)
    except SystemExit:
        print("  %-30s FAILED (workflow rejected)" % label)
        return False
    except Exception as e:
        print("  %-30s FAILED %s" % (label, str(e)[:70]))
        return False
    ok = fetch(outs, dst)
    print("  %-30s %s" % (label, "%6.0f KB" % (os.path.getsize(dst) / 1024) if ok else "NO OUTPUT"))
    return ok


# --------------------------------------------------------------- workflow builders

def wf_t2i(prompt, seed, style_lora=None, strength=0.0, w=W, h=H):
    """Qwen-Image 2512 text-to-image. Node 7 is the style slot and ships OFF."""
    wf = load_wf(T2I)
    set_path(wf, "10.inputs.text", prompt)
    set_path(wf, "12.inputs.width", w)
    set_path(wf, "12.inputs.height", h)
    set_path(wf, "13.inputs.seed", seed)
    if style_lora:
        set_path(wf, "7.inputs.lora_name", style_lora)
    set_path(wf, "7.inputs.strength_model", float(strength))
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/qc/t2i")
    return wf


def wf_ref(prompt, seed, sheet, style_lora=None, strength=0.0, w=W, h=H):
    """Qwen-Image-Edit 2511 in REFERENCE mode: the sheet conditions, an empty latent is
    the canvas (node 13 samples node 20, not node 12). The sheet is NOT the thing being
    painted over - a whole new scene is generated with the sheet as side-conditioning."""
    wf = load_wf(REF)
    wf.pop("9", None)      # second LoadImage, unwired here; drop it so it cannot fail
    wf.pop("12", None)     # VAEEncode of the ref - dead in reference mode
    set_path(wf, "8.inputs.image", sheet)
    # Both encoders get the references. That is the Qwen edit convention and node 11 is
    # the negative; feeding it the same images is deliberate, not a copy-paste bug.
    set_path(wf, "10.inputs.prompt", prompt)
    set_path(wf, "20.inputs.width", w)
    set_path(wf, "20.inputs.height", h)
    set_path(wf, "13.inputs.seed", seed)
    if style_lora:
        set_path(wf, "7.inputs.lora_name", style_lora)
    set_path(wf, "7.inputs.strength_model", float(strength))
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/qc/ref")
    return wf


def wf_angles(src, prompt, seed, strength=0.85):
    wf = load_wf(ANG)
    set_path(wf, "7.inputs.image", src)
    set_path(wf, "10.inputs.prompt", prompt)
    set_path(wf, "15.inputs.seed", seed)
    set_path(wf, "40.inputs.strength_model", float(strength))
    set_path(wf, "17.inputs.filename_prefix", "claude-generated/qc/ang")
    return wf


def wf_relight(src, prompt, seed, strength=1.0):
    """Qwen-Image-Edit 2509 + Relight. Built by patching workflow 03 rather than adding a
    workflow file, because this is an experiment and not yet a sanctioned graph.

    Chain order follows the project convention set in workflow 32: the accelerator sits
    CLOSEST TO THE BASE WEIGHTS and the task LoRA stacks after it. The accelerator is
    sampler configuration, not style, and must stay at 1.0.

    Relight is a 2509 LoRA, so it runs on the 2509 checkpoint. 2511 is a different base
    and this project has already proved LoRAs are base-locked."""
    wf = load_wf(EDT)
    wf["40"] = {"class_type": "LoraLoaderModelOnly",
                "inputs": {"model": ["1", 0], "lora_name": L_LIGHT09, "strength_model": 1.0}}
    wf["41"] = {"class_type": "LoraLoaderModelOnly",
                "inputs": {"model": ["40", 0], "lora_name": L_RELIGHT,
                           "strength_model": float(strength)}}
    set_path(wf, "5.inputs.model", ["41", 0])
    set_path(wf, "7.inputs.image", src)
    set_path(wf, "10.inputs.prompt", prompt)
    set_path(wf, "13.inputs.seed", seed)
    set_path(wf, "13.inputs.steps", 4)      # the 2509 Lightning LoRA is installed, so the
    set_path(wf, "13.inputs.cfg", 1.0)      # 20-step / cfg 4.0 default in 03 is obsolete
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/qc/relight")
    return wf


# --------------------------------------------------------------- stages

def dirfor(name):
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    return d


def stage_sheet(force):
    """A photographic reference sheet, rendered the way make_sheets.py does it but with
    the style LoRA slot explicitly OFF.

    This exists because the sheet the films actually use (sheet_viro.png) is an
    ILLUSTRATION. It was rendered through workflow 13 back when node 7 carried the
    storybook LoRA at 0.8, so the style is baked into the reference itself. Comparing an
    illustrated reference against a photographic target confounds identity with style,
    so arm B2 needs a style-matched sheet to be a fair test."""
    d = dirfor("sheet")
    dst = os.path.join(d, "viro_photo_sheet.png")
    if force and os.path.exists(dst):
        os.remove(dst)
    p = (f"A character reference sheet photograph of {PROSE}, {WEAR}, neutral expression, "
         f"facing the camera directly, even soft lighting, plain flat grey background, "
         f"head and shoulders.")
    do(wf_t2i(p, 990, w=1328, h=1328), dst, "photo sheet")
    if os.path.exists(dst):
        stage_img(dst, SHEET_PHOTO)
    return d


def stage_A(force):
    """CONTROL: description only, no reference of any kind. How far do words carry a face?"""
    d = dirfor("A_control")
    for i, (pid, place) in enumerate(PLACES):
        dst = os.path.join(d, "%d_%s.png" % (i, pid))
        if force and os.path.exists(dst):
            os.remove(dst)
        p = f"A {FRAME} of {PROSE}, {WEAR}, {place}."
        do(wf_t2i(p, SEED + i), dst, pid)
    return d


def _ref_arm(name, sheet, phrasing, force):
    d = dirfor(name)
    for i, (pid, place) in enumerate(PLACES):
        dst = os.path.join(d, "%d_%s.png" % (i, pid))
        if force and os.path.exists(dst):
            os.remove(dst)
        do(wf_ref(phrasing(place), SEED + i, sheet), dst, pid)
    return d


def _literal(place):
    """The phrasing workflow 23 says the model was trained on: refer to the reference as
    "image 1", literally. Its _notes warn that vaguer wording degrades the association."""
    return (f"The man in image 1 is now {place}. {FRAME.capitalize()}. "
            f"Keep his face, hair and features exactly as they are in image 1. "
            f"He is {WEAR}.")


def _shortpy(place):
    """What scripts/short.py actually emits: the character's prose with "from the reference
    image" hand-written into the film's character string, and no mention of image 1."""
    return f"A {FRAME} of {PROSE} from the reference image, {WEAR}, {place}."


def stage_B1(force):
    return _ref_arm("B1_film_sheet", SHEET_FILM, _literal, force)


def stage_B2(force):
    return _ref_arm("B2_photo_sheet", SHEET_PHOTO, _literal, force)


def stage_B3(force):
    return _ref_arm("B3_shortpy_phrasing", SHEET_PHOTO, _shortpy, force)


def stage_C(force):
    """MULTIPLE ANGLES on a photographic source. The existing VIRO turnaround was run from
    the ANIME sheet, so it has never been tried on the kind of image the qwen engine
    actually produces."""
    d = dirfor("C_angles")
    src = SHEET_PHOTO
    for i, (vid, prompt) in enumerate(VIEWS):
        dst = os.path.join(d, "%d_%s.png" % (i, vid))
        if force and os.path.exists(dst):
            os.remove(dst)
        do(wf_angles(src, prompt, 1200 + i), dst, vid)
    return d


def stage_E2(force):
    """The combination the question is actually about: a style LoRA restyling a person
    while a reference sheet holds the face.

    NOTE THE BASE-REVISION TRAP. illustration-1.0-qwen-image was trained on Qwen-Image
    (text-to-image). This arm runs it on Qwen-Image-EDIT 2511, which shares the 60-block
    geometry so it will attach silently and cleanly whether or not it does anything.
    Stage E1 is the positive control that separates "the LoRA is inert" from "the LoRA
    does not cross to the edit model"."""
    d = dirfor("E2_style_on_ref")
    place = PLACES[3][1]      # the library, which has the most to lose to a flat style
    for s in (0.0, 1.0, 1.5):
        dst = os.path.join(d, "str_%.1f.png" % s)
        if force and os.path.exists(dst):
            os.remove(dst)
        do(wf_ref(_literal(place), 5150, SHEET_PHOTO, L_ILLUS, s), dst, "illus %.1f" % s)
    return d


def stage_E1(force):
    """Positive control for E2: the same style LoRA on its OWN base, the 2512 t2i model,
    where it is already proven to work."""
    d = dirfor("E1_style_t2i")
    place = PLACES[3][1]
    for s in (0.0, 1.0, 1.5):
        dst = os.path.join(d, "str_%.1f.png" % s)
        if force and os.path.exists(dst):
            os.remove(dst)
        p = f"A {FRAME} of {PROSE}, {WEAR}, {place}."
        do(wf_t2i(p, 5150, L_ILLUS, s), dst, "illus %.1f" % s)
    return d


def stage_F(force):
    """SEED ROBUSTNESS for the style stages, because the single-seed result was strong
    enough that it had to be checked before being reported.

    At seed 5150 the illustration LoRA on the bare t2i path turned VIRO into a woman at
    both 1.0 and 1.5, while the same LoRA over a reference sheet kept him male. If that
    holds across seeds it is the whole answer to "how do I give them a look"; if it was
    one unlucky sample it is nothing. Three extra seeds per arm settles it."""
    d = dirfor("F_style_seeds")
    place = PLACES[3][1]
    for s in (1.0, 1.5):
        for k, seed in enumerate((6001, 6002, 6003)):
            dst = os.path.join(d, "t2i_str%.1f_s%d.png" % (s, seed))
            if force and os.path.exists(dst):
                os.remove(dst)
            p = f"A {FRAME} of {PROSE}, {WEAR}, {place}."
            do(wf_t2i(p, seed, L_ILLUS, s), dst, "t2i %.1f seed%d" % (s, seed))
    return d


def stage_G(force):
    """The same seed sweep on the REFERENCE path, so F and G are directly comparable.
    Split from F only because it needs the 2511 edit checkpoint and F needs 2512 t2i -
    interleaving them would pay a ~20 GB model load per image."""
    d = dirfor("G_style_seeds_ref")
    place = PLACES[3][1]
    for s in (1.0, 1.5):
        for k, seed in enumerate((6001, 6002, 6003)):
            dst = os.path.join(d, "ref_str%.1f_s%d.png" % (s, seed))
            if force and os.path.exists(dst):
                os.remove(dst)
            do(wf_ref(_literal(place), seed, SHEET_PHOTO, L_ILLUS, s), dst,
               "ref %.1f seed%d" % (s, seed))
    return d


def stage_D(force):
    """RELIGHT: the "give them a certain look" half of the question. Lighting is the one
    part of "look" that is a physical fact about the image rather than an adjective, so it
    is exactly the kind of thing that belongs in a deterministic post-stage."""
    d = dirfor("D_relight")
    src_png = os.path.join(OUT, "B2_photo_sheet", "3_library.png")
    if not os.path.exists(src_png):
        src_png = os.path.join(OUT, "sheet", "viro_photo_sheet.png")
    if not os.path.exists(src_png):
        print("  no source image for relight - run stage B2 or sheet first")
        return d
    sh("cp", src_png, os.path.join(d, "0_source.png"))
    src = stage_img(src_png, "qc_relight_src.png")
    for i, (lid, prompt) in enumerate(LIGHTS):
        dst = os.path.join(d, "%d_%s.png" % (i + 1, lid))
        if force and os.path.exists(dst):
            os.remove(dst)
        do(wf_relight(src, prompt, 3300 + i), dst, lid)
    return d


# --------------------------------------------------------------- contact sheets

def grid(cells, dst, cols, cell_w, title, crop=None):
    """cells is [(label, path)]. crop is (y_frac, side_frac) to cut a square around the
    head, or None for the whole frame."""
    ims, labels = [], []
    for label, p in cells:
        if not os.path.isfile(p):
            continue
        im = Image.open(p).convert("RGB")
        if crop:
            yf, sf = crop
            side = int(im.height * sf)
            x0 = max(0, (im.width - side) // 2)
            y0 = max(0, int(im.height * yf))
            im = im.crop((x0, y0, min(im.width, x0 + side), min(im.height, y0 + side)))
        w = cell_w
        h = max(1, int(im.height * w / im.width))
        ims.append(im.resize((w, h), Image.LANCZOS))
        labels.append(label)
    if not ims:
        return None

    bar, pad, top = 26, 6, 34
    cw = cell_w
    ch = max(i.height for i in ims) + bar
    rows = (len(ims) + cols - 1) // cols
    Wg = cols * cw + pad * (cols + 1)
    Hg = rows * ch + pad * (rows + 1) + top
    out = Image.new("RGB", (Wg, Hg), (17, 17, 17))
    dr = ImageDraw.Draw(out)
    dr.text((pad + 2, 8), title, font=font(19), fill=(255, 220, 90))
    for i, im in enumerate(ims):
        r, c = divmod(i, cols)
        x = pad + c * (cw + pad)
        y = top + pad + r * (ch + pad)
        dr.rectangle([x, y, x + cw, y + bar], fill=(0, 0, 0))
        dr.text((x + 5, y + 5), labels[i][:34], font=font(16), fill=(120, 235, 255))
        out.paste(im, (x, y + bar))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    out.save(dst, quality=93)
    print("  %s  %.0f KB" % (dst, os.path.getsize(dst) / 1024))
    return dst


def sheets():
    """Build every contact sheet from whatever has been rendered."""
    def cells(sub, order=None):
        d = os.path.join(OUT, sub)
        if not os.path.isdir(d):
            return []
        fs = sorted(f for f in os.listdir(d) if f.endswith(".png"))
        return [(os.path.splitext(f)[0], os.path.join(d, f)) for f in fs]

    S = os.path.join(OUT, "_sheets")

    # The identity ladder, one row per arm, same four places in the same order.
    arms = [("A_control", "A  CONTROL - description only, no reference"),
            ("B1_film_sheet", "B1  REF = sheet_viro.png (the illustrated sheet films use)"),
            ("B2_photo_sheet", "B2  REF = photographic sheet, image-1 phrasing"),
            ("B3_shortpy_phrasing", "B3  REF = photographic sheet, short.py phrasing")]
    ladder, ladder_faces = [], []
    for sub, cap in arms:
        for label, p in cells(sub):
            ladder.append(("%s  %s" % (sub.split("_")[0], label), p))
            ladder_faces.append(("%s  %s" % (sub.split("_")[0], label), p))
    grid(ladder, os.path.join(S, "identity_ladder.jpg"), 4, 330,
         "IDENTITY ON QWEN - rows: A control / B1 film sheet / B2 photo sheet / B3 short.py phrasing")
    grid(ladder_faces, os.path.join(S, "identity_ladder_faces.jpg"), 4, 330,
         "SAME CELLS, FACE CROP - judge identity here, not on the jersey",
         crop=(0.04, 0.42))

    for sub, title, cols, crop in [
        ("sheet", "THE TWO REFERENCE SHEETS", 2, None),
        ("C_angles", "C  MULTIPLE-ANGLES LoRA on a photographic source", 3, None),
        ("D_relight", "D  RELIGHT (2509 + Relight LoRA) - source then three lightings", 4, None),
        ("E1_style_t2i", "E1  illustration LoRA on its OWN base (2512 t2i) - positive control", 3, None),
        ("E2_style_on_ref", "E2  illustration LoRA on 2511 EDIT with a reference sheet", 3, None),
        ("F_style_seeds", "F  style LoRA, NO reference - 3 seeds at 1.0 (top) and 1.5 (bottom)", 3, None),
        ("G_style_seeds_ref", "G  style LoRA + REFERENCE SHEET - same 3 seeds, 1.0 then 1.5", 3, None),
    ]:
        c = cells(sub)
        if c:
            grid(c, os.path.join(S, sub + ".jpg"), cols, 360, title, crop=crop)
    grid(cells("C_angles"), os.path.join(S, "C_angles_faces.jpg"), 3, 360,
         "C  MULTIPLE-ANGLES - face crop", crop=(0.02, 0.5))
    grid(cells("D_relight"), os.path.join(S, "D_relight_faces.jpg"), 4, 360,
         "D  RELIGHT - face crop, does identity survive the lighting change?",
         crop=(0.04, 0.42))

    # THE ANSWER SHEET. One row, every mechanism, all face-cropped against the source, so
    # the ranking can be checked by eye instead of taken on trust.
    def one(sub, fn):
        p = os.path.join(OUT, sub, fn)
        return p if os.path.isfile(p) else None
    picks = [
        ("SOURCE sheet", one("sheet", "viro_photo_sheet.png")),
        ("A  prose only", one("A_control", "1_kitchen.png")),
        ("A  prose only", one("A_control", "2_beach.png")),
        ("B2 + ref sheet", one("B2_photo_sheet", "1_kitchen.png")),
        ("B2 + ref sheet", one("B2_photo_sheet", "2_beach.png")),
        ("C  angles LoRA", one("C_angles", "1_three_quarter.png")),
        ("D  relight", one("D_relight", "1_golden_hour.png")),
        ("F  style, NO ref", one("F_style_seeds", "t2i_str1.5_s6001.png")),
        ("G  style + ref", one("G_style_seeds_ref", "ref_str1.5_s6001.png")),
    ]
    picks = [(l, p) for l, p in picks if p]
    grid(picks, os.path.join(S, "ANSWER.jpg"), 3, 340,
         "THE ANSWER - every mechanism vs the source, face crop. A drifts, B2/C/D/G hold, F loses the man entirely",
         crop=(0.04, 0.44))


STAGES = [("sheet", stage_sheet), ("A", stage_A), ("E1", stage_E1), ("F", stage_F),
          ("B1", stage_B1), ("B2", stage_B2), ("B3", stage_B3),
          ("C", stage_C), ("E2", stage_E2), ("G", stage_G), ("D", stage_D)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", nargs="*", help="subset of: " + " ".join(s for s, _ in STAGES))
    ap.add_argument("--sheets", action="store_true", help="rebuild contact sheets only")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    if a.sheets:
        sheets()
        return

    # Stage ORDER IS DELIBERATE and is not the alphabet: it is grouped by checkpoint.
    # 2512 t2i, then 2511 edit, then 2509 edit. Each of those is a ~20 GB fp8 model on a
    # 32 GB card, so an order that interleaves them pays a full model load per cell.
    want = [s for s in STAGES if not a.stage or s[0] in a.stage]
    if a.stage:
        unknown = set(a.stage) - {s for s, _ in STAGES}
        if unknown:
            raise SystemExit("unknown stage(s): %s" % ", ".join(sorted(unknown)))
    os.makedirs(OUT, exist_ok=True)
    for name, fn in want:
        print("\n== %s ==" % name, flush=True)
        fn(a.force)
    print("\n-- contact sheets --")
    sheets()
    print("\nlook at %s/_sheets/" % OUT)


if __name__ == "__main__":
    main()
