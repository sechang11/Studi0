#!/usr/bin/env python3
"""Make a SCULPT-READY seed image - one a mould could release from.

    --stage sweep     the broad cross: hair treatment x hand treatment, base res
    --stage final     the survivors, at 1664x2432
    --stage matte     BiRefNet to RGBA, then measure the alpha
    --stage publish   assemble source/ and write RECOMMENDATION_V2.json
    --stage report    print the measurements back

THIS TOOL HAS ARGPARSE AND DOES NOTHING AT IMPORT TIME. Seventeen of the sixty tools in
this directory run their whole job on any argument including --help; this one does not.

WHY THERE IS A V2. The v1 mesh (TERRA_150mm.stl) has two faults the user named: the hair
reads as Medusa, and the right hand has wrong fingers. Both are SOURCE faults, visible in
studio/samples/terra_3d/source/G_out_dark_s1_rgba.png before any 3D ran:

  THE HAIR IS DRAWN AS BIG SEPARATED S-CURVE LOCKS with background visible between them.
  Hunyuan3D turned each lock into a tube and stacked tubes read as snakes. The mesh is a
  correct reconstruction of a drawing whose hair was never sculptural. A figurine sculpts
  hair as ONE CLOSED MASS with carved grooves, because free-floating strands cannot be
  moulded or printed.

  THE RIGHT HAND IS ALREADY WRONG IN THE SEED. Fingers splayed, not resolving in 2D. The
  mesh inherited a bad hand rather than inventing one.

*** THE ROOT CAUSE V1 MISSED, AND IT IS ONE LINE ***
TERRA.json's tags field is:
    "terra branford (final fantasy vi), 1girl, solo, LONG WAVY GREEN HAIR, VERY LONG HAIR,
     green eyes, red hair ribbon"
and v1's positive() pasted that string into EVERY prompt verbatim. v1's F_tamehair cell
appended "ponytail, hair behind back" AFTER it and concluded from the failure that "the
volume is trained into the LoRA". That conclusion does not follow: the prompt was
arguing with itself. Two explicit strand tags were still in the sentence.

So v2 does TAG SURGERY rather than tag addition - IDENTITY holds the tags that make her
her, the hair tags are REMOVED, and each hair treatment substitutes its own nouns. The
model renders nouns; give it exactly one hair noun and no competing one.

The second lever v1 could not use: v1's NEG contained "arms behind back, hand on hip,
holding". Those are three of the five hand treatments this tool needs to test, so the
negative is built per-cell - each hand treatment negates the OTHER hand vocabularies and
never its own.

KEPT FROM V1 BECAUSE IT WAS MEASURED, not because it was inherited:
  outstretched arms   the only pose word of five that opened her arms with real air on
                      both sides. "spread arms" - the tag that MEANS a T-pose - returned
                      arms near the hips at both LoRA strengths.
  light L3            the only arm with no cast-shadow pool at her feet that still keeps
                      form shading. Note the lever: "no cast shadow" in the POSITIVE
                      prompt is a negation and did not work; the word had to move to the
                      NEGATIVE prompt.
  dark plate          on the grey plate BiRefNet ATE A BARE FOREARM - pale skin on pale
                      grey is not enough contrast and the hand came out a floating island.
  lora 0.50           the card's measured strength. 0.25 drifted off the anime engine.
  wear rung 0, 1536+ long edge, danbooru name present, whole figure with margin.

ADDED TO THE NEGATIVE IN V2, and this is a third source fault nobody named: the v1 seed
renders the gold bodice STAINED AND TORN at wear rung 0, because rung 0's words "red and
blue pattern" and "clean and unmarked" are descriptions and the checkpoint drew the
pattern as blotches. Damage nouns are cheap to negate and a figurine wants the canonical
outfit.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, HOST          # noqa: E402

OUT = os.path.join(ROOT, "studio", "samples", "terra_3d_v2", "source")
WORK = os.path.join(ROOT, "studio", "samples", "terra_3d_v2", "_work")
COMFY_IN = os.path.expanduser("~/ComfyUI/input")

SEEDS = [4242, 1337]
Q = "masterpiece, best quality, very aesthetic, absurdres"

# IDENTITY WITHOUT THE HAIR. Every tag here earns its place: the danbooru name is
# load-bearing (measured - without it the LoRA alone returns a generic green-haired
# woman), and "green hair" has to survive because it is the character. What is deleted is
# "long wavy green hair" and "very long hair" - the two tags that draw strands.
IDENTITY = "terra branford (final fantasy vi), 1girl, solo, green eyes"
BASE = "female focus, young woman, slender"
WEAR0 = ("red cape, sleeveless gold dress with red and blue pattern, wide red sash, "
         "red boots")

FRAME = ("full body, standing, whole figure in frame, full length shot, symmetrical, "
         "centered")
LIGHT = "soft even lighting, diffuse light, ambient light"
PLATE = "plain flat dark blue background, simple background"

# The base negative, with EVERY pose and hand word removed - those are now per-cell, since
# three of them are things this tool is trying to render.
NEG = (
    "cropped, out of frame, close-up, upper body, portrait, multiple views, multiple "
    "girls, 2girls, 1boy, male focus, sitting, lying, kneeling, from above, from below, "
    "dutch angle, leaning, dynamic pose, orb, weapon, "
    "dramatic lighting, harsh shadow, cast shadow, backlighting, rim light, spotlight, "
    "chiaroscuro, shadow, drop shadow, floor, ground, reflection, "
    "gradient background, scenery, indoors, outdoors, cluttered background, "
    "text, watermark, signature, artist name, border, letterboxed, "
    "motion blur, blurry, depth of field, lowres, worst quality, bad anatomy, bad hands, "
    "extra arms, extra legs, missing limb, fused fingers, extra fingers, "
    # THE THIRD SOURCE FAULT: rung 0 rendered dirty in v1.
    "torn clothes, damaged clothes, stained, dirty, tattered, ragged, blood, patches"
)

# THE ANTI-STRAND NEGATIVE. This is the half of the hair fix that the positive prompt
# cannot do, because "hair as one mass" is a description and descriptions do not render.
# What renders is the removal of the nouns that draw separation.
NO_STRANDS = ("floating hair, very long hair, wavy hair, curly hair, messy hair, "
              "hair spread out, windswept, drill hair, hair flowing, big hair, "
              "hair over shoulder, sidelocks")

# HAIR TREATMENTS. Every one of these is a danbooru tag, i.e. a NOUN, because that is what
# this model renders. H0 is the v1 hair reproduced exactly so the sweep has its own
# control rather than a remembered one.
#   tag -> (positive hair nouns, extra negative)
HAIRS = {
    "H0_control": ("long wavy green hair, very long hair, red hair ribbon", ""),
    "H1_lowpony": ("green hair, low ponytail, hair tied back, red hair ribbon",
                   NO_STRANDS),
    "H2_braid":   ("green hair, single braid, braided ponytail, hair tied back, "
                   "red hair ribbon", NO_STRANDS),
    "H3_bun":     ("green hair, hair bun, single hair bun, hair up, hair tied back, "
                   "red hair ribbon", NO_STRANDS + ", ponytail, braid"),
    "H4_halfup":  ("green hair, half updo, hair tied back, straight hair, "
                   "red hair ribbon", NO_STRANDS),
    "H5_sleek":   ("green hair, low ponytail, straight hair, hair tied back, "
                   "hair behind back, red hair ribbon", NO_STRANDS),
    "H6_crown":   ("green hair, crown braid, braided bun, hair up, short hair, "
                   "red hair ribbon", NO_STRANDS + ", ponytail, long hair"),
}

# HAND TREATMENTS. The constraint that outranks all of them: ARMS CLEAR OF THE TORSO.
# A feed-forward reconstructor has no step that separates a fused arm - the geometry
# simply never had two surfaces there. So the two treatments that press the arm against
# the body (hips, behind back) are in the sweep to be MEASURED and expected to lose, not
# because they are good ideas.
#   tag -> (positive, extra negative)
_ALL_HANDS = "open hands, spread fingers, hand on hip, arms behind back, holding, clenched hands"


def _other_hands(*mine):
    return ", ".join(w for w in _ALL_HANDS.split(", ") if w not in mine)


HANDS = {
    "D0_open":  ("outstretched arms, legs apart, standing, open hands, empty hands",
                 _other_hands("open hands", "spread fingers")),
    "D1_fist":  ("outstretched arms, legs apart, standing, clenched hands, fist",
                 _other_hands("clenched hands")),
    "D2_hips":  ("hands on hips, legs apart, standing",
                 _other_hands("hand on hip")),
    "D3_back":  ("arms behind back, legs apart, standing",
                 _other_hands("arms behind back")),

    # --- ROUND TWO. MEASURED IN ROUND ONE: adding ANY hand noun to the positive prompt
    # drops the arms back to her sides. D0 and D1 both did it, and v1's winning G render
    # had "outstretched arms" with NO hand noun beside it - which is why v1 got an open
    # A-pose and also why v1 got splayed fingers it never asked for. The arm tag and the
    # hand tag compete for the same region of the sentence.
    #
    # So round two stops asking the positive prompt for two things at once. The ARM stays
    # in the positive, alone or weighted; the HAND CLOSURE moves entirely to the negative,
    # where "open hands, spread fingers" is a thing-to-remove rather than a competing
    # noun. Same lever that fixed the cast shadow in v1: state the unwanted thing in the
    # negative instead of the wanted thing in the positive.
    "D4_outfist": ("(outstretched arms:1.4), arms to the sides, legs apart, standing, "
                   "clenched hands", _other_hands("clenched hands")),
    "D5_outneg":  ("outstretched arms, legs apart, standing",
                   "open hands, spread fingers, holding, hand on hip, arms behind back"),
    "D6_outhard": ("(outstretched arms:1.5), arms to the sides, legs apart, standing",
                   "open hands, spread fingers, holding, hand on hip, arms behind back"),

    # --- ROUND THREE. D4 won the arm at weight 1.4 but left the fingers relaxed and
    # slightly open rather than closed. D6 proved 1.5 is past the ceiling - it snapped to
    # a full T-pose AND shredded both hands into feathered extra fingers, which is the
    # same failure mode as the v1 seed only worse. So the arm weight stays at 1.4 and the
    # fist gets its own weight instead.
    "D7_fistw": ("(outstretched arms:1.4), arms to the sides, legs apart, standing, "
                 "(clenched hands:1.3), fist", _other_hands("clenched hands")),
}

# The sweep is the full cross of the two, so hair and hands can be attributed separately
# rather than confounded. 7 x 4 = 28 cells at base resolution.
SWEEP = [(h, d) for h in HAIRS for d in HANDS]


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def card():
    with open(os.path.join(ROOT, "studio", "characters", "TERRA.json"),
              encoding="utf-8") as f:
        return json.load(f)


# THE THIRD SCULPT HAZARD, and v1 named it without acting on it: "the skirt fringe is
# drawn as many separate hanging strands, and at figurine scale each is far below any
# printable minimum feature size." The same sentence describes the long thin sash panels
# that hang to the shin - a sheet one voxel thick is a hole in a printed figurine.
# These are nouns, so they can be negated like any other noun.
NO_TRIM = "fringe, tassel, tassels, frills, long scarf, cape, shawl, drapery, ribbon trim"


def positive(hair, hand):
    bits = [IDENTITY, HAIRS[hair][0], BASE, WEAR0, HANDS[hand][0], FRAME, LIGHT, PLATE, Q]
    return ", ".join(b for b in bits if b)


def negative(hair, hand, extra_neg=""):
    extra = ", ".join(x for x in (HAIRS[hair][1], HANDS[hand][1], extra_neg) if x)
    return NEG + (", " + extra if extra else "")


def graph(c, hair, hand, seed, lora_st=0.50, w=832, h=1216, hires=None, extra_neg=""):
    """The production anime path with the IPAdapter branch REMOVED rather than zeroed.

    Zeroing the IPAdapter weight still loads the model and still requires sheet_rask.png
    in the input folder. Deleting the branch and rewiring the sampler straight to the
    model is cheaper and has no residual.
    """
    wf = load_wf("22_anime_kf_ipadapter.json")
    for n in ("2", "3", "4"):
        wf.pop(n, None)
    set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
    src = ["1", 0]

    lora = c.get("lora")
    if lora and lora_st > 0:
        wf["90"] = {"class_type": "LoraLoaderModelOnly",
                    "inputs": {"model": ["1", 0], "lora_name": lora,
                               "strength_model": lora_st}}
        src = ["90", 0]
    set_path(wf, "8.inputs.model", src)

    set_path(wf, "5.inputs.text", positive(hair, hand))
    set_path(wf, "6.inputs.text", negative(hair, hand, extra_neg))
    set_path(wf, "8.inputs.seed", seed)
    set_path(wf, "8.inputs.steps", 30)
    set_path(wf, "8.inputs.cfg", 5.0)
    set_path(wf, "7.inputs.width", w)
    set_path(wf, "7.inputs.height", h)

    if hires:
        hw, hh = hires
        set_path(wf, "10.inputs.width", hw)
        set_path(wf, "10.inputs.height", hh)
        wf["12"] = {"class_type": "VAEEncode",
                    "inputs": {"pixels": ["10", 0], "vae": ["1", 2]}}
        wf["13"] = {"class_type": "KSampler",
                    "inputs": {"model": src, "positive": ["5", 0], "negative": ["6", 0],
                               "latent_image": ["12", 0], "seed": seed, "steps": 20,
                               "cfg": 5.0, "sampler_name": "dpmpp_2m",
                               "scheduler": "karras", "denoise": 0.42}}
        wf["14"] = {"class_type": "VAEDecode",
                    "inputs": {"samples": ["13", 0], "vae": ["1", 2]}}
        set_path(wf, "11.inputs.images", ["14", 0])
    else:
        wf.pop("10", None)
        set_path(wf, "11.inputs.images", ["9", 0])
    return wf


def render(wf, tag, dest_dir):
    set_path(wf, "11.inputs.filename_prefix", "claude-generated/terra_3d_v2/%s" % tag)
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        print("  ! %s produced nothing" % tag, file=sys.stderr)
        return None
    os.makedirs(dest_dir, exist_ok=True)
    return ensure_local(outs[0], os.path.join(dest_dir, "%s.png" % tag), required=False)


# ---------------------------------------------------------------- matting

def matte(src, tag, dest_dir):
    """BiRefNet to real RGBA. Hair is where matting fails, so the proof render on magenta
    is kept beside the cutout - a grey halo is invisible on grey and screams on magenta."""
    import PIL.Image
    im = PIL.Image.open(src)
    w, h = im.size
    base = "t3dv2_%s.png" % tag
    shutil.copy(src, os.path.join(COMFY_IN, base))

    wf = load_wf("14_birefnet_matte.json")
    set_path(wf, "1.inputs.image", base)
    set_path(wf, "8.inputs.width", w)
    set_path(wf, "8.inputs.height", h)
    set_path(wf, "10.inputs.filename_prefix",
             "claude-generated/terra_3d_v2/matte/%s_rgba" % tag)
    set_path(wf, "11.inputs.filename_prefix",
             "claude-generated/terra_3d_v2/matte/%s_mask" % tag)
    set_path(wf, "12.inputs.filename_prefix",
             "claude-generated/terra_3d_v2/matte/%s_proof" % tag)
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        return None, None
    os.makedirs(dest_dir, exist_ok=True)
    rgba = proof = None
    for rel in outs:
        n = os.path.basename(rel)
        if "_rgba" in n:
            rgba = ensure_local(rel, os.path.join(dest_dir, "%s_rgba.png" % tag))
        elif "_proof" in n:
            proof = ensure_local(rel, os.path.join(WORK, "proof", "%s_proof.png" % tag))
    return rgba, proof


# ---------------------------------------------------------------- measurement

def _labels(mask):
    """Connected components, two-pass union-find. No scipy on this box. The mask is
    downsampled by 4 first, so anything under ~16 source pixels is invisible here - which
    is the right threshold, since smaller than that is antialias speckle not geometry."""
    import numpy as np
    h, w = mask.shape
    lab = np.zeros((h, w), dtype=np.int32)
    parent = [0]

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    nxt = 1
    for y in range(h):
        row = mask[y]
        for x in range(w):
            if not row[x]:
                continue
            up = lab[y - 1, x] if y else 0
            lf = lab[y, x - 1] if x else 0
            if up and lf:
                lab[y, x] = min(up, lf)
                union(up, lf)
            elif up or lf:
                lab[y, x] = up or lf
            else:
                lab[y, x] = nxt
                parent.append(nxt)
                nxt += 1
    out = {}
    for y in range(h):
        for x in range(w):
            v = lab[y, x]
            if v:
                r = find(v)
                out[r] = out.get(r, 0) + 1
    return sorted(out.values(), reverse=True)


def _biggest(mask):
    """Boolean mask of the largest connected blob, computed on a 4x downsample.

    Needed because a colour segmentation is never clean: the teal panel on her wrap skirt
    is inside any hue window wide enough to hold the teal tips of her hair, and it sits at
    the hem. Left in, it stretches the hair bounding box to the full height of the figure
    and every fill number collapses to noise - measured, hair_drop_pct read 100% for all
    seven candidates including the ones whose hair stops at the ear. The hair is one blob
    joined at the scalp; the skirt is a different blob. Keeping the largest is enough.

    Areas and bbox fills are ratios, so computing them at 1/4 scale is exact enough and
    sixteen times cheaper.
    """
    import numpy as np
    small = mask[::4, ::4]
    h, w = small.shape
    lab = np.zeros((h, w), dtype=np.int32)
    parent = [0]

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    nxt = 1
    for y in range(h):
        row = small[y]
        for x in range(w):
            if not row[x]:
                continue
            up = lab[y - 1, x] if y else 0
            lf = lab[y, x - 1] if x else 0
            if up and lf:
                lab[y, x] = min(up, lf)
                union(up, lf)
            elif up or lf:
                lab[y, x] = up or lf
            else:
                lab[y, x] = nxt
                parent.append(nxt)
                nxt += 1
    if nxt == 1:
        return small, 0
    roots = np.array([find(i) for i in range(nxt)], dtype=np.int32)
    flat = roots[lab]
    counts = np.bincount(flat.ravel())
    counts[0] = 0
    return flat == int(counts.argmax()), int(counts.max())


def alpha_report(path):
    """Everything about an RGBA that decides whether it is a usable 3D source, plus two
    numbers v1 did not have and this iteration needs.

    HAIR_FILL_PCT is the sculpt test made numeric. Take the hair band - the top 32% of the
    figure - and ask what fraction of its bounding box is opaque. Hair drawn as separated
    locks leaves background between them, so the box is mostly holes and the number is
    low. Hair drawn as one bound mass fills its own box. This is the single number that
    separates Medusa from a figurine, and it is cheap.

    HAIR_W_RATIO is the overhang warning: hair width over shoulder width. The v1 mesh's
    hair flared wider than the body on both sides, which is the thin-shell problem and the
    overhang problem at once.
    """
    import numpy as np
    import PIL.Image
    im = PIL.Image.open(path).convert("RGBA")
    a = np.asarray(im)[:, :, 3].astype(np.int16)
    rgb = np.asarray(im)[:, :, :3].astype(np.float32)
    H, W = a.shape
    solid = a >= 128
    n = int(solid.sum())
    r = {"file": os.path.basename(path), "w": W, "h": H}
    if not n:
        r["EMPTY"] = True
        return r
    ys, xs = np.where(solid)
    y0, y1, x0, x1 = int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())
    fh, fw = y1 - y0 + 1, x1 - x0 + 1
    r["coverage_pct"] = round(100.0 * n / (W * H), 2)
    r["bbox"] = [x0, y0, x1, y1]
    r["figure_h_px"] = fh
    r["figure_h_pct"] = round(100.0 * fh / H, 1)
    r["figure_w_px"] = fw
    r["margin_px"] = {"top": y0, "bottom": H - 1 - y1, "left": x0, "right": W - 1 - x1}
    r["touches_edge"] = [k for k, v in r["margin_px"].items() if v <= 1]
    r["centre_offset_pct"] = round(100.0 * (((x0 + x1) / 2.0) - W / 2.0) / W, 1)

    soft = int(((a > 8) & (a < 248)).sum())
    per = 2.0 * (fh + fw)
    r["soft_px"] = soft
    r["edge_softness_px"] = round(soft / per, 2)

    # --- the hair band, top 15% of the figure.
    # v1 used 32% and this tool did too on its first run, which was WRONG THE MOMENT THE
    # POSE OPENED: at 32% of a seven-head figure the band reaches past the shoulders, so
    # outstretched arms land inside it. That inflates the band's bounding box to the full
    # arm span and every hair number computed from it becomes a statement about the arms.
    # It is why K3_bun first measured hair_w_ratio 1.57 while visibly having the smallest
    # hair in the set. 15% is roughly one head on this figure and stays above the collar.
    hy1 = y0 + max(1, int(fh * 0.15))
    ah = a[y0:hy1, :]
    solid_h = ah >= 128
    if solid_h.any():
        hxs = np.where(solid_h.any(axis=0))[0]
        hw_px = int(hxs.max() - hxs.min() + 1)
        hper = 2.0 * ((hy1 - y0) + hw_px)
        r["hair_edge_softness_px"] = round(
            float(((ah > 8) & (ah < 248)).sum()) / hper, 2)
        r["hair_w_px"] = hw_px
        # THE SCULPT NUMBER: opaque fraction of the hair band's own bounding box.
        box = solid_h[:, hxs.min():hxs.max() + 1]
        r["hair_fill_pct"] = round(100.0 * float(box.sum()) / box.size, 1)
        # Torso width, measured at the waist rather than the shoulders - with the arms out
        # there is no row that contains shoulders and not arms. The 45-52% band is below
        # the hands and above the hem, so it is the body alone.
        sy0, sy1 = y0 + int(fh * 0.45), y0 + int(fh * 0.52)
        srows = solid[sy0:sy1]
        if srows.any():
            widths = [int(np.ptp(np.where(row)[0]) + 1) for row in srows if row.any()]
            sh_w = float(np.median(widths))
            r["torso_w_px"] = int(sh_w)
            r["hair_w_ratio"] = round(hw_px / sh_w, 2)

    # --- THE HAIR, SEGMENTED BY ITS OWN COLOUR. This is the sculpt test made numeric and
    # it is the only version of it that works.
    #
    # A geometric band cannot measure this fault. The v1 hair is Medusa precisely BECAUSE
    # it hangs to the hips, so any band drawn around the head misses the part that is
    # wrong - K0_control scored a healthy 57.8% fill in the head band while being the
    # worst image in the set. Terra's hair is green and nothing else on her is, so the
    # colour is a free segmentation.
    #
    # HAIR_BBOX_FILL_PCT IS THE NUMBER THAT SEPARATES MEDUSA FROM A FIGURINE. Hair drawn
    # as separated S-curve locks leaves background between the locks, so its bounding box
    # is mostly holes. Hair gathered into one bound volume fills its own box. A mould
    # releases from the second and not the first.
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    chroma = mx - mn
    with np.errstate(invalid="ignore", divide="ignore"):
        hue = np.zeros_like(mx)
        g_is_max = (mx == rgb[:, :, 1]) & (chroma > 0)
        b_is_max = (mx == rgb[:, :, 2]) & (chroma > 0)
        hue[g_is_max] = 60.0 * (2.0 + (rgb[:, :, 2] - rgb[:, :, 0])[g_is_max]
                                / chroma[g_is_max])
        hue[b_is_max] = 60.0 * (4.0 + (rgb[:, :, 0] - rgb[:, :, 1])[b_is_max]
                                / chroma[b_is_max])
    # 80-200 degrees spans her whole range, pale green #A0C0A0 through the teal tips.
    # Saturation floor keeps pale skin and the white highlights out.
    hair_raw = solid & (hue >= 80) & (hue <= 200) & (chroma > 30)
    if hair_raw.sum() > 800:
        hair, harea = _biggest(hair_raw)
        if harea > 50:
            hys, hxs2 = np.where(hair)
            hy0b, hy1b = int(hys.min()) * 4, int(hys.max()) * 4
            hx0b, hx1b = int(hxs2.min()) * 4, int(hxs2.max()) * 4
            hbox = ((hy1b - hy0b) / 4.0 + 1) * ((hx1b - hx0b) / 4.0 + 1)
            r["hair_area_pct"] = round(100.0 * harea / (n / 16.0), 1)
            r["hair_bbox_fill_pct"] = round(100.0 * harea / hbox, 1)
            # How far down the body the hair reaches, 0 = crown, 100 = feet. The v1 seed
            # runs past the sash; a figurine sculpt stops near the shoulder blades.
            r["hair_drop_pct"] = round(100.0 * (hy1b - y0) / fh, 1)
            r["hair_span_w_ratio"] = round((hx1b - hx0b + 1) / float(fw), 2)

    band = (a > 40) & (a < 200)
    if band.sum() > 50:
        core = a >= 250
        bm = rgb[band].mean(axis=0)
        cm = rgb[core].mean(axis=0) if core.sum() else bm
        r["band_rgb"] = [round(float(v)) for v in bm]
        r["core_rgb"] = [round(float(v)) for v in cm]
        r["band_vs_core_dE"] = round(float(np.linalg.norm(bm - cm)), 1)

    small = solid[::4, ::4]
    sizes = _labels(small)
    r["islands"] = len(sizes)
    if sizes:
        r["island_sizes_px4"] = sizes[:6]
        r["stray_area_pct"] = round(100.0 * sum(sizes[1:]) / sum(sizes), 2)
    return r


def sheet(paths, labels, dst, cols=4, cw=380):
    """Contact sheet as a NUMBERED IMAGE SEQUENCE at a FORCED cell size.

    Two traps, both paid for here.
      1. ffmpeg's tile= fed by a glob drops cells whose size differs from the first. The
         fix is scale=W:H with BOTH dimensions forced, not scale=W:-1.
      2. tile= tiles the FRAMES OF ONE STREAM. Passing the cells as separate -i inputs
         does not tile them - it silently emits input 0 alone and pads the rest black,
         which is exactly what the first run of this tool produced. A %02d sequence is one
         stream of N frames, so it keeps tile working while still fixing trap 1.
    """
    tmp = os.path.join(WORK, "_tile")
    sh("rm", "-rf", tmp)
    os.makedirs(tmp, exist_ok=True)
    cells = []
    ch = int(cw * 1216 / 832)
    for i, (p, lb) in enumerate(zip(paths, labels)):
        cell = os.path.join(tmp, "%02d.png" % i)
        sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
           "scale=%d:%d,drawtext=text='%s':fontcolor=yellow:fontsize=19:x=6:y=6:"
           "box=1:boxcolor=black@0.85:boxborderw=5"
           % (cw, ch, lb.replace(":", "\\:").replace("'", "")), cell)
        if os.path.exists(cell):
            cells.append(cell)
    if not cells:
        return None
    rows = (len(cells) + cols - 1) // cols
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    sh("ffmpeg", "-y", "-v", "error", "-start_number", "0",
       "-i", os.path.join(tmp, "%02d.png"),
       "-vf", "tile=%dx%d:margin=6:padding=6:color=0x111111" % (cols, rows),
       "-frames:v", "1", "-q:v", "2", dst)
    return dst


# ---------------------------------------------------------------- stages

def stage_sweep(c, a):
    """The broad cross, at base resolution. 28 cells is cheap - these are image renders."""
    only_h = set(a.hair.split(",")) if a.hair else None
    only_d = set(a.hand.split(",")) if a.hand else None
    dest = os.path.join(WORK, "sweep")
    done = []
    for hair, hand in SWEEP:
        if only_h and hair not in only_h:
            continue
        if only_d and hand not in only_d:
            continue
        tag = "%s__%s" % (hair, hand)
        print("  %s" % tag, flush=True)
        p = render(graph(c, hair, hand, a.seed), tag, dest)
        if p:
            done.append((tag, p))
    # One sheet per hand treatment, so hair reads down a column of like poses.
    for hand in HANDS:
        sel = [(t, p) for t, p in done if t.endswith(hand)]
        if sel:
            sheet([p for _, p in sel], [t.split("__")[0] for t, _ in sel],
                  os.path.join(WORK, "sheet_sweep_%s.jpg" % hand), cols=4)
    sheet([p for _, p in done], [t for t, _ in done],
          os.path.join(WORK, "sheet_sweep_all.jpg"), cols=4, cw=300)
    print("\n%s" % os.path.join(WORK, "sheet_sweep_all.jpg"))


def stage_sheets(c, a):
    """Rebuild the contact sheets from what is already on disk. Separate from --stage
    sweep because a sheet bug must never cost 28 re-renders."""
    src = os.path.join(WORK, a.dir or "sweep")
    done = [(n[:-4], os.path.join(src, n))
            for n in sorted(os.listdir(src)) if n.endswith(".png")]
    for hand in HANDS:
        sel = [(t, p) for t, p in done if t.endswith(hand)]
        if sel:
            print(sheet([p for _, p in sel], [t.split("__")[0] for t, _ in sel],
                        os.path.join(WORK, "sheet_%s_%s.jpg" % (a.dir or "sweep", hand)),
                        cols=4))
    print(sheet([p for _, p in done], [t for t, _ in done],
                os.path.join(WORK, "sheet_%s_all.jpg" % (a.dir or "sweep")),
                cols=4, cw=300))


# CHOSEN FROM THE SWEEP BY THE SCULPT TEST, not by prettiness. Every cell below was
# opened and looked at; the reasoning is in RECOMMENDATION_V2.json.
#
# THE HAND AXIS IS SETTLED AT D4 and it is the same finding three times:
#   D0/D1  an unweighted hand noun BEATS the arm noun - arms drop to her sides.
#   D5     moving the closure to the negative alone does not restore the arm either.
#   D4     (outstretched arms:1.4) beats the hand noun - A-pose back, hands relaxed.
#   D6     1.5 overshoots to a T-pose AND shreds the hands into extra fingers.
#   D7     re-weighting the fist to 1.3 beats the arm again - arms drop.
# So there is a narrow window and D4 is in it. The remaining finger softness is left to
# the hires pass, which redraws the hands with four times the pixels.
#
# K0 is the CONTROL and is rendered on purpose: the v1 hair with the v2 pose, so the hair
# fix can be attributed to the tag surgery rather than to the pose change.
#
# ROUND FOUR, added after looking at the hand crops at full resolution: only H3_bun and
# H6_crown closed the hands. H0, H1 and H2 all splayed the fingers into thin separated
# spikes - the v1 fault - even though their HAIR was fixed. That is a real result and not
# a coincidence of seed: the hair treatments that shorten the hair are also the ones that
# leave the model no long-thin-strand pattern to fall into, and the fingers stop being
# drawn as strands too.
#
# So the third candidate cannot come from the H1/H2 family. It comes from attacking the
# remaining hazard instead: the fringe and the shin-length sash panels.
FINALS = [
    # tag,            hair,         hand,         seed,     extra negative
    ("K0_control",   "H0_control", "D4_outfist", SEEDS[0], ""),
    ("K1_lowpony",   "H1_lowpony", "D4_outfist", SEEDS[0], ""),
    ("K2_braid",     "H2_braid",   "D4_outfist", SEEDS[0], ""),
    ("K3_bun",       "H3_bun",     "D4_outfist", SEEDS[0], ""),
    ("K6_crown",     "H6_crown",   "D4_outfist", SEEDS[0], ""),
    ("K2_braid_s2",  "H2_braid",   "D4_outfist", SEEDS[1], ""),
    ("K3_bun_s2",    "H3_bun",     "D4_outfist", SEEDS[1], ""),
    ("K3_bun_trim",  "H3_bun",     "D4_outfist", SEEDS[0], NO_TRIM),
    ("K6_crown_trim", "H6_crown",  "D4_outfist", SEEDS[0], NO_TRIM),
]


def stage_final(c, a):
    """The survivors, rendered LARGE. Geometry detail follows source detail.

    832x1216 base then a 0.42-denoise second pass at 2x. SDXL sampled straight at
    1664x2432 duplicates limbs; the two-pass route is the only way to get real detail at
    this size on this checkpoint, and an upscaler alone would only interpolate detail a
    90px head never had.
    """
    only = set(a.only.split(",")) if a.only else None
    picks = FINALS
    if a.pick:
        picks = []
        for spec in a.pick.split(","):
            tag, hair, hand, seed = spec.split(":")
            picks.append((tag, hair, hand, int(seed), ""))
    for tag, hair, hand, seed, xneg in picks:
        if only and tag not in only:
            continue
        print("  %s (hires)" % tag, flush=True)
        render(graph(c, hair, hand, seed, hires=(1664, 2432), extra_neg=xneg), tag,
               os.path.join(WORK, "final"))


def stage_matte(c, a):
    src_dir = os.path.join(WORK, a.dir or "final")
    rows, paths, labels = [], [], []
    for n in sorted(os.listdir(src_dir)):
        if not n.endswith(".png"):
            continue
        tag = n[:-4]
        print("  matte %s" % tag, flush=True)
        rgba, proof = matte(os.path.join(src_dir, n), tag, OUT)
        if not rgba:
            continue
        r = alpha_report(rgba)
        r["tag"] = tag
        rows.append(r)
        paths.append(proof or rgba)
        labels.append("%s fill=%s%% hw=%s isl=%d" % (
            tag, r.get("hair_fill_pct", "?"), r.get("hair_w_ratio", "?"),
            r.get("islands", 0)))
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "alpha_report.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    sheet(paths, labels, os.path.join(WORK, "sheet_matte.jpg"), cols=3)
    for r in rows:
        print(json.dumps(r))


RECOMMEND = {
    "_": "WHICH SEED TO SCULPT FROM. Written by studio/_tools/terra_3d_source_v2.py "
         "--stage publish. Every claim was measured by the stage named beside it and "
         "every image behind it was opened and looked at, including the hands at full "
         "resolution rather than in a contact sheet.",

    "first_choice": {
        "use": "K3_bun_trim_rgba.png",
        "px": "1664x2432 RGBA",
        "recipe": "hair H3_bun, hand D4_outfist, seed 4242, lora 0.50, plus the NO_TRIM "
                  "negative",
        "why": [
            "HAIR IS ONE CLOSED VOLUME. A bound cap with a tied topknot, no separated "
            "locks, no background visible through it. Measured: hair_bbox_fill_pct 39.3 "
            "against the v1-hair control's 28.8, and hair_drop_pct 20.2 against the "
            "control's 33.6 - the hair stops at the jaw instead of running past the sash.",
            "HANDS ARE CLOSED and were checked as a full-resolution crop, not in a "
            "thumbnail. Both are soft closed fists with no separated digits. This is the "
            "fault the user named on the v1 mesh and it is gone.",
            "ARMS CLEAR OF THE TORSO for their whole length, with a wide air triangle on "
            "both sides. Nothing to fuse.",
            "NOTHING HANGS BELOW THE HEM. The shin-length sash panels and the fringe "
            "strands are gone, which were the features v1 flagged as below any printable "
            "minimum size and then shipped anyway.",
            "LEGS AND BOOTS SEPARATE, both feet complete, nothing bridging them.",
            "WHOLE FIGURE at 90.1% of frame height, no edge touched, matte clean at the "
            "hair edge on the magenta proof - no halo, no plate bleed.",
            "COSTUME IS THE CARD'S at wear rung 0, and unlike the v1 seed it is not "
            "rendered dirty."
        ],
        "residual": "Three or four small curl flicks still leave the hair silhouette. "
                    "They are far smaller than v1's locks but they are the most likely "
                    "place for a spike, and they are the first thing to check on the "
                    "mesh."
    },

    "runner_up": {
        "use": "K6_crown_rgba.png",
        "why": [
            "THE CLEANEST ALPHA IN THE SET - islands 1, stray area 0.00%. One connected "
            "shell and nothing else, where the bun candidates carry 3 speckle fragments.",
            "THE MOST DEFINITE HANDS - proper clenched fists with a read on the thumb, "
            "rather than the bun candidates' softer closed shape.",
            "SHORTEST HAIR DROP in the set at 18.0%."
        ],
        "against": "The shin-length sash panels SURVIVED the NO_TRIM negative here, "
                   "though the same negative removed them from H3_bun. Two thin sheets "
                   "hanging to the shin are the worst remaining print feature in the set."
    },

    "third": {
        "use": "K3_bun_rgba.png",
        "why": "Identical hair and hands to the first choice - it is K3_bun_trim with the "
               "NO_TRIM negative off. Offered because it keeps more of the canonical "
               "sash, and because holding one variable apart is what makes the trim "
               "negative's effect attributable."
    },

    "rejected_and_why": {
        "K0_control": "THE CONTROL, and it earns its place in the evidence rather than "
                      "the deliverable. Same pose vocabulary as the winners, v1's hair "
                      "tags restored - and it reproduces BOTH original faults exactly: "
                      "hair fanned into separated locks past the waist, fingers splayed "
                      "into thin spikes. That is what makes the fix attributable to the "
                      "tag surgery rather than to the pose change.",
        "K1_lowpony, K2_braid": "Hair fixed, HANDS NOT. Both splay the fingers into thin "
                                "separated spikes at full resolution. See the note under "
                                "vocabulary_that_worked - the hair treatments that "
                                "shorten the hair are the same ones that close the hands.",
        "K2_braid_s2, K3_bun_s2": "Seed 1337 changes the costume rather than the "
                                  "framing: it flares a cape as a thin sheet welded out "
                                  "to the side, and brings back a cast shadow at the "
                                  "feet. Both are v1 failure modes returning.",
        "K6_crown_trim": "The trim negative cost hair quality here without removing the "
                         "panels it was aimed at."
    },

    "vocabulary_that_worked": {
        "THE ROOT CAUSE V1 MISSED": "TERRA.json's tags field contains 'long wavy green "
            "hair, very long hair', and v1 pasted that string into every prompt then "
            "APPENDED 'ponytail, hair behind back' after it. The prompt was arguing with "
            "itself. v1 read the failure as proof that the hair volume is trained into "
            "the LoRA; that conclusion does not follow and is wrong. REMOVE the "
            "competing tags and the LoRA gives up the volume immediately - hair area "
            "fell from 13.1% of the figure to 5.1-7.3%.",
        "hair, as danbooru nouns that worked": [
            "hair bun, single hair bun, hair up, hair tied back  - best closed mass",
            "crown braid, braided bun, hair up, short hair       - tightest, best fists",
            "single braid, braided ponytail, hair tied back      - mass good, hands bad",
            "low ponytail, hair tied back                        - mass good, hands bad"
        ],
        "the anti-strand negative, which is the other half of the fix": NO_STRANDS,
        "an unexpected coupling, and it is the most reusable finding here":
            "THE HAIR TREATMENT DECIDES THE HANDS. Every candidate whose hair stayed "
            "long (H0, H1, H2) splayed its fingers into thin separated spikes; both "
            "candidates whose hair became a short bound cap (H3, H6) closed the hands "
            "into fists. The pose words were identical across all five. The model "
            "appears to hold one 'long thin strand' habit that it applies to hair and "
            "fingers together, so fixing the hair fixed the hands for free. Worth "
            "testing on the next character before assuming it generalises.",
        "the fringe and drapery negative": NO_TRIM
    },

    "vocabulary_that_did_not_work": {
        "any unweighted hand noun": "'open hands' and 'clenched hands' BOTH pull the "
            "arms down to her sides, beating 'outstretched arms'. v1's winning render "
            "had no hand noun at all, which is why it got an open pose AND fingers it "
            "never specified.",
        "moving the hand closure to the negative alone (D5)": "Does not restore the arm. "
            "The weight on the arm was the lever, not the negative on the hand.",
        "(outstretched arms:1.5) (D6)": "Overshoots into a full T-pose and shreds both "
            "hands into feathered extra fingers - worse than the fault being fixed. 1.4 "
            "is the working value and the window is narrow.",
        "re-weighting the fist to 1.3 (D7)": "Beats the arm again and the arms drop. The "
            "arm and the hand compete; only one can be weighted.",
        "hands on hips (D2)": "Fuses forearm to hip and closes an arm-to-torso loop. "
            "There is no later step that separates it. One cell also drifted off the "
            "anime engine to a 3D-render look.",
        "arms behind back (D3)": "Removes the arms from the silhouette entirely. A "
            "reconstructor gets a limbless torso.",
        "'no cast shadow' in the positive prompt": "Inherited from v1 and still true - a "
            "negation does not render. The word has to be in the negative prompt.",
        "wear rung 0's own words": "'red and blue pattern, clean and unmarked' rendered "
            "as a STAINED and torn bodice in v1. Adding damage nouns to the negative "
            "fixed it. Rung 0 describing itself is not enough."
    },

    "carry_forward_to_the_mesh_stage": [
        "HER BOOTS ARE STILL POINTED WITH A RAISED HEEL. Ground contact is two small "
        "triangles. This figure still needs a base, exactly as v1 found.",
        "THE HAIR IS NO LONGER THE DOMINANT VOLUME. It was 30% of the figure from the "
        "front in v1; it is now 7.3% of figure area with a span of 0.29 of the figure "
        "width. The overhang and thin-shell problem v1 flagged should be much reduced - "
        "worth re-measuring on the mesh rather than assuming.",
        "THE REMAINING THIN FEATURES are the earrings, the hair-ribbon prongs and three "
        "or four curl flicks at the hair edge. Check these first on the mesh.",
        "NOTHING WAS PROVEN ABOUT THE MESH. This deliverable is a source image. The "
        "claim that these two faults were source faults is now well supported, but it is "
        "only confirmed when Hunyuan3D is run on K3_bun_trim and the result is looked at."
    ]
}


def stage_publish(c, a):
    with open(os.path.join(OUT, "RECOMMENDATION_V2.json"), "w", encoding="utf-8") as f:
        json.dump(RECOMMEND, f, indent=2)
    keep = set((a.keep or "").split(",")) if a.keep else None
    if keep:
        rej = os.path.join(OUT, "rejected")
        os.makedirs(rej, exist_ok=True)
        for n in sorted(os.listdir(OUT)):
            if n.endswith("_rgba.png") and n[:-9] not in keep:
                shutil.move(os.path.join(OUT, n), os.path.join(rej, n))
    ev = os.path.join(OUT, "evidence")
    os.makedirs(ev, exist_ok=True)
    for n in sorted(os.listdir(WORK)):
        if n.endswith(".jpg"):
            shutil.copy(os.path.join(WORK, n), os.path.join(ev, n))
    for root, _, files in os.walk(OUT):
        for n in sorted(files):
            p = os.path.join(root, n)
            print("  %8.1f KB  %s" % (os.path.getsize(p) / 1024.0,
                                      os.path.relpath(p, OUT)))


COLS = ("tag", "hair_bbox_fill_pct", "hair_drop_pct", "hair_area_pct",
        "hair_span_w_ratio", "hair_edge_softness_px", "edge_softness_px", "islands",
        "stray_area_pct", "figure_h_pct", "touches_edge")


def stage_report(c, a):
    """RE-MEASURE the RGBAs on disk rather than replay alpha_report.json.

    Measuring is milliseconds and matting is not, so a metric that turns out to be wrong -
    and one here was - must never cost a re-matte to correct.
    """
    rows = []
    for root in (OUT, os.path.join(OUT, "rejected")):
        if not os.path.isdir(root):
            continue
        for n in sorted(os.listdir(root)):
            if n.endswith("_rgba.png"):
                r = alpha_report(os.path.join(root, n))
                r["tag"] = n[:-9]
                rows.append(r)
    with open(os.path.join(OUT, "alpha_report.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    print("  ".join("%-13s" % h for h in COLS))
    for r in rows:
        print("  ".join("%-13s" % str(r.get(h, "-")) for h in COLS))


def stage_prompts(c, a):
    """Print the exact strings a cell would send, without rendering. The cheapest way to
    see that the hair surgery actually removed the competing tags."""
    for hair, hand in SWEEP:
        if a.hair and hair not in a.hair.split(","):
            continue
        if a.hand and hand not in a.hand.split(","):
            continue
        print("== %s__%s\n  +%s\n  -%s\n" % (hair, hand, positive(hair, hand),
                                             negative(hair, hand)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", required=True,
                    choices=["sweep", "sheets", "final", "matte", "publish", "report",
                             "prompts"])
    ap.add_argument("--seed", type=int, default=SEEDS[0])
    ap.add_argument("--hair", default=None, help="comma list of hair tags")
    ap.add_argument("--hand", default=None, help="comma list of hand tags")
    ap.add_argument("--only", default=None, help="comma list of final tags")
    ap.add_argument("--pick", default=None,
                    help="final specs, tag:hair:hand:seed comma separated")
    ap.add_argument("--dir", default=None, help="subdir of _work to matte")
    ap.add_argument("--keep", default=None, help="publish: comma list of tags to keep")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    c = card()
    {"sweep": stage_sweep, "sheets": stage_sheets, "final": stage_final,
     "matte": stage_matte,
     "publish": stage_publish, "report": stage_report,
     "prompts": stage_prompts}[a.stage](c, a)


if __name__ == "__main__":
    main()
