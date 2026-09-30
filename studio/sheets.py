#!/usr/bin/env python3
"""Sheets: one picture in, every angle out - a labelled model sheet of a character, an item or a place.

    python3 studio/sheets.py new character PICTURE --name "Doran Vey" [--closeup PICTURE]
    python3 studio/sheets.py new item PICTURE --name "Winged sword" --subject sword --item-type weapon
    python3 studio/sheets.py new place PICTURE --name "Harbour at night" --times midday,golden,night,rain
    python3 studio/sheets.py make SHEET_ID [--redo turn_back,face_right]
    python3 studio/sheets.py list

The page is /sheets (studio/sheets.html; routes in studio/_tools/sheets_routes.py). This module has
no web code: it plans the views, runs them through ComfyUI, checks them, upscales them and lays out
the sheet, so the page, this CLI and the Foundry all make a sheet the same way. Everything a sheet
makes lives in studio/sheets/<id>/ (sheet.json is the record; the pictures are git-ignored).

WHAT TURNS THE CAMERA (MEASURED 2026-09-30 on this box - craft/SHEETS.md has the contact sheets)
  Qwen-Image-Edit-2511 + its 4-step Lightning LoRA + the multiple-angles LoRA at 0.85 (workflow 32),
  asked in the LoRA's OWN camera words: "<sks> {azimuth} {elevation} {distance}", for example
  "<sks> back view eye-level shot wide shot". Plain English ("the same place seen from the opposite
  direction") handed the harbour and the temple back unchanged; the structured words turned both,
  including the full reverse. About 6 s a view on the 5090, ~1 MP out.
    works      8 azimuths of a person on a plain backdrop; an item's sides, back and top; a place's
               sides, reverse, raised three-quarters and aerial.
    weak       "low-angle shot" and "close-up" on a PLACE come back nearly unchanged - not offered.
    tilts      "back-left quarter view elevated shot" rolled the temple onto its side - not offered.
  A figure turns best cut out onto flat grey first (BiRefNet, workflow 14): the anime figure whose
  Foundry turnaround fell apart turned cleanly once it stood on grey.

WHAT DOES NOT TURN THE CAMERA
  Expressions, time of day, "worn by a person", a flat lay, standing a sword upright, the most
  detailed part in close-up, finishing a body below a head-and-shoulders crop: all the same edit
  model WITHOUT the angles LoRA, in plain sentences.

FACES ARE CROPPED, NOT ASKED FOR
  Framing words in an edit prompt are a suggestion (terra_views.py measured 23 of 24 "waist up"
  asks coming back full length). A face close-up is therefore cut from the clean full figure, made
  sharp by SeedVR2 x4 (a 270 px crop becomes a 1080 px face with its scar still on it), and turned
  from there. A close-up picture you supply is used instead of the crop.

HD
  SeedVR2 3B (int8) restores and doubles every view in ~5 s; RealESRGAN x4 is quicker but paints
  skin as plastic next to it (MEASURED on the same crop), so it is only the fallback.

THE CHECK
  Two things are measured on every view and one retry is made on a new seed when either trips:
    colours    the subject's colour histogram against the source's (characters and items only):
               a character's own views scored 0.71-0.93, two different characters 0.00-0.01, so
               under 0.55 is flagged. An item's back can honestly be another colour (a radio's
               plain green back scored 0.52 against its chrome front), so an item is flagged only
               under 0.40 - which catches a different object, not a subtle one.
    unchanged  mean pixel difference from its source under 3.0 (of 255) on a view meant to move the
               camera: a real back view of a man in a dark coat scored 5.3, a "high angle" that did
               nothing 2.4.
  Neither judges a face. What is flagged says so on the page, and every view has a redo.
"""
import argparse
import json
import math
import os
import re
import shutil
import sys
import time

STUDIO = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(STUDIO)
SHEETS = os.path.join(STUDIO, "sheets")
TRASH = os.path.join(SHEETS, "_trash")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

KINDS = ("character", "item", "place")
ITEM_TYPES = ("object", "weapon", "clothing")
GREY = (118, 118, 118)
ANGLES = 0.85          # the multiple-angles LoRA; 0 means the plain edit model
SEED = 21              # the measured seed; a retry or a redo moves on from here
PALETTE_MIN = {"character": 0.55, "item": 0.40}   # an item's back may be another colour (a radio's is plain green)
UNCHANGED_MAX = 3.0
KEEP = " Keep every building, object and the camera exactly the same."

