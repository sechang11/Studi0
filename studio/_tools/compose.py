#!/usr/bin/env python3
"""compose.py - put a built-out character into a built-out place.

    python3 studio/_tools/compose.py --character bai-liwen --place night-market
    python3 studio/_tools/compose.py -c terra -p hilltop-temple --plate dawn_wide
    python3 studio/_tools/compose.py -c bai-liwen -p back-alley --framing close
    python3 studio/_tools/compose.py --matrix          # a spread of combinations

WHY IT IS FIVE STEPS AND NOT ONE PROMPT.

Handing both images to qwen-image-edit and asking for one in the other makes a
good picture of a DIFFERENT market. Measured: the left margin of a "relit"
composite sat 0.187 from the original plate, against 0.211 for the same market
at a different time of day. The model does not edit locally, it regenerates - so
anything you care about has to be kept out of its reach.

    1 paste      the character's cutout onto the plate, at a stated scale
    2 relight    that composite through qwen-image-edit, which fixes the light
                 on her and wrecks the market
    3 re-cut     take ONLY the relit character back out
    4 shadow     ground her - see below
    5 paste      onto the PRISTINE plate, which was never model-touched

Steps 1-3 spend the model on the one thing it is good at here and throw away the
rest of what it did. Plate fidelity after step 5 measures 0.004, i.e. the place
is the asset.

THE SHADOW IS GEOMETRIC, NOT PROMPTED, for the reason bobble.py gives about
heads: a model asked for a shadow may or may not draw one, and cannot be asked
for it in a fixed place. So it is built from the silhouette:

    contact pool   an ellipse at the feet, the width of her stance. This is what
                   actually stops a figure floating - not the long cast.
    directional    the silhouette squashed to a fraction of its height and
                   sheared by the light angle, anchored at the feet.

Both are blurred and multiplied under the character. Defaults are stated as
numbers rather than tuned invisibly, and --light lets a scene with an obvious
key move it.
"""
import argparse, json, os, shutil, sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(TOOLS))
for p in (TOOLS, os.path.join(ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

CHARS = os.path.join(ROOT, "studio", "foundry", "characters")
PLACES = os.path.join(ROOT, "studio", "foundry", "places")
OUT_DIR = os.path.join(ROOT, "studio", "foundry", "composites")
PROPS = os.path.join(ROOT, "studio", "foundry", "props")

# How tall a prop is in the world, in metres, by dictionary category. The depth
# pass sizes a 1.7 m person; a prop is that height scaled by this. An asset can
# override with "size_m" in its asset.json.
PROP_M = {"sword": 1.0, "staff": 1.7, "bow": 1.6, "dagger": 0.35, "umbrella": 0.95,
          "lantern": 0.4, "book": 0.25, "satchel": 0.4}
PROP_M_DEFAULT = 0.5

# Framing is (height as a fraction of frame, where the BOTTOM of the source image
# lands as a fraction of frame). Two tables, because the anchor means different
# things: the bottom of a full-body view is her feet, the bottom of a face view is
# her collarbone. One table with a fudge factor got this wrong twice - first a
# macro of an eyeball, then a head peeking over the bottom edge.
FRAMINGS_BODY = {
    "wide":   (0.62, 0.94),
    "full":   (0.78, 0.96),
    "medium": (1.35, 1.40),      # cropped at the waist by overflow
    "close":  (2.60, 2.35),      # head and shoulders by overflow
}
FRAMINGS_FACE = {
    "wide":   (0.34, 0.86),      # a face view cannot really do a wide - it is a bust
    "full":   (0.55, 0.95),
    "medium": (0.70, 1.00),
    "close":  (0.92, 1.06),      # fills the frame, chin near the bottom edge
}
FRAMINGS = FRAMINGS_BODY          # kept for --framing choices


def _framings_for(view):
    """A face or expression view is already a bust; a turnaround is a whole
    figure. They cannot share one scale table."""
    return (FRAMINGS_FACE if view.startswith(("face", "expr", "base_portrait"))
            else FRAMINGS_BODY)


def _comfy():
    from epic import COMFY, HOST, run, set_path, load_wf, ensure_local
    return COMFY, HOST, run, set_path, load_wf, ensure_local


def stage(src, name):
    COMFY = _comfy()[0]
    shutil.copy(src, os.path.join(COMFY, "input", name))
    return name


def qwen_edit(ref1, ref2, prompt, dest, seed=7, w=1664, h=928, anime=0.0):
    COMFY, HOST, run, set_path, load_wf, ensure_local = _comfy()
    wf = load_wf("14_qwen_edit_ref.json")
    set_path(wf, "8.inputs.image", ref1)
    set_path(wf, "9.inputs.image", ref2)
    set_path(wf, "10.inputs.prompt", prompt)
    set_path(wf, "13.inputs.seed", seed)
    set_path(wf, "20.inputs.width", w)
    set_path(wf, "20.inputs.height", h)
    set_path(wf, "7.inputs.strength_model", anime)
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/compose/relit")
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        raise RuntimeError("relight produced nothing")
    if os.path.exists(dest):
        os.remove(dest)
    ensure_local(outs[0], dest)
    return dest


def ask_image(src_path, question, tag="ask"):
    """One vision call: an image and a question, a short answer back. Same graph as
    the character captioner, with SaveText appended so the answer lands in a file."""
    import glob, time
    COMFY, HOST, run, set_path, load_wf, ensure_local = _comfy()
    rel = stage(src_path, "compose_%s.png" % tag)
    wf = load_wf("30_vision_caption.json")
    set_path(wf, "2.inputs.image", rel)
    set_path(wf, "3.inputs.prompt", question)
    stamp = "ask_%s_%d" % (tag, int(time.time() * 10) % 1000000)
    wf["90"] = {"class_type": "SaveText",
                "inputs": {"text": ["3", 0], "filename_prefix": stamp, "format": "txt"}}
    run(HOST, wf, quiet=True)
    hits = sorted(glob.glob(os.path.join(COMFY, "output", "**", stamp + "*"), recursive=True))
    return open(hits[-1], encoding="utf-8", errors="replace").read().strip() if hits else ""


SURFACE_ASK = ("There is a red dot drawn on this image. What is the surface directly "
               "under the red dot? Answer with exactly one word from this list: water, "
               "road, pavement, grass, sand, stone, wood, deck, floor, mud, snow, other.")
WET = ("water", "river", "sea", "lake", "canal", "pond", "ocean", "stream", "wave", "waves")


def footing(plate_p, x, y, tag="foot"):
    """What is under the point (x, y) of the plate, by asking it. -> one word."""
    from PIL import Image, ImageDraw
    im = Image.open(plate_p).convert("RGB")
    W, H = im.size
    scale = min(1.0, 1024.0 / W)
    im = im.resize((int(W * scale), int(H * scale)), Image.LANCZOS)
    r = max(6, int(im.width * 0.014))
    d = ImageDraw.Draw(im)
    cx, cy = int(x * scale), int(min(H - 1, y) * scale)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 0, 0), outline=(255, 255, 255), width=2)
    tmp = os.path.join(OUT_DIR, "_footing_%s.png" % tag)
    os.makedirs(OUT_DIR, exist_ok=True)
    im.save(tmp)
    ans = ask_image(tmp, SURFACE_ASK, tag="foot").lower()
    word = next((w for w in ("water", "road", "pavement", "grass", "sand", "stone", "wood",
                             "deck", "floor", "mud", "snow") if w in ans), ans.split()[0] if ans else "?")
    return word


