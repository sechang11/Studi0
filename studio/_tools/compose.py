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


def compose(char_id, place_id, plate_key=None, view="turn_front",
            framing="full", cx=0.42, light=-0.35, seed=7, tag=None,
            quiet=False, stand=None):
    from PIL import Image
    cdir = os.path.join(CHARS, char_id)
    pdir = os.path.join(PLACES, place_id)
    src = os.path.join(cdir, view + ".png")
    if not os.path.isfile(src):
        raise SystemExit("no such view: %s" % src)
    plates = sorted(f for f in os.listdir(pdir) if f.endswith(".png"))
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
    if stand is not None and not view.startswith(("face", "expr")):
        try:
            dpath = depth_for_plate(plate_p)
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
    rough = plate.copy()
    rough.paste(cut, (x, y), cut)
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
        "Relight only the person in the first image so she belongs in this "
        "location: the same colour temperature and direction of light as the "
        "scene around her, light falling on her from the scene's own sources. "
        "Do not change her face, her hair, her pose or her clothing. Do not "
        "move her. Do not change the background. %s. The location is %s. "
        "The whole image stays %s."
        % (clause, desc, (ch.get("compiled") or {}).get("look", "") or style),
        os.path.join(work, "03_relit.png"), seed=seed, anime=anime_w)

    # 3 take only her back out
    say("  3 re-cut")
    relit_cut_p = cutout(relit_p, os.path.join(work, "04_relit_cut.png"),
                         tag="r" + str(seed))
    rc = Image.open(relit_cut_p).convert("RGBA")
    if dpath is not None:
        y_feet, th, _ = place_by_depth(plate, dpath, stand, cx)
        rc = _trim(rc)
        tw = max(1, int(rc.width * th / rc.height))
        rc = rc.resize((tw, th), Image.LANCZOS)
        rx, ry = int(plate.size[0] * cx) - tw // 2, y_feet - th
    else:
        rc, rx, ry = place_cut(plate, rc, framing, cx, view)

    # 4 + 5 ground her, then paste onto the plate that was never touched
    say("  4 shadow + paste")
    final = ground(plate, rc, rx, ry, light=light)
    final.paste(rc, (rx, ry), rc)
    out_p = os.path.join(work, "final.png")
    final.save(out_p)

    json.dump({"character": char_id, "view": view, "place": place_id,
               "plate": pf, "framing": framing, "cx": cx, "light": light,
               "seed": seed, "stand": stand}, open(os.path.join(work, "recipe.json"), "w"),
              indent=1)
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
    ap.add_argument("--matrix", action="store_true")
    a = ap.parse_args()

    jobs = ([(c, p, pl, v, f, cx) for c, p, pl, v, f, cx in MATRIX] if a.matrix
            else [(a.character, a.place, a.plate, a.view, a.framing, a.cx)])
    if not a.matrix and not (a.character and a.place):
        ap.error("need --character and --place, or --matrix")

    for c, p, pl, v, f, cx in jobs:
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