AZIMUTHS = [            # key, the LoRA's word, what the sheet calls it
    ("front", "front view", "front"),
    ("front_r", "front-right quarter view", "front 3/4 right"),
    ("right", "right side view", "right side"),
    ("back_r", "back-right quarter view", "back 3/4 right"),
    ("back", "back view", "back"),
    ("back_l", "back-left quarter view", "back 3/4 left"),
    ("left", "left side view", "left side"),
    ("front_l", "front-left quarter view", "front 3/4 left"),
]
FACE_VIEWS = [
    ("front", "front view", "face, front"),
    ("front_r", "front-right quarter view", "face, 3/4"),
    ("right", "right side view", "face, profile"),
    ("back_l", "back-left quarter view", "face, rear 3/4"),
]
EXPRESSIONS = [         # the Foundry's own six, less "neutral" (that is the front face)
    ("joy", "joy", "laughing, eyes crinkled, plainly delighted"),
    ("anger", "anger", "furious, brows drawn down, jaw set"),
    ("fear", "fear", "frightened, eyes wide, drawn back"),
    ("sorrow", "sorrow", "grieving, eyes lowered, mouth tight"),
    ("surprise", "surprise", "caught off guard, brows up, eyes wide, mouth open"),
]
ITEM_VIEWS = [          # key, azimuth, elevation, label
    ("front", "front view", "eye-level shot", "front"),
    ("front_r", "front-right quarter view", "eye-level shot", "front 3/4"),
    ("right", "right side view", "eye-level shot", "side"),
    ("back", "back view", "eye-level shot", "back"),
    ("left", "left side view", "eye-level shot", "other side"),
    ("back_l", "back-left quarter view", "eye-level shot", "back 3/4"),
    ("top", "front view", "high-angle shot", "from above"),
]
PLACE_VIEWS = [
    ("left", "left side view", "eye-level shot", "from the left"),
    ("right", "right side view", "eye-level shot", "from the right"),
    ("reverse", "back view", "eye-level shot", "reverse"),
    ("back_r", "back-right quarter view", "eye-level shot", "reverse 3/4"),
    ("high_l", "front-left quarter view", "elevated shot", "raised, left"),
    ("high_r", "front-right quarter view", "elevated shot", "raised, right"),
    ("aerial", "front view", "high-angle shot", "aerial"),
]
TIMES = {               # key: (label, sentence) - midday, golden, night and rain MEASURED; the rest the same form
    "dawn": ("dawn", "Change the time of day to dawn, soft pale light, mist low on the ground."),
    "midday": ("midday", "Change the time of day to bright midday under a clear sky."),
    "golden": ("golden hour", "Change the time of day to golden hour, low warm sun from the side, long shadows."),
    "night": ("night", "Change the time of day to deep night, lit only by the lamps and windows."),
    "rain": ("rain", "Make it pouring with rain, wet reflective surfaces, overcast grey sky."),
    "snow": ("snow", "Cover everything in fresh snow under a cold overcast winter sky."),
    "fog": ("fog", "Fill the scene with thick fog, soft grey light, the distance fading away."),
}
TIME_ORDER = ["dawn", "midday", "golden", "night", "rain", "snow", "fog"]

FINISH_BODY = ("the same {s} standing, full body visible from head to feet, arms relaxed at the sides, "
               "plain flat grey background, the same clothes and hair")
UPRIGHT = ("the same {s} standing upright, floating centred on a plain mid-grey background, "
           "the whole {s} visible from end to end, front view")
DETAIL = ("an extreme close-up of the most detailed part of the same {s}, filling the frame, "
          "sharp focus, same lighting, same background")
WORN = "a person wearing exactly this outfit, standing, full body, head to feet visible, plain grey background"
FLAT = "the outfit laid out flat, seen from directly above, flat lay on a plain grey background"
EXPR = "the same {s} {w}, same framing, same lighting, plain grey background"

GROUP_TITLES = {"turnaround": "Turnaround", "faces": "Face", "expressions": "Expressions",
                "details": "Detail", "worn": "Worn", "angles": "Angles", "times": "Time of day"}
DEFAULT_SUBJECT = {"character": "person", "item": "object", "place": "place"}


# ─── the record ────────────────────────────────────────────────────────────────────────────────

def sheet_dir(sid):
    return os.path.join(SHEETS, sid)


def _slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")[:40]
    return s or "sheet"