def find_footing(plate, plate_p, dpath, stand, cx, say=None, max_checks=7):
    """Keep the requested spot if it is solid; otherwise walk along the ground
    line, then a step nearer, until the plate says the surface is not water.
    -> (stand, cx, surface, checks)."""
    W, H = plate.size
    tried = []
    cands = [(stand, cx)]
    for dx in (0.12, -0.12, 0.24, -0.24, 0.34, -0.34):
        c = cx + dx
        if 0.08 <= c <= 0.92:
            cands.append((stand, c))
    cands.append((max(0.05, stand - 0.1), cx))
    cands.append((min(0.9, stand + 0.15), cx))
    for i, (s, c) in enumerate(cands[:max_checks]):
        y_feet, th, _ = place_by_depth(plate, dpath, s, c)
        word = footing(plate_p, int(W * c), y_feet, tag="f%d" % i)
        tried.append((round(s, 2), round(c, 2), word))
        if say:
            say("  ? footing at stand %.2f across %.2f: %s" % (s, c, word))
        if word not in WET:
            return s, c, word, tried
    return stand, cx, tried[0][2] if tried else "?", tried


def cutout(src_path, dest, tag="cut"):
    """birefnet -> RGBA. Node 10 saves the RGBA; 11 and 12 save the matte and a
    magenta proof, and either of those looks like a good cutout in a file list
    while being a silhouette."""
    COMFY, HOST, run, set_path, load_wf, ensure_local = _comfy()
    rel = stage(src_path, "compose_%s_src.png" % tag)
    wf = load_wf("14_birefnet_matte.json")
    set_path(wf, "1.inputs.image", rel)
    set_path(wf, "10.inputs.filename_prefix", "claude-generated/compose/%s" % tag)
    _, outs = run(HOST, wf, quiet=True)
    png = next((o for o in outs if "/compose/%s" % tag in str(o)), None)
    if not png:
        raise RuntimeError("no rgba cutout among %s" % outs)
    if os.path.exists(dest):
        os.remove(dest)
    ensure_local(png, dest)
    return dest


# How much of the relight canvas the figure occupies. The rest is margin so the
# model has scene to relight her against, and so she cannot reach an edge.
RELIGHT_MARGIN = 0.66


def _edge_touching(rgba, slack=2):
    """Is the opaque region flush against any edge? Then the figure is cut off
    and its proportions are unknown - scaling it would invent the missing part."""
    bb = rgba.split()[-1].getbbox()
    if not bb:
        return True
    W, H = rgba.size
    return (bb[0] <= slack or bb[1] <= slack
            or bb[2] >= W - slack or bb[3] >= H - slack)


def _aspect_of(rgba):
    bb = rgba.split()[-1].getbbox()
    if not bb:
        return 0.0
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    return (w / h) if h else 0.0


def tint_to(cut, plate, strength=0.5):
    """A fallback when the relight is refused: push the cutout toward the plate's
    own mean colour. It is not lighting - there is no direction to it - but it
    keeps the body intact, which matters more than a key light."""
    from PIL import Image, ImageStat
    st = ImageStat.Stat(plate.convert("RGB"))
    pr, pg, pb = st.mean[:3]
    rgb = cut.convert("RGB")
    cs = ImageStat.Stat(rgb).mean[:3]
    lut = []
    for ch, (src, dst) in enumerate(zip(cs, (pr, pg, pb))):
        shift = (dst - src) * strength
        lut += [max(0, min(255, int(v + shift))) for v in range(256)]
    out = rgb.point(lut)
    out.putalpha(cut.split()[-1])
    return out


def relight_canvas(plate, cut):
    """The plate, with the whole figure on it at a size that leaves margin. This
    is what gets relit - never the final framing, which may legitimately crop
    her and would hand the re-cut a partial body."""
    from PIL import Image
    W, H = plate.size
    cut = _trim(cut)
    th = int(H * RELIGHT_MARGIN)
    tw = max(1, int(cut.width * th / cut.height))
    cut = cut.resize((tw, th), Image.LANCZOS)
    x = (W - tw) // 2
    # Seated with real room under the feet: the relight drifts downward, and
    # with a thin gap it pushes the feet off the canvas. 12% of frame height
    # below is enough that the measured drift no longer truncates them.
    y = int(H * 0.88) - th
    canvas = plate.copy()
    canvas.paste(cut, (x, y), cut)
    return canvas


def _trim(rgba):
    """Crop to what is actually opaque, so 'her height' means her, not padding."""
    bb = rgba.split()[-1].getbbox()
    return rgba.crop(bb) if bb else rgba


def ground(plate, cut, x, y, light=-0.35, pool=0.92, cast=0.42):
    """Multiply a contact pool and a directional cast under the figure.

    light  shear of the cast: negative throws it to the left, 0 straight back
    pool   opacity of the contact ellipse - the part that stops her floating
    cast   opacity of the long shadow
    """
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    W, H = plate.size
    cw, ch = cut.size
    alpha = cut.split()[-1]
    ph = max(8, int(ch * 0.075))          # contact pool thickness

    # the long cast: her silhouette squashed and sheared, anchored at her feet
    sh_h = max(4, int(ch * 0.22))
    squashed = alpha.resize((cw, sh_h), Image.LANCZOS)
    pad = int(abs(light) * sh_h * 3)
    sheared = squashed.transform(
        (cw + pad, sh_h), Image.AFFINE,
        (1, light * 3, pad if light < 0 else 0, 0, 1, 0),
        resample=Image.BILINEAR)
    cast_layer = Image.new("L", (W, H), 0)
    cast_layer.paste(sheared, (x - (pad if light < 0 else 0), y + ch - sh_h))
    cast_layer = cast_layer.filter(ImageFilter.GaussianBlur(sh_h * 0.25))
    cast_layer = cast_layer.point(lambda v: int(v * cast))

    # the contact pool: an ellipse the width of her stance, right at the feet.
    # This is the part that actually stops a figure floating; the long cast is
    # decoration by comparison.
    pool_layer = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(pool_layer)
    pw = int(cw * 1.15)   # wider than her, or it hides under the hem
    px = x + (cw - pw) // 2
    py = y + ch
    d.ellipse([px, py - ph, px + pw, py + ph], fill=255)
    pool_layer = pool_layer.filter(ImageFilter.GaussianBlur(ph * 0.7))
    pool_layer = pool_layer.point(lambda v: int(v * pool))

    # whichever is darker at each pixel, then multiply the plate down by it
    mask = ImageChops.lighter(cast_layer, pool_layer)
    dark = Image.new("RGB", (W, H), (0, 0, 0))
    return Image.composite(dark, plate, mask.point(lambda v: int(v * 0.95)))


# ─── depth: where the ground is, and therefore how big she is ───────────────────────

def depth_for_plate(plate_path, force=False):
    """A normalised greyscale depth map beside the plate, made once and cached."""
    dest = plate_path[:-4] + "_depth.png"
    if os.path.isfile(dest) and not force:
        return dest
    COMFY, HOST, run, set_path, load_wf, ensure_local = _comfy()
    rel = stage(plate_path, "compose_depth_src.png")
    wf = {
        "1": {"class_type": "LoadDA3Model",
              "inputs": {"model_name": "depth_anything_3_mono_large.safetensors",
                         "weight_dtype": "default"}},
        "2": {"class_type": "LoadImage", "inputs": {"image": rel}},
        "3": {"class_type": "DA3Inference",
              "inputs": {"da3_model": ["1", 0], "image": ["2", 0],
                         "resolution": 1024,
                         "resize_method": "upper_bound_resize", "mode": "mono"}},
        # DA3Render.output is a dynamic combo - its option carries its own
        # required inputs, namespaced. The bare key is rejected.
        "4": {"class_type": "DA3Render",
              "inputs": {"da3_geometry": ["3", 0], "output": "depth",
                         "output.normalization": "min_max",
                         "output.apply_sky_clip": True}},
        "5": {"class_type": "SaveImage",
              "inputs": {"images": ["4", 0],
                         "filename_prefix": "claude-generated/compose/depth"}},
    }
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        raise RuntimeError("depth pass produced nothing")
    if os.path.exists(dest):
        os.remove(dest)
    ensure_local(outs[0], dest)
    return dest