def load(sid):
    if not re.match(r"^[a-z0-9][a-z0-9-]{0,60}$", sid or ""):
        raise KeyError("no such sheet: %r" % sid)
    p = os.path.join(sheet_dir(sid), "sheet.json")
    if not os.path.isfile(p):
        raise KeyError("no such sheet: %r" % sid)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(s):
    d = sheet_dir(s["id"])
    os.makedirs(d, exist_ok=True)
    s["updated"] = int(time.time())
    tmp = os.path.join(d, ".sheet.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=1)
    os.replace(tmp, os.path.join(d, "sheet.json"))


def listing():
    out = []
    if not os.path.isdir(SHEETS):
        return out
    for sid in sorted(os.listdir(SHEETS)):
        if sid.startswith(("_", ".")):
            continue
        try:
            out.append(load(sid))
        except (KeyError, ValueError, OSError):
            continue
    out.sort(key=lambda s: -s.get("updated", 0))
    return out


def new(kind, name, pictures, subject="", item_type="object", options=None):
    """pictures: [(path_or_PIL_image, role)] with role main | closeup | extra. The main picture is
    the one every angle is turned from."""
    from PIL import Image
    if kind not in KINDS:
        raise ValueError("kind must be one of %s" % ", ".join(KINDS))
    if item_type not in ITEM_TYPES:
        item_type = "object"
    if not pictures or not any(r == "main" for _, r in pictures):
        raise ValueError("a sheet needs its main picture")
    os.makedirs(SHEETS, exist_ok=True)
    base = _slug(name)
    sid, n = base, 2
    while os.path.exists(sheet_dir(sid)) or os.path.exists(os.path.join(TRASH, sid)):
        sid, n = "%s-%d" % (base, n), n + 1
    d = sheet_dir(sid)
    os.makedirs(os.path.join(d, "_work"), exist_ok=True)
    o = {"faces": True, "expressions": True, "finish_body": True, "hd": "x2",
         "upright": item_type == "weapon", "times": ["midday", "golden", "night", "rain"]}
    o.update(options or {})
    sources = []
    for i, (pic, role) in enumerate(pictures):
        im = pic if hasattr(pic, "save") else Image.open(pic)
        im = im.convert("RGB")
        if max(im.size) > 2048:                         # the edit model works at ~1 MP anyway
            r = 2048 / max(im.size)
            im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
        fn = "source_%d.png" % (i + 1)
        im.save(os.path.join(d, fn))
        _thumb(os.path.join(d, fn), os.path.join(d, "_work", "thumbs", "source_%d.jpg" % (i + 1)))
        sources.append({"file": fn, "role": role, "size": list(im.size)})
    s = {"id": sid, "kind": kind, "name": (name or sid).strip()[:80],
         "subject": (subject or "").strip()[:40] or DEFAULT_SUBJECT[kind],
         "item_type": item_type if kind == "item" else "", "created": int(time.time()),
         "options": o, "sources": sources, "views": {}, "prep": {}, "sent": []}
    save(s)
    return s


def source(s, role):
    f = next((x["file"] for x in s["sources"] if x["role"] == role), None)
    return os.path.join(sheet_dir(s["id"]), f) if f else None


# ─── the plan ──────────────────────────────────────────────────────────────────────────────────

def sks(azimuth, elevation, distance):
    return "<sks> %s %s %s" % (azimuth, elevation, distance)


def plan(s):
    """Every view this sheet should hold, in the order the sheet lays them out."""
    k, o, subj = s["kind"], s.get("options") or {}, s.get("subject") or DEFAULT_SUBJECT[s["kind"]]
    out = []

    def v(key, group, label, src, prompt, angles, moves=False, colours=False, op="edit"):
        out.append({"key": key, "group": group, "label": label, "src": src, "prompt": prompt,
                    "angles": angles, "moves": moves, "colours": colours, "op": op})

    if k == "character":
        for key, az, label in AZIMUTHS:
            v("turn_" + key, "turnaround", label, "base", sks(az, "eye-level shot", "medium shot"),
              ANGLES, moves=key != "front", colours=True)
        if o.get("faces", True):
            for key, az, label in FACE_VIEWS:
                v("face_" + key, "faces", label, "face", sks(az, "eye-level shot", "close-up"),
                  ANGLES, moves=key != "front", colours=True)
        if o.get("expressions", True):
            for key, label, words in EXPRESSIONS:
                v("expr_" + key, "expressions", label, "face", EXPR.format(s=subj, w=words), 0, colours=True)
    elif k == "item":
        for key, az, elev, label in ITEM_VIEWS:
            if key == "top" and o.get("upright"):
                continue        # from above, a sword stood on its point is its pommel: it came back unmoved
            v("turn_" + key, "turnaround", label, "base", sks(az, elev, "medium shot"),
              ANGLES, moves=key != "front", colours=True)
        v("detail", "details", "detail", "main", DETAIL.format(s=subj), 0)
        if source(s, "closeup"):
            v("closeup", "details", "your close-up, restored", "closeup", "", 0, op="restore")
        if s.get("item_type") == "clothing":
            v("worn_front", "worn", "worn", "main", WORN, 0)
            v("worn_back", "worn", "worn, back", "worn_front", sks("back view", "eye-level shot", "medium shot"),
              ANGLES, moves=True)
            v("flat", "worn", "flat lay", "main", FLAT, 0)
    else:
        for key, az, elev, label in PLACE_VIEWS:
            v("angle_" + key, "angles", label, "base", sks(az, elev, "wide shot"), ANGLES, moves=True)
        for t in TIME_ORDER:
            if t in (o.get("times") or []):
                v("time_" + t, "times", TIMES[t][0], "base", TIMES[t][1] + KEEP, 0)
    return out


def estimate(s):
    """Seconds, from what the lab measured: ~6 s an edit, ~5 s a SeedVR2 x2 pass (x4 ~3x that),
    ~3 s a cut-out, and ~15 s the first time the models load."""
    views = plan(s)
    todo = [v for v in views if (s.get("views") or {}).get(v["key"], {}).get("status") != "done"]
    hd = (s.get("options") or {}).get("hd", "x2")
    per_hd = {"off": 0, "x2": 5, "x4": 15}.get(hd, 5)
    prep = 0 if s.get("prep", {}).get("base") else {"character": 20, "item": 12, "place": 2}[s["kind"]]
    return int(15 + prep + len(todo) * (6 + per_hd) + 4)


# ─── ComfyUI ───────────────────────────────────────────────────────────────────────────────────

def _comfy():
    from comfy import run, set_path
    from epic import load_wf, ensure_local, HOST, COMFY
    return run, set_path, load_wf, ensure_local, HOST, COMFY


def comfy_ok():
    import urllib.request
    _, _, _, _, HOST, _ = _comfy()
    try:
        urllib.request.urlopen("http://%s/system_stats" % HOST, timeout=5).read()
        return True
    except Exception:
        return False


def _stage(src, name):
    _, _, _, _, _, COMFY = _comfy()
    shutil.copy(src, os.path.join(COMFY, "input", name))
    return name


def _fetch(outs, dest, pick=None):
    _, _, _, ensure_local, _, _ = _comfy()
    rel = next((o for o in outs if pick is None or pick(o)), None)
    if not rel:
        raise RuntimeError("ComfyUI returned no picture")
    if os.path.exists(dest):
        os.remove(dest)                                 # ensure_local keeps an existing file
    got = ensure_local(rel, dest)
    if not got or not os.path.exists(dest):
        raise RuntimeError("could not fetch %s from ComfyUI" % rel)
    return dest


def edit(images, prompt, seed, angles, dest, tag):
    """The edit model on one picture (a second becomes image2), with or without the angles LoRA."""
    run, set_path, load_wf, _, HOST, _ = _comfy()
    wf = load_wf("32_qwen_turnaround.json")
    set_path(wf, "7.inputs.image", _stage(images[0], "sheet_%s.png" % tag))
    if angles and angles > 0:
        set_path(wf, "40.inputs.strength_model", angles)
    else:
        wf["5"]["inputs"]["model"] = ["4", 0]           # straight past the angles LoRA
        del wf["40"]
    if len(images) > 1:
        wf["70"] = {"class_type": "LoadImage", "inputs": {"image": _stage(images[1], "sheet_%s_b.png" % tag)}}
        wf["71"] = {"class_type": "FluxKontextImageScale", "inputs": {"image": ["70", 0]}}
        wf["10"]["inputs"]["image2"] = ["71", 0]
        wf["12"]["inputs"]["image2"] = ["71", 0]
    set_path(wf, "10.inputs.prompt", prompt)
    set_path(wf, "15.inputs.seed", seed)
    set_path(wf, "17.inputs.filename_prefix", "claude-generated/sheets/%s" % tag)
    _, outs = run(HOST, wf, quiet=True)
    return _fetch(outs, dest)


def matte(src, dest, tag):
    """BiRefNet (workflow 14) to a real RGBA cut-out."""
    from PIL import Image
    run, set_path, load_wf, _, HOST, _ = _comfy()
    w, h = Image.open(src).size
    wf = load_wf("14_birefnet_matte.json")
    set_path(wf, "1.inputs.image", _stage(src, "sheet_m_%s.png" % tag))
    set_path(wf, "8.inputs.width", w)
    set_path(wf, "8.inputs.height", h)
    # only the cut-out is kept; the mask and the magenta proof are dropped from the graph
    for n in ("6", "8", "9", "11", "12"):
        wf.pop(n, None)
    set_path(wf, "10.inputs.filename_prefix", "claude-generated/sheets/m_%s" % tag)
    _, outs = run(HOST, wf, quiet=True)
    return _fetch(outs, dest)


def restore(src, dest, mult, tag):
    """SeedVR2 3B int8: restore and enlarge. RealESRGAN x4 if the SeedVR2 graph is refused."""
    run, set_path, load_wf, _, HOST, _ = _comfy()
    staged = _stage(src, "sheet_r_%s.png" % tag)
    wf = {
        "1": {"class_type": "LoadImage", "inputs": {"image": staged}},
        "2": {"class_type": "ImageScaleBy", "inputs": {"image": ["1", 0], "upscale_method": "lanczos", "scale_by": float(mult)}},
        "3": {"class_type": "SeedVR2Preprocess", "inputs": {"resized_images": ["2", 0]}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "seedvr2_ema_vae_fp16.safetensors"}},
        "5": {"class_type": "VAEEncodeTiled", "inputs": {"pixels": ["3", 0], "vae": ["4", 0], "tile_size": 512,
                                                         "overlap": 128, "temporal_size": 4096, "temporal_overlap": 8}},
        "6": {"class_type": "UNETLoader", "inputs": {"unet_name": "seedvr2_3b_int8_convrot.safetensors", "weight_dtype": "default"}},
        "7": {"class_type": "SeedVR2Conditioning", "inputs": {"model": ["6", 0], "vae_conditioning": ["5", 0]}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["6", 0], "positive": ["7", 0], "negative": ["7", 1],
                                                   "latent_image": ["5", 0], "seed": 7, "steps": 1, "cfg": 1.0,
                                                   "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "9": {"class_type": "VAEDecodeTiled", "inputs": {"samples": ["8", 0], "vae": ["4", 0], "tile_size": 512,
                                                         "overlap": 128, "temporal_size": 4096, "temporal_overlap": 8}},
        "10": {"class_type": "SeedVR2PostProcessing", "inputs": {"images": ["9", 0], "original_resized_images": ["2", 0],
                                                                 "color_correction_method": "lab"}},
        "11": {"class_type": "SaveImage", "inputs": {"images": ["10", 0], "filename_prefix": "claude-generated/sheets/r_%s" % tag}},
    }
    try:
        _, outs = run(HOST, wf, quiet=True)
        return _fetch(outs, dest)
    except RuntimeError as e:
        if "rejected" not in str(e):
            raise
    wf = load_wf("69_esrgan_upscale.json")              # the fallback, then brought to size
    set_path(wf, "1.inputs.image", staged)
    set_path(wf, "4.inputs.filename_prefix", "claude-generated/sheets/e_%s" % tag)
    _, outs = run(HOST, wf, quiet=True)
    _fetch(outs, dest)
    from PIL import Image
    im = Image.open(src)
    Image.open(dest).resize((round(im.width * mult), round(im.height * mult)), Image.LANCZOS).save(dest)
    return dest


# ─── pictures ─────────────────────────────────────────────────────────────────────────────────

def _alpha_box(rgba, thr=24):
    a = rgba.getchannel("A").point(lambda v: 255 if v > thr else 0)
    return a.getbbox()


def truncated(rgba_path):
    """True when the cut-out runs off the bottom edge - a head-and-shoulders picture, a waist-up
    crop - so there is no body to turn."""
    from PIL import Image
    im = Image.open(rgba_path).convert("RGBA")
    a = im.getchannel("A")
    W, H = im.size
    row = a.crop((0, H - max(2, H // 100), W, H)).point(lambda v: 255 if v > 64 else 0)
    box = row.getbbox()
    return bool(box) and (box[2] - box[0]) > W * 0.06


def on_grey(rgba_path, dest, canvas=None, fill=0.86):
    """The cut-out centred on flat grey. canvas None picks portrait, landscape or square from the
    subject's own shape. Writes dest and dest's alpha beside it (…_alpha.png) for the head crop."""
    from PIL import Image
    im = Image.open(rgba_path).convert("RGBA")
    box = _alpha_box(im)
    if not box:
        raise RuntimeError("the cut-out is empty - nothing was found in the picture")
    fig = im.crop(box)
    if canvas is None:
        r = fig.height / max(1, fig.width)
        canvas = (896, 1216) if r > 1.25 else (1216, 832) if r < 0.8 else (1024, 1024)
    W, H = canvas
    k = min(W * 0.9 / fig.width, H * fill / fig.height)
    fig = fig.resize((max(1, round(fig.width * k)), max(1, round(fig.height * k))), Image.LANCZOS)
    x, y = (W - fig.width) // 2, (H - fig.height) // 2
    out = Image.new("RGBA", (W, H), GREY + (255,))
    out.alpha_composite(fig, (x, y))
    out.convert("RGB").save(dest)
    alpha = Image.new("L", (W, H), 0)
    alpha.paste(fig.getchannel("A"), (x, y))
    alpha.save(dest[:-4] + "_alpha.png")
    return dest


def head_crop(base_png, dest, frac=0.26):
    """The head and shoulders, squared, from the figure on its grey canvas."""
    from PIL import Image
    import numpy as np
    a = np.asarray(Image.open(base_png[:-4] + "_alpha.png"), dtype=np.float32) / 255.0
    rows = np.where(a.max(axis=1) > 0.1)[0]
    if not len(rows):
        raise RuntimeError("no figure to crop a face from")
    top, bot = int(rows[0]), int(rows[-1])
    fh = bot - top
    band = a[top:top + max(4, int(fh * 0.08))]
    cols = band.sum(axis=0)
    cx = float((cols * np.arange(len(cols))).sum() / max(1e-6, cols.sum()))
    im = Image.open(base_png).convert("RGB")
    W, H = im.size
    side = int(max(64, fh * frac))
    left = int(max(0, min(W - side, cx - side / 2)))
    t = int(max(0, top - side * 0.08))
    crop = im.crop((left, t, left + side, min(H, t + side)))
    crop.save(dest)
    return dest, crop.size


def _grey_small(p, n=128):
    from PIL import Image
    import numpy as np
    return np.asarray(Image.open(p).convert("L").resize((n, n), Image.BILINEAR), dtype=np.float32)


def _fg_hist(p, bins=12):
    from PIL import Image
    import numpy as np
    hsv = np.asarray(Image.open(p).convert("HSV").resize((256, 256)), dtype=np.float32)
    rgb = np.asarray(Image.open(p).convert("RGB").resize((256, 256)), dtype=np.float32)
    edge = np.concatenate([rgb[:8].reshape(-1, 3), rgb[:, :8].reshape(-1, 3), rgb[:, -8:].reshape(-1, 3)])
    bg = np.median(edge, axis=0)
    mask = np.abs(rgb - bg).sum(axis=2) > 40
    if mask.sum() < 50:
        mask = np.ones(mask.shape, bool)
    hist, _ = np.histogramdd(np.stack([hsv[..., 0][mask], hsv[..., 1][mask], hsv[..., 2][mask]], 1),
                             bins=(bins, 4, 4), range=((0, 256), (0, 256), (0, 256)))
    return hist.ravel() / max(1, hist.sum())


def check(kind, view, src, out):
    """-> (measures, flag). See THE CHECK in the module docstring."""
    import numpy as np
    m, flags = {}, []
    if view.get("colours") and kind in ("character", "item"):
        m["colours"] = round(float(np.minimum(_fg_hist(src), _fg_hist(out)).sum()), 3)
        if m["colours"] < PALETTE_MIN.get(kind, 0.55):
            flags.append("colours drifted from the source")
    if view.get("moves"):
        m["change"] = round(float(np.abs(_grey_small(src) - _grey_small(out)).mean()), 2)
        if m["change"] < UNCHANGED_MAX:
            flags.append("came back almost unchanged")
    return m, "; ".join(flags)


# ─── making ───────────────────────────────────────────────────────────────────────────────────

class Stopped(Exception):
    pass


def _lock_path(sid):
    return os.path.join(sheet_dir(sid), "_work", "making.lock")


def locked_by(sid):
    """The pid of a live process making this sheet, or None. The page's server and this command
    line can both make sheets; the lock keeps them off the same one at the same time."""
    try:
        with open(_lock_path(sid)) as f:
            pid = int(f.read().split()[0])
    except (OSError, ValueError, IndexError):
        return None
    try:
        os.kill(pid, 0)
    except OSError:
        return None                                     # its holder died: the lock is stale
    return pid


def _src_for(s, view):
    d = sheet_dir(s["id"])
    src = view["src"]
    if src == "base":
        return os.path.join(d, s["prep"]["base"])
    if src == "face":
        return os.path.join(d, s["prep"]["face"])
    if src in ("main", "closeup"):
        return source(s, src)
    got = (s["views"].get(src) or {}).get("file")
    if not got:
        raise RuntimeError("%s needs %s first" % (view["key"], src))
    return os.path.join(d, got)


def prepare(s, log, tag):
    """Make the picture every angle turns from: the figure or the item cut out onto grey (a body
    finished first if the picture stops at the shoulders; a weapon stood upright first), and a
    face close-up for a character. A place is used as it is."""
    from PIL import Image
    d = sheet_dir(s["id"])
    w = os.path.join(d, "_work")
    os.makedirs(w, exist_ok=True)
    main = source(s, "main")
    subj = s.get("subject") or DEFAULT_SUBJECT[s["kind"]]
    o = s.get("options") or {}
    p = s.setdefault("prep", {})
    if s["kind"] == "character":
        if not p.get("base"):
            log("cutting the figure out")
            rgba = matte(main, os.path.join(w, "main_rgba.png"), tag + "_main")
            if truncated(rgba) and o.get("finish_body", True):
                log("the picture stops above the feet - finishing the body")
                pre = on_grey(rgba, os.path.join(w, "pre_grey.png"))
                full = edit([pre], FINISH_BODY.format(s=subj), SEED, 0, os.path.join(w, "finished.png"),
                            tag + "_finish")
                rgba = matte(full, os.path.join(w, "finished_rgba.png"), tag + "_fin")
                p["finished_body"] = True
            on_grey(rgba, os.path.join(d, "base.png"), canvas=(896, 1216), fill=0.86)
            p["base"] = "base.png"
            _thumb(os.path.join(d, "base.png"), os.path.join(w, "thumbs", "base.jpg"))
        if not p.get("face") and (o.get("faces", True) or o.get("expressions", True)):
            close = source(s, "closeup")
            if close:
                # your own close-up: cut out onto grey; a small one is restored at its new size
                log("cutting out your close-up")
                crgba = matte(close, os.path.join(w, "close_rgba.png"), tag + "_close")
                crop = on_grey(crgba, os.path.join(w, "face_crop.png"), canvas=(1024, 1024), fill=0.92)
                mult = 1 if min(Image.open(close).size) < 700 else 0
            else:
                log("cropping the face from the figure")
                crop, (side, _) = head_crop(os.path.join(d, "base.png"), os.path.join(w, "face_crop.png"))
                mult = 4 if side < 400 else 2 if side < 700 else 0
            if mult:
                log("sharpening the face with SeedVR2%s" % (" x%d" % mult if mult > 1 else ""))
                restore(crop, os.path.join(d, "face.png"), mult, tag + "_face")
            else:
                shutil.copy(crop, os.path.join(d, "face.png"))
            p["face"] = "face.png"
            _thumb(os.path.join(d, "face.png"), os.path.join(w, "thumbs", "face.jpg"))
    elif s["kind"] == "item":
        src = main
        if o.get("upright"):
            log("standing the %s upright" % subj)
            src = edit([main], UPRIGHT.format(s=subj), SEED, 0, os.path.join(w, "upright.png"), tag + "_up")
            p["upright"] = True
        log("cutting the %s out" % subj)
        rgba = matte(src, os.path.join(w, "main_rgba.png"), tag + "_main")
        on_grey(rgba, os.path.join(d, "base.png"), fill=0.8)
        p["base"] = "base.png"
        _thumb(os.path.join(d, "base.png"), os.path.join(w, "thumbs", "base.jpg"))
    else:
        im = Image.open(main)
        if max(im.size) < 1000:
            log("the picture is small - restoring it first")
            restore(main, os.path.join(d, "base.png"), 2, tag + "_base")
        else:
            shutil.copy(main, os.path.join(d, "base.png"))
        p["base"] = "base.png"
        _thumb(os.path.join(d, "base.png"), os.path.join(w, "thumbs", "base.jpg"))
    save(s)


def _thumb(src, dest, h=420):
    from PIL import Image
    im = Image.open(src).convert("RGB")
    im.thumbnail((int(h * 2.2), h), Image.LANCZOS)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    im.save(dest, quality=84)


def make(sid, log=print, progress=None, stopped=lambda: False, redo=None):
    """Make whatever this sheet still lacks (and remake `redo`), check it, lift it to HD and lay the
    sheet out. Safe to run again: done views are kept. One maker per sheet (see locked_by)."""
    load(sid)
    holder = locked_by(sid)
    if holder and holder != os.getpid():
        raise RuntimeError("this sheet is already being made by another process (%d)" % holder)
    lp = _lock_path(sid)
    os.makedirs(os.path.dirname(lp), exist_ok=True)
    with open(lp, "w") as f:
        f.write("%d %d\n" % (os.getpid(), int(time.time())))
    try:
        return _make(sid, log, progress, stopped, redo)
    finally:
        try:
            os.remove(lp)
        except OSError:
            pass


def _make(sid, log, progress, stopped, redo):
    s = load(sid)
    d = sheet_dir(sid)
    tag = "%s_%d" % (sid[:24], int(time.time()) % 100000)
    redo = set(redo or [])
    if not comfy_ok():
        raise RuntimeError("ComfyUI is not answering on the box - start it and try again")
    views = plan(s)
    for v in views:                                     # a redo also remakes what is built on it
        if v["src"] in redo:
            redo.add(v["key"])
    todo = [v for v in views if v["key"] in redo or (s["views"].get(v["key"]) or {}).get("status") != "done"]
    todo_keys = {v["key"] for v in todo}
    hd = (s.get("options") or {}).get("hd", "x2")
    # HD for what is made now, and for anything an interrupted run left without it
    need_hd = [] if hd == "off" else [v for v in views if v["key"] in todo_keys or
                                      not (s["views"].get(v["key"]) or {}).get("hd")]
    o = s.get("options") or {}
    wants_face = s["kind"] == "character" and (o.get("faces", True) or o.get("expressions", True))
    must_prep = not s.get("prep", {}).get("base") or (wants_face and not s["prep"].get("face"))
    total = len(todo) + len(need_hd) + (1 if must_prep else 0) + 1
    done = [0]

    def step(msg=None):
        done[0] += 1
        if progress:
            progress(done[0], total, msg)

    if progress:
        progress(0, total, "starting")
    if must_prep:
        prepare(s, log, tag)
        step("prepared")
    from PIL import Image
    for v in todo:
        if stopped():
            raise Stopped()
        s = load(sid)
        key = v["key"]
        rec = s["views"].get(key) or {}
        tries = rec.get("tries", 0)
        src = _src_for(s, v)
        ref = os.path.join(d, s["prep"]["face"]) if v["src"] == "face" else \
            os.path.join(d, s["prep"]["base"]) if v["src"] == "base" else src
        dest = os.path.join(d, "views", key + ".png")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        t0 = time.time()
        if v["op"] == "restore":
            side = min(Image.open(src).size)
            restore(src, dest, 4 if side < 400 else 2, "%s_%s" % (tag, key))
            m, flag, seed = {}, "", None
        else:
            seed = SEED + 2 * tries                     # 21, then 23, 25 ... a retry takes the odd one between
            log("%s: %s" % (v["label"], v["prompt"][:90]))
            edit([src], v["prompt"], seed, v["angles"], dest, "%s_%s" % (tag, key))
            m, flag = check(s["kind"], v, ref, dest)
            if flag:
                log("  %s - %s; trying another seed" % (v["label"], flag))
                alt = dest[:-4] + "_alt.png"
                edit([src], v["prompt"], seed + 1, v["angles"], alt, "%s_%s_b" % (tag, key))
                m2, flag2 = check(s["kind"], v, ref, alt)
                better = (not flag2) or (m2.get("colours", 1) > m.get("colours", 1)) or \
                         (m2.get("change", 99) > m.get("change", 99))
                if better:
                    os.replace(alt, dest)
                    m, flag, seed = m2, flag2, seed + 1
                else:
                    os.remove(alt)
                if flag:
                    log("  %s still flagged: %s" % (v["label"], flag))
        s = load(sid)                                   # the page may have renamed it meanwhile
        s["views"][key] = {"file": "views/%s.png" % key, "status": "done", "seed": seed,
                           "tries": tries + 1, "check": m, "flag": flag,
                           "secs": round(time.time() - t0, 1), "at": int(time.time()), "hd": ""}
        _thumb(dest, os.path.join(d, "_work", "thumbs", key + ".jpg"))
        save(s)
        step(v["label"])
    if need_hd:
        mult = 4 if hd == "x4" else 2
        for v in need_hd:
            if stopped():
                raise Stopped()
            key = v["key"]
            s = load(sid)
            rec = s["views"].get(key) or {}
            if rec.get("status") != "done":
                step()
                continue
            src = os.path.join(d, rec["file"])
            dest = os.path.join(d, "hd", key + ".png")
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if v["op"] == "restore" and max(Image.open(src).size) >= 1600:
                shutil.copy(src, dest)                  # already restored
            else:
                log("HD: %s" % v["label"])
                restore(src, dest, mult, "%s_%s_hd" % (tag, key))
            s = load(sid)
            s["views"][key]["hd"] = "hd/%s.png" % key
            s["views"][key]["hd_size"] = list(Image.open(dest).size)
            save(s)
            step("HD " + v["label"])
    log("laying out the sheet")
    compose(sid)
    step("sheet laid out")
    return load(sid)


# ─── into the Foundry ─────────────────────────────────────────────────────────────────────────

FOUNDRY_KEYS = {        # a Foundry pack's own names <- this sheet's views (@base / @face: the prepared pictures)
    "character": {
        "base_fullbody": "@base", "base_portrait": "@face",
        "turn_front": "turn_front", "turn_front_three_quarter": "turn_front_r", "turn_side": "turn_right",
        "turn_back_three_quarter": "turn_back_r", "turn_back": "turn_back",
        "face_front": "face_front", "face_three_quarter": "face_front_r", "face_side": "face_right",
        "expr_neutral": "face_front", "expr_joy": "expr_joy", "expr_anger": "expr_anger",
        "expr_fear": "expr_fear", "expr_sorrow": "expr_sorrow", "expr_surprise": "expr_surprise"},
    "prop": {"hero": "turn_front", "macro": "detail"},
    "costume": {"card": "turn_front"},
}


def foundry_images(sid, atype, adir):
    """Copy this sheet's pictures into a Foundry asset's folder under the Foundry's names; -> the
    asset's `images` dict. Used by the page's "Save to the Foundry" and by the Foundry's own
    "from an image", so a pack made from a picture is that picture turned, not a lookalike."""
    s = load(sid)
    d = sheet_dir(sid)
    os.makedirs(adir, exist_ok=True)
    out = {}
    for fkey, skey in FOUNDRY_KEYS[atype].items():
        if skey == "@base":
            p = os.path.join(d, s["prep"]["base"]) if s.get("prep", {}).get("base") else None
        elif skey == "@face":
            p = os.path.join(d, s["prep"]["face"]) if s.get("prep", {}).get("face") else None
        else:
            rec = s["views"].get(skey) or {}
            rel = rec.get("hd") or rec.get("file")
            p = os.path.join(d, rel) if rel else None
        if p and os.path.isfile(p):
            shutil.copy(p, os.path.join(adir, fkey + ".png"))
            out[fkey] = fkey + ".png"
    return out


# ─── the sheet itself ─────────────────────────────────────────────────────────────────────────

def _font(size, bold=False):
    """Liberation Sans is what this box (Fedora) has; DejaVu is the Debian spelling; Pillow's own
    scalable default is the last resort - never the 11 px bitmap, which vanishes on a 4096 px sheet."""
    from PIL import ImageFont
    b = "-Bold" if bold else "-Regular"
    for p in ("/usr/share/fonts/liberation-sans-fonts/LiberationSans%s.ttf" % b,
              "/usr/share/fonts/liberation-sans/LiberationSans%s.ttf" % b,
              "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else "")):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def compose(sid, width=4096):
    """One picture: the name, the source, then each group of views in rows, every cell labelled.
    sheet.png at full width, and a 1600 px preview for the page."""
    from PIL import Image, ImageDraw
    s = load(sid)
    d = sheet_dir(sid)
    views = [v for v in plan(s) if (s["views"].get(v["key"]) or {}).get("status") == "done"]
    groups = []
    for v in views:
        if not groups or groups[-1][0] != v["group"]:
            groups.append((v["group"], []))
        groups[-1][1].append(v)
    pad, gap, lab = 48, 16, 44
    ink, dim, paper = (24, 24, 28), (110, 110, 120), (246, 246, 243)
    blocks = []                                         # (title, [(label, img)])
    srcs = [("your picture" if x["role"] == "main" else "your close-up" if x["role"] == "closeup"
             else "also supplied", os.path.join(d, x["file"])) for x in s["sources"]]
    blocks.append(("Source", [(r, Image.open(p).convert("RGB")) for r, p in srcs]))
    for g, vs in groups:
        cells = []
        for v in vs:
            rec = s["views"][v["key"]]
            p = os.path.join(d, rec.get("hd") or rec["file"])
            cells.append((v["label"], Image.open(p).convert("RGB")))
        blocks.append((GROUP_TITLES.get(g, g), cells))
    inner = width - 2 * pad
    rows = []                                           # (title or None, [(label, img)], height)
    for title, cells in blocks:
        # as many to a row as keeps a cell about 700 px tall: 8 standing figures, 4 landscapes
        avg = sum(im.width / im.height for _, im in cells) / len(cells)
        n = max(2, min(8, round(inner / (700 * avg))))
        n = min(n, len(cells))
        cap = 700 if title == "Source" else 800 if len(cells) < 3 else 1100
        h = min(cap, int((inner - gap * (n - 1)) / (avg * n)))
        for i in range(0, len(cells), n):
            rows.append((title if i == 0 else None, cells[i:i + n], h))
    H = pad + 96 + sum((56 if t else 0) + lab + h + gap for t, _, h in rows) + pad
    sheet = Image.new("RGB", (width, H), paper)
    dr = ImageDraw.Draw(sheet)
    dr.text((pad, pad), s["name"], fill=ink, font=_font(60, True))
    kind = s["kind"] if s["kind"] != "item" else "%s (%s)" % (s.get("subject") or "item", s.get("item_type") or "object")
    dr.text((pad, pad + 70), "%s sheet  ·  %d views  ·  %s" % (kind, len(views), time.strftime("%Y-%m-%d")),
            fill=dim, font=_font(26))
    y = pad + 96 + 24
    f_title, f_lab = _font(34, True), _font(24)
    for title, chunk, h in rows:
        if title:
            dr.text((pad, y + 8), title, fill=ink, font=f_title)
            y += 56
        x = pad
        for label, im in chunk:
            w = int(im.width * h / im.height)
            dr.text((x + 2, y + 8), label, fill=dim, font=f_lab)
            sheet.paste(im.resize((w, h), Image.LANCZOS), (x, y + lab))
            x += w + gap
        y += lab + h + gap
    out = os.path.join(d, "sheet.png")
    sheet.save(out)
    prev = sheet.copy()
    prev.thumbnail((1600, 1600 * H // width + 1), Image.LANCZOS)
    os.makedirs(os.path.join(d, "_work"), exist_ok=True)
    prev.save(os.path.join(d, "_work", "sheet_preview.jpg"), quality=85)
    s = load(sid)
    s["sheet"] = {"file": "sheet.png", "size": [width, H], "views": len(views), "at": int(time.time())}
    save(s)
    return out


# ─── command line ─────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("kind", choices=KINDS)
    n.add_argument("picture")
    n.add_argument("--name", required=True)
    n.add_argument("--closeup")
    n.add_argument("--subject", default="")
    n.add_argument("--item-type", default="object", choices=ITEM_TYPES)
    n.add_argument("--no-faces", action="store_true")
    n.add_argument("--no-expressions", action="store_true")
    n.add_argument("--times", default="midday,golden,night,rain")
    n.add_argument("--hd", default="x2", choices=["off", "x2", "x4"])
    n.add_argument("--upright", choices=["yes", "no"], default=None)
    n.add_argument("--dry", action="store_true", help="create the sheet and print its plan, make nothing")
    m = sub.add_parser("make")
    m.add_argument("sheet")
    m.add_argument("--redo", default="")
    sub.add_parser("list")
    c = sub.add_parser("compose")
    c.add_argument("sheet")
    a = ap.parse_args()
    if a.cmd == "list":
        for s in listing():
            views = plan(s)
            done = sum(1 for v in views if (s["views"].get(v["key"]) or {}).get("status") == "done")
            print("%-28s %-9s %3d/%-3d %s" % (s["id"], s["kind"], done, len(views), s["name"]))
        return
    if a.cmd == "compose":
        print(compose(a.sheet))
        return
    if a.cmd == "new":
        pics = [(a.picture, "main")] + ([(a.closeup, "closeup")] if a.closeup else [])
        opts = {"faces": not a.no_faces, "expressions": not a.no_expressions, "hd": a.hd,
                "times": [t for t in a.times.split(",") if t in TIMES]}
        if a.upright:
            opts["upright"] = a.upright == "yes"
        s = new(a.kind, a.name, pics, a.subject, a.item_type, opts)
        print("sheet %s: %d views planned, about %d s" % (s["id"], len(plan(s)), estimate(s)))
        if a.dry:
            for v in plan(s):
                print("  %-14s %-12s %s" % (v["key"], v["group"], v["prompt"][:80]))
            return
        sid = s["id"]
    else:
        sid = a.sheet
    t0 = time.time()

    def prog(i, n, msg):
        print("  [%3.0fs] %d/%d %s" % (time.time() - t0, i, n, msg or ""), flush=True)
    s = make(sid, log=lambda m: print("   ", m, flush=True), progress=prog,
             redo=[k for k in (getattr(a, "redo", "") or "").split(",") if k])
    flagged = {k: v["flag"] for k, v in s["views"].items() if v.get("flag")}
    print("done in %.0fs: %s  (%d flagged%s)" % (time.time() - t0, os.path.join(sheet_dir(sid), "sheet.png"),
                                                 len(flagged), (": " + json.dumps(flagged)) if flagged else ""))


if __name__ == "__main__":
    main()