def _depth_rows(depth_path, plate_size):
    """Mean depth per row, normalised 0..1. Nearer is brighter in DA3's output,
    so this is inverted to read as distance."""
    from PIL import Image
    im = Image.open(depth_path).convert("L").resize(plate_size)
    W, H = im.size
    px = im.load()
    step = max(1, W // 64)
    rows = []
    for y in range(H):
        vals = [px[x, y] for x in range(0, W, step)]
        rows.append(1.0 - (sum(vals) / len(vals)) / 255.0)
    return rows


def _smooth(rows, k=9):
    out, n = [], len(rows)
    for i in range(n):
        lo, hi = max(0, i - k // 2), min(n, i + k // 2 + 1)
        out.append(sum(rows[lo:hi]) / (hi - lo))
    return out


def horizon_of(depth_path, plate_size, patience=0.03):
    """The row where the ground stops receding.

    Walk up from the bottom edge. Ground depth climbs monotonically as it
    recedes; the horizon is where that climb turns over. `patience` is how far
    depth may fall back below the running maximum before the climb is declared
    finished, as a fraction of the total climb so far - noise in a depth map is
    not a horizon.
    """
    rows = _smooth(_depth_rows(depth_path, plate_size))
    H = len(rows)
    bottom = rows[-1]
    best, best_y = bottom, H - 1
    for y in range(H - 1, int(H * 0.10), -1):
        v = rows[y]
        if v > best:
            best, best_y = v, y
        elif best - v > max(0.01, (best - bottom) * patience):
            break                      # it turned over: the ground ended here
    return max(int(H * 0.10), min(best_y, int(H * 0.92)))


def place_by_depth(plate, depth_path, stand=0.55, cx=0.42, cut=None,
                   person_m=1.7):
    """Where the feet land and how tall she is, from the horizon.

    stand  0 = right at the camera, 1 = at the horizon. It is the ONE dial: the
           height follows from it, so a figure can no longer be far away and
           gigantic at the same time.
    """
    W, H = plate.size
    y_h = horizon_of(depth_path, (W, H))
    # feet somewhere between the bottom edge and the horizon
    y_feet = int(H - (H - y_h) * max(0.02, min(stand, 0.98)))
    # apparent height is proportional to distance below the horizon. The constant
    # is set so a figure standing at the bottom edge is about 0.8 of frame - the
    # value the old "full" framing used, kept so existing shots do not jump.
    k = 0.80 * H / max(1.0, (H - y_h))
    th = int(k * (y_feet - y_h))
    th = max(int(H * 0.06), min(th, int(H * 2.2)))
    return y_feet, th, y_h

def place_cut(plate, cut, framing="full", cx=0.42, view="turn_front"):
    """Scale and position the cutout. Returns (composited, cut, x, y)."""
    from PIL import Image
    scale, feet = _framings_for(view)[framing]
    W, H = plate.size
    cut = _trim(cut)
    th = int(H * scale)
    tw = max(1, int(cut.width * th / cut.height))
    cut = cut.resize((tw, th), Image.LANCZOS)
    x = int(W * cx) - tw // 2
    y = int(H * feet) - th
    return cut, x, y


def prop_layer(prop_id, plate, dpath, stand, cx, view="hero", seed=7, work=None,
               framing="full", plate_p=None):
    """Cut a prop's view and size it for its depth. -> (cut, x, y), bottom at
    the ground line for that stand."""
    from PIL import Image
    pdir = os.path.join(PROPS, prop_id)
    src = os.path.join(pdir, view + ".png")
    if not os.path.isfile(src):
        raise SystemExit("no such prop view: %s" % src)
    meta = json.load(open(os.path.join(pdir, "asset.json"), encoding="utf-8"))
    cat = (meta.get("selections") or {}).get("category") or ""
    size_m = float(meta.get("size_m") or PROP_M.get(cat, PROP_M_DEFAULT))
    cut_p = cutout(src, os.path.join(work or OUT_DIR, "prop_%s_cut.png" % prop_id),
                   tag="p" + str(seed))
    cut = _trim(Image.open(cut_p).convert("RGBA"))
    W, H = plate.size
    if dpath is not None:
        if plate_p:
            stand, cx, _surface, _tried = find_footing(plate, plate_p, dpath, stand, cx)
        y_feet, th_person, _ = place_by_depth(plate, dpath, stand, cx)
        th = max(8, int(th_person * size_m / 1.7))
    else:
        scale, feet = _framings_for("turn_front")[framing]
        th = max(8, int(H * scale * size_m / 1.7))
        y_feet = int(H * feet)
    tw = max(1, int(cut.width * th / cut.height))
    cut = cut.resize((tw, th), Image.LANCZOS)
    return cut, int(W * cx) - tw // 2, y_feet - th


def character_layer(char_id, plate, dpath, stand, cx, view="turn_front", seed=7,
                    work=None, framing="full", plate_p=None, relight=True, footing_check=True):
    """A second (or third) character as a layer: cut, sized as a 1.7 m person at
    its depth, tinted to the plate. -> (cut, x, y)."""
    from PIL import Image
    src = os.path.join(CHARS, char_id, view + ".png")
    if not os.path.isfile(src):
        raise SystemExit("no such view: %s" % src)
    cut_p = cutout(src, os.path.join(work or OUT_DIR, "char_%s_%s_cut.png" % (char_id, view)),
                   tag="k" + str(seed))
    cut = _trim(Image.open(cut_p).convert("RGBA"))
    W, H = plate.size
    if dpath is not None:
        if plate_p and footing_check:
            stand, cx, surface, _tried = find_footing(plate, plate_p, dpath, stand, cx)
        y_feet, th, _ = place_by_depth(plate, dpath, stand, cx)
    else:
        scale, feet = _framings_for(view)[framing]
        th, y_feet = int(H * scale), int(H * feet)
    # lit by the scene like the first figure: rough paste alone, relight, re-cut
    lit = None
    if plate_p and relight:
        try:
            meta = json.load(open(os.path.join(CHARS, char_id, "asset.json"), encoding="utf-8"))
            clause = (meta.get("compiled") or {}).get("clause", "")
            style = meta.get("style", "")
            rough = relight_canvas(plate, Image.open(cut_p).convert("RGBA"))
            rough_p = os.path.join(work or OUT_DIR, "char_%s_rough.png" % char_id)
            rough.save(rough_p)
            relit_p = qwen_edit(
                stage(rough_p, "compose_rough_%s.png" % char_id),
                stage(plate_p, "compose_plate_%s.png" % char_id),
                "Keep the person full length, the whole body from head to feet inside "
                "the frame. Do not crop, do not zoom in, do not reframe. Relight only the "
                "person so they belong in this location: the same colour temperature and "
                "direction of light as the scene around them. Do not change the face, hair, "
                "pose or clothing. Do not move them. Do not change the background. %s. "
                "The whole image stays %s." % (clause, (meta.get("compiled") or {}).get("look", "") or style),
                os.path.join(work or OUT_DIR, "char_%s_relit.png" % char_id), seed=seed,
                anime=0.6 if style in ("anime", "cartoon") else 0.0,
                w=plate.size[0], h=plate.size[1])
            rc = Image.open(cutout(relit_p, os.path.join(work or OUT_DIR, "char_%s_relit_cut.png" % char_id),
                                   tag="kr" + str(seed))).convert("RGBA")
            a_src, a_rel = _aspect_of(cut), _aspect_of(rc)
            drift = abs(a_rel - a_src) / a_src if a_src else 1.0
            if drift <= 0.25 and rc.getbbox():
                lit = _trim(rc)
        except Exception:
            lit = None
    cut = lit if lit is not None else tint_to(cut, plate)
    tw = max(1, int(cut.width * th / cut.height))
    cut = cut.resize((tw, th), Image.LANCZOS)
    return cut, int(W * cx) - tw // 2, y_feet - th


def compose(char_id, place_id, plate_key=None, view="turn_front",
            framing="full", cx=0.42, light=-0.35, seed=7, tag=None,
            quiet=False, stand=None, props=None, footing_check=True):
    from PIL import Image
    cdir = os.path.join(CHARS, char_id)
    pdir = os.path.join(PLACES, place_id)
    src = os.path.join(cdir, view + ".png")
    if not os.path.isfile(src):
        raise SystemExit("no such view: %s" % src)
    plates = sorted(f for f in os.listdir(pdir)
                    if f.endswith(".png") and not f.endswith("_depth.png"))
    if plate_key:
        pf = plate_key if plate_key.endswith(".png") else plate_key + ".png"
    else:
        pf = next((p for p in plates if p.endswith("_wide.png")), plates[0])
    plate_p = os.path.join(pdir, pf)

    ch = json.load(open(os.path.join(cdir, "asset.json"), encoding="utf-8"))
    pl = json.load(open(os.path.join(pdir, "asset.json"), encoding="utf-8"))
    clause = (ch.get("compiled") or {}).get("clause", "")
    desc = (pl.get("compiled") or {}).get("description", "")

    def say(*a):
        if not quiet:
            print(*a, flush=True)

    os.makedirs(OUT_DIR, exist_ok=True)
    tag = tag or "%s__%s__%s" % (
        char_id, place_id,
        ("d%02d" % round(stand * 100)) if stand is not None else framing)
    work = os.path.join(OUT_DIR, tag)
    os.makedirs(work, exist_ok=True)

    # 1 cut and paste
    say("  1 cut")
    cut_p = cutout(src, os.path.join(work, "01_cut.png"), tag="c" + str(seed))
    plate = Image.open(plate_p).convert("RGB")
    cut = Image.open(cut_p).convert("RGBA")
    # stand= switches placement from the framing table to the depth pass: one
    # dial (how far into the scene) sets BOTH where the feet land and how big she
    # is, so the two can no longer contradict each other.
    dpath = None
    surface = None
    if stand is not None and not view.startswith(("face", "expr")):
        try:
            dpath = depth_for_plate(plate_p)
            if footing_check:
                s2, c2, surface, tried = find_footing(plate, plate_p, dpath, stand, cx, say=say)
                if (s2, c2) != (stand, cx):
                    say("  ! footing: moved from stand %.2f across %.2f to %.2f / %.2f (%s)"
                        % (stand, cx, s2, c2, surface))
                    stand, cx = s2, c2
            y_feet, th, y_h = place_by_depth(plate, dpath, stand, cx)
            cut = _trim(cut)
            tw = max(1, int(cut.width * th / cut.height))
            cut = cut.resize((tw, th), Image.LANCZOS)
            x, y = int(plate.size[0] * cx) - tw // 2, y_feet - th
            say("  0 depth: horizon y=%d, feet y=%d, height %dpx" % (y_h, y_feet, th))
        except Exception as e:
            say("  0 depth unavailable (%s) - using the framing table" % str(e)[:70])
            dpath = None
    if dpath is None:
        cut, x, y = place_cut(plate, cut, framing, cx, view)
    rough = relight_canvas(plate, Image.open(cut_p).convert("RGBA"))
    rough_p = os.path.join(work, "02_paste.png")
    rough.save(rough_p)

    # 2 relight - this wrecks the plate, which is why steps 3-5 exist
    say("  2 relight")
    rel_ref = stage(rough_p, "compose_rough.png")
    plate_ref = stage(plate_p, "compose_plate.png")
    # the drawn styles need the storybook LoRA during the relight; the
    # photographic ones must NOT have it or the relight redraws them as cartoons
    style = ch.get("style", "")
    anime_w = 0.6 if style in ("anime", "cartoon") else 0.0
    relit_p = qwen_edit(
        rel_ref, plate_ref,
        "Keep the person full length, her whole body from head to feet inside "
        "the frame. Do not crop her, do not zoom in, do not reframe. "
        "Relight only the person in the first image so she belongs in this "
        "location: the same colour temperature and direction of light as the "
        "scene around her, light falling on her from the scene's own sources. "
        "Do not change her face, her hair, her pose or her clothing. Do not "
        "move her. Do not change the background. %s. The location is %s. "
        "The whole image stays %s."
        % (clause, desc, (ch.get("compiled") or {}).get("look", "") or style),
        os.path.join(work, "03_relit.png"), seed=seed, anime=anime_w,
        w=plate.size[0], h=plate.size[1])

    # 3 take only her back out
    say("  3 re-cut")
    relit_cut_p = cutout(relit_p, os.path.join(work, "04_relit_cut.png"),
                         tag="r" + str(seed))
    rc = Image.open(relit_cut_p).convert("RGBA")
    src_cut = Image.open(cut_p).convert("RGBA")
    a_src, a_rel = _aspect_of(src_cut), _aspect_of(rc)
    drift = abs(a_rel - a_src) / a_src if a_src else 1.0
    # Proportion decides. A full-body cutout ends at its own feet, so a bbox
    # reaching the bottom is ambiguous; a silhouette that changed shape is not.
    if drift > 0.25:
        say("  ! relight refused: shape %.2f -> %.2f (%.0f%% drift)%s. Using the "
            "source cutout tinted to the plate instead - the light will be flat."
            % (a_src, a_rel, drift * 100,
               ", and it touches an edge" if _edge_touching(rc) else ""))
        rc = tint_to(src_cut, plate)
    elif _edge_touching(rc):
        say("  . relit cutout reaches an edge (shape held at %.0f%% drift) - "
            "accepted, but check the feet" % (drift * 100))
    if dpath is not None:
        y_feet, th, _ = place_by_depth(plate, dpath, stand, cx)
        rc = _trim(rc)
        tw = max(1, int(rc.width * th / rc.height))
        rc = rc.resize((tw, th), Image.LANCZOS)
        rx, ry = int(plate.size[0] * cx) - tw // 2, y_feet - th
    else:
        rc, rx, ry = place_cut(plate, rc, framing, cx, view)

    # 4 + 5 ground everything, far to near, onto the plate that was never touched.
    # Props are layers like her: same depth pass, their own world size.
    say("  4 shadow + paste")
    c_stand = stand if stand is not None else 0.5
    layers = [(c_stand, rc, rx, ry)]
    for p in (props or []):
        p_stand = float(p.get("stand", c_stand))
        if p.get("character"):
            pc, px, py = character_layer(p["character"], plate, dpath, p_stand,
                                         float(p.get("cx", 0.6)),
                                         view=p.get("view", "turn_front"), seed=seed,
                                         work=work, framing=framing, plate_p=plate_p,
                                         footing_check=footing_check)
            say("  + character %s (%s) at stand %.2f, %dpx tall"
                % (p["character"], p.get("view", "turn_front"), p_stand, pc.height))
        else:
            pc, px, py = prop_layer(p["id"], plate, dpath, p_stand,
                                    float(p.get("cx", 0.6)), view=p.get("view", "hero"),
                                    seed=seed, work=work, framing=framing,
                                    plate_p=plate_p if footing_check else None)
            say("  + prop %s at stand %.2f, %dpx tall" % (p["id"], p_stand, pc.height))
        layers.append((p_stand, pc, px, py))
    final = plate.copy()
    for _, lc, lx, ly in sorted(layers, key=lambda L: -L[0]):   # far first
        final = ground(final, lc, lx, ly, light=light)
        final.paste(lc, (lx, ly), lc)
    out_p = os.path.join(work, "final.png")
    final.save(out_p)
    json.dump({"character": char_id, "view": view, "place": place_id,
               "plate": pf, "framing": framing, "cx": cx, "light": light,
               "seed": seed, "stand": stand, "props": props or [],
               "surface": surface},
              open(os.path.join(work, "recipe.json"), "w"), indent=1)
    return out_p, plate_p


def fidelity(plate_p, final_p):
    """How much of the plate survived. The number this whole shape exists for."""
    from PIL import Image
    a = Image.open(plate_p).convert("RGB")
    b = Image.open(final_p).convert("RGB").resize(a.size)
    W, H = a.size
    out = []
    for box in ((0, 0, int(W * 0.26), H), (int(W * 0.58), 0, W, H)):
        ca, cb = a.crop(box).resize((160, 90)), b.crop(box).resize((160, 90))
        pa, pb = ca.tobytes(), cb.tobytes()
        out.append(sum(abs(p - q) for p, q in zip(pa, pb)) / (255.0 * len(pa)))
    return out


# ─── pinned shots: choose both ends, let H3 interpolate ─────────────────────────────
#
# Prose cannot direct action on LTX. Measured on one crouch, with the enhancer
# off, the action first and in capitals, and an explicit "locked off on a tripod,
# no dolly, no zoom, no pan": she did not crouch and the camera pushed in anyway.
# That is an engine prior, not a wording problem.
#
# H3's fl2va checkpoint takes a first frame AND a last frame, so the action stops
# being a request and becomes the interpolation between two states we choose. The
# same run, pinned: she lowers across all 192 frames and the framing holds.
#
# The end state costs one still. It is made by editing the START frame - same
# person, same place, same camera - so a pinned shot needs no new asset, and the
# edit is returned for looking at before any video is rendered, because pinning
# to a bad end frame tests nothing.

H3_MAX_FRAMES = 209          # 8.7s; the kernel OOMs past it
H3_FPS = 24


# How different the two pinned frames must be, per second of shot, measured in
# the subject's own region. Below this the model has nothing to interpolate and
# invents. See the module note above for the three measurements behind it.
MIN_PIN_RATE = 0.009
# When the end frame is the figure alone on the pristine plate, the background
# contributes nothing to the distance and the number is smaller for the same
# motion. One verified interpolation (the crouch) measures 0.0052/s this way;
# the floor sits at half of it. First calibration - one data point.
MIN_PIN_RATE_PLATE = 0.002


def _subject_distance(a_path, b_path):
    """Mean absolute difference across the middle of the frame, where the figure
    is. The whole frame is dominated by a background that does not move and
    understates the change."""
    from PIL import Image
    a, b = Image.open(a_path).convert("L"), Image.open(b_path).convert("L")
    W, H = a.size
    box = (int(W * 0.15), 0, int(W * 0.60), H)
    a = a.crop(box).resize((160, 110))
    b = b.crop(box).resize((160, 110))
    pa, pb = a.tobytes(), b.tobytes()
    return sum(abs(x - y) for x, y in zip(pa, pb)) / (255.0 * len(pa))


def subject_change(start_path, end_path, roi):
    """Mean absolute change inside `roi` (x0, y0, x1, y1) - the subject's own
    region - so the number does not shrink with distance from the camera."""
    from PIL import Image
    a = Image.open(start_path).convert("L").crop(roi)
    b = Image.open(end_path).convert("L").crop(roi)
    if a.size != b.size or a.size[0] < 2 or a.size[1] < 2:
        return 0.0
    pa, pb = a.tobytes(), b.tobytes()
    return sum(abs(x - y) for x, y in zip(pa, pb)) / (255.0 * len(pa))


def pin_floor(on_plate=False):
    return MIN_PIN_RATE_PLATE if on_plate else MIN_PIN_RATE


def pin_feasible(start_path, end_path, seconds, on_plate=False):
    """-> (ok, rate, the longest duration this pair can actually carry).
    `on_plate`: the end frame shares the start frame's background exactly, so
    the smaller floor applies."""
    d = _subject_distance(start_path, end_path)
    rate = d / max(0.1, seconds)
    floor = pin_floor(on_plate)
    longest = d / floor
    return rate >= floor, rate, longest


def h3_length(seconds):
    """H3 wants 17n+5 frames. Returns the largest valid length within `seconds`."""
    want = min(int(seconds * H3_FPS), H3_MAX_FRAMES)
    n = max(0, (want - 5) // 17)
    return int(17 * n + 5)


def plate_for(place_id, plate_key=None):
    """The plate compose() would pick for this place - the same rule, so a
    caller that only knows the place can find the pristine background."""
    pdir = os.path.join(PLACES, place_id)
    plates = sorted(f for f in os.listdir(pdir)
                    if f.endswith(".png") and not f.endswith("_depth.png"))
    if plate_key:
        pf = plate_key if plate_key.endswith(".png") else plate_key + ".png"
    else:
        pf = next((p for p in plates if p.endswith("_wide.png")), plates[0])
    return os.path.join(pdir, pf)


def _head_width(alpha, box):
    """Width of the figure a little below its top - the head, whatever the pose.
    Median over the rows 3-9% down the silhouette."""
    x0, y0, x1, y1 = box
    h = max(1, y1 - y0)
    ws = []
    for y in range(y0 + int(h * 0.03), min(y1, y0 + int(h * 0.09) + 1)):
        row = alpha.crop((x0, y, x1, y + 1)).tobytes()
        xs = [i for i, v in enumerate(row) if v > 128]
        if xs:
            ws.append(xs[-1] - xs[0] + 1)
    return sorted(ws)[len(ws) // 2] if ws else 0


# How much a moving motion may change the figure's scale (head width, end over
# start) inside one shot. A walk is a modest change of depth; beyond this the
# model has to invent the ground she crossed.
MOVE_SCALE = (0.6, 1.6)

MOVING_WORDS = ("walk", "closer", "further", "farther", "larger in the frame",
                "smaller in the frame", "run", "steps toward", "steps away",
                "approach", "retreat", "leaves the frame", "enters")


def end_state(start_path, change, dest, seed=11, keep=None, plate_path=None,
              light=-0.35, src=None, hold_feet=None):
    """The start frame, edited so ONE thing about the subject is different.

    `change` says what moved - "she has lowered into a deep crouch, knees bent".
    Everything not named is held, because an end frame that also moved the
    camera or relit the scene turns an interpolation into a dissolve.

    qwen-edit regenerates the whole frame, background included, however firmly
    it is told not to. With `plate_path` - the pristine plate the start frame
    was composed on - the figure is cut out of the regeneration and put back on
    that plate with its shadow, so both ends of the pin share one background.
    """
    from PIL import Image
    plate = Image.open(start_path)
    rel = stage(start_path, "pin_src.png")
    hold = keep or ("her face, her hair, her clothing and the whole background")
    raw_dest = dest if not plate_path else dest[:-4] + "_raw.png"
    raw = qwen_edit(
        rel, rel,
        "The same subject in the same place, but %s. Keep %s exactly as they "
        "are. Same camera position, same framing, same light. Only the pose "
        "changes." % (change, hold),
        raw_dest, seed=seed, w=plate.size[0], h=plate.size[1], anime=0.0)
    if not plate_path:
        return raw
    # the figure only, back onto the background that never moved
    cut_p = cutout(raw, dest[:-4] + "_cut.png", tag="e" + str(seed))
    cut = Image.open(cut_p).convert("RGBA")
    bg = Image.open(plate_path).convert("RGB")
    if bg.size != cut.size:
        bg = bg.resize(cut.size, Image.LANCZOS)
    box = cut.getbbox()
    if not box:
        return raw          # nothing cut out - keep the regeneration, honestly
    fig = cut.crop(box)
    x, y = box[0], box[1]
    geom = {"hold_feet": None, "scale": 1.0}
    if hold_feet is None:
        hold_feet = not any(k in change.lower() for k in MOVING_WORDS)
    geom["hold_feet"] = bool(hold_feet)
    if src and hold_feet:
        # in-place motion: same feet, same centre, same head size as the start
        try:
            from PIL import ImageChops
            W, H = bg.size
            stand = float(src.get("stand", 0.35))
            cx = float(src.get("cx", 0.42))
            dpath = depth_for_plate(plate_path)
            y_feet, th, _ = place_by_depth(bg, dpath, stand, cx)
            start_im = Image.open(start_path).convert("RGB").resize(bg.size)
            diff = ImageChops.difference(start_im, bg).convert("L").point(
                lambda v: 255 if v > 14 else 0)
            cxp = int(W * cx)
            roi = (max(0, cxp - th), max(0, y_feet - int(th * 1.15)),
                   min(W, cxp + th), min(H, y_feet))
            sbox = diff.crop(roi).getbbox()
            if sbox:
                sbox = (sbox[0] + roi[0], sbox[1] + roi[1],
                        sbox[2] + roi[0], sbox[3] + roi[1])
                hw_s = _head_width(diff, sbox)
                hw_e = _head_width(fig.split()[-1], (0, 0, fig.width, fig.height))
                if hw_s > 4 and hw_e > 4:
                    s = max(0.6, min(1.5, hw_s / float(hw_e)))
                    if abs(s - 1.0) > 0.03:
                        fig = fig.resize((max(1, int(fig.width * s)),
                                          max(1, int(fig.height * s))), Image.LANCZOS)
                    geom["scale"] = round(s, 3)
                geom.update(head_start=hw_s, head_end=hw_e)
            x = cxp - fig.width // 2
            y = y_feet - fig.height
            geom.update(y_feet=y_feet, cx=cxp, raw_box=list(box))
        except Exception as e:
            geom["error"] = str(e)[:120]
    elif src and not hold_feet:
        # a moving motion: clamp the change of scale, then stand the figure at
        # the depth the plate gives a figure of that height
        try:
            from PIL import ImageChops
            W, H = bg.size
            stand = float(src.get("stand", 0.35))
            cx = float(src.get("cx", 0.42))
            dpath = depth_for_plate(plate_path)
            y_feet0, th0, y_h = place_by_depth(bg, dpath, stand, cx)
            start_im = Image.open(start_path).convert("RGB").resize(bg.size)
            diff = ImageChops.difference(start_im, bg).convert("L").point(
                lambda v: 255 if v > 14 else 0)
            cxp = int(W * cx)
            roi = (max(0, cxp - th0), max(0, y_feet0 - int(th0 * 1.15)),
                   min(W, cxp + th0), min(H, y_feet0))
            sbox = diff.crop(roi).getbbox()
            if sbox:
                sbox = (sbox[0] + roi[0], sbox[1] + roi[1],
                        sbox[2] + roi[0], sbox[3] + roi[1])
                hw_s = _head_width(diff, sbox)
                hw_e = _head_width(fig.split()[-1], (0, 0, fig.width, fig.height))
                if hw_s > 4 and hw_e > 4:
                    want = max(MOVE_SCALE[0], min(MOVE_SCALE[1], hw_e / float(hw_s)))
                    s = (want * hw_s) / float(hw_e)       # resize so head = want x start
                    if abs(s - 1.0) > 0.03:
                        fig = fig.resize((max(1, int(fig.width * s)),
                                          max(1, int(fig.height * s))), Image.LANCZOS)
                    geom.update(scale=round(s, 3), rel_scale=round(want, 3),
                                head_start=hw_s, head_end=hw_e)
            # where does a figure this tall stand? invert place_by_depth:
            # th = k * (y_feet - y_h), k = 0.8 H / (H - y_h)
            k = 0.80 * H / max(1.0, (H - y_h))
            y_feet = int(y_h + fig.height / k)
            y_feet = max(y_h + 4, min(H + int(fig.height * 0.35), y_feet))
            x = cxp - fig.width // 2
            y = y_feet - fig.height
            geom.update(y_feet=y_feet, y_feet_start=y_feet0, cx=cxp, raw_box=list(box))
        except Exception as e:
            geom["error"] = str(e)[:120]
    final = ground(bg, fig, x, y, light=light)
    final.paste(fig, (x, y), fig)
    final.save(dest)
    try:
        json.dump(geom, open(dest[:-4] + "_geom.json", "w"), indent=1)
    except Exception:
        pass
    return dest


def pin_shot(start_path, end_path, prompt, dest, seconds=8, seed=42,
             force=False):
    """H3 fl2va between two chosen frames.

    The node hardcodes 768x1344 and renders portrait in silence unless width and
    height are passed - a bug this project has already paid for once.
    """
    from PIL import Image
    ok, rate, longest = pin_feasible(start_path, end_path, seconds)
    if not ok and not force:
        raise RuntimeError(
            "the two pinned frames are too alike for %.1fs: %.4f change per "
            "second, and below %.3f the model invents rather than interpolates "
            "(it has produced a second copy of the subject and fire on water). "
            "Either pick a bigger change, or run this pair at %.1fs or less."
            % (seconds, rate, MIN_PIN_RATE, longest))
    if not ok:
        print("  ! forced: %.4f/s is under %.3f - expect invention"
              % (rate, MIN_PIN_RATE), flush=True)
    COMFY, HOST, run, set_path, load_wf, ensure_local = _comfy()
    w, h = Image.open(start_path).size
    a = stage(start_path, "pin_a.png")
    b = stage(end_path, "pin_b.png")
    wf = load_wf("62_minimax_h3_fl.json")
    set_path(wf, "8.inputs.image", a)
    set_path(wf, "9.inputs.image", b)
    set_path(wf, "20.inputs.prompt", prompt)
    set_path(wf, "20.inputs.length", h3_length(seconds))
    set_path(wf, "20.inputs.width", w)
    set_path(wf, "20.inputs.height", h)
    set_path(wf, "33.inputs.noise_seed", seed)
    set_path(wf, "51.inputs.filename_prefix", "claude-generated/compose/pinned")
    _, outs = run(HOST, wf, quiet=True)
    mp4 = next((o for o in outs if str(o).lower().endswith((".mp4", ".webm"))),
               None)
    if not mp4:
        raise RuntimeError("the pinned render returned no video: %s" % outs)
    if os.path.exists(dest):
        os.remove(dest)
    ensure_local(mp4, dest)
    return dest


def pinned(char_id, place_id, change, prompt=None, plate_key=None,
           view="turn_front", stand=0.28, cx=0.42, seconds=8, seed=42,
           tag=None):
    """The whole path: compose a start, edit an end, interpolate between them."""
    start, plate_p = compose(char_id, place_id, plate_key, view, "full", cx,
                             seed=seed, stand=stand,
                             tag=(tag or "%s__%s__pin" % (char_id, place_id)))
    work = os.path.dirname(start)
    end = end_state(start, change, os.path.join(work, "05_end.png"), seed=seed)
    ok, rate, longest = pin_feasible(start, end, seconds)
    print("  end state -> %s" % end, flush=True)
    print("  pin rate  -> %.4f/s (floor %.3f); this pair carries up to %.1fs"
          % (rate, MIN_PIN_RATE, longest), flush=True)
    vid = pin_shot(start, end,
                   prompt or ("The subject %s. The camera does not move." % change),
                   os.path.join(work, "pinned.mp4"), seconds=seconds, seed=seed)
    return start, end, vid


MATRIX = [
    ("bai-liwen", "night-market", "night_wide", "turn_front", "full", 0.42),
    ("bai-liwen", "night-market", "night_wide", "face_three_quarter", "close", 0.38),
    ("bai-liwen", "back-alley", "night_wide", "turn_front_three_quarter", "full", 0.55),
    ("terra", "hilltop-temple", "dawn_wide", "turn_front", "full", 0.45),
    ("terra", "old-quarter-rooftops", "night_wide", "pres_hero", "medium", 0.40),
    ("terra", "night-market", "dawn_wide", "turn_side", "full", 0.60),
]


def main():
    ap = argparse.ArgumentParser(
        description="Composite a foundry character into a foundry place.")
    ap.add_argument("-c", "--character")
    ap.add_argument("-p", "--place")
    ap.add_argument("--plate")
    ap.add_argument("--view", default="turn_front")
    ap.add_argument("--framing", default="full", choices=sorted(FRAMINGS))
    ap.add_argument("--cx", type=float, default=0.42)
    ap.add_argument("--light", type=float, default=-0.35)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--stand", type=float, default=None,
                    help="0 = at the camera, 1 = at the horizon. Uses the depth "
                         "pass and derives the height from it, instead of the "
                         "framing table.")
    ap.add_argument("--pin", metavar="CHANGE",
                    help="make a PINNED shot: compose a start frame, edit it so "
                         "CHANGE has happened, and interpolate between the two "
                         "on H3. e.g. --pin \"she has lowered into a deep "
                         "crouch, knees bent\"")
    ap.add_argument("--seconds", type=float, default=8.0)
    ap.add_argument("--matrix", action="store_true")
    a = ap.parse_args()

    jobs = ([(c, p, pl, v, f, cx) for c, p, pl, v, f, cx in MATRIX] if a.matrix
            else [(a.character, a.place, a.plate, a.view, a.framing, a.cx)])
    if not a.matrix and not (a.character and a.place):
        ap.error("need --character and --place, or --matrix")

    for c, p, pl, v, f, cx in jobs:
        if a.pin:
            print("%s in %s - pinned: %s" % (c, p, a.pin), flush=True)
            s, e, vid = pinned(c, p, a.pin, plate_key=pl, view=v,
                               stand=(a.stand if a.stand is not None else 0.28),
                               cx=cx, seconds=a.seconds, seed=a.seed)
            print("  -> %s" % vid, flush=True)
            continue
        print("%s in %s (%s, %s)" % (c, p, f, v), flush=True)
        try:
            out, plate = compose(c, p, pl, v, f, cx, a.light, a.seed,
                                 stand=a.stand)
            l, r = fidelity(plate, out)
            print("  -> %s   plate fidelity L=%.4f R=%.4f" % (out, l, r),
                  flush=True)
        except Exception as e:
            print("  FAILED: %s" % e, flush=True)


if __name__ == "__main__":
    main()
