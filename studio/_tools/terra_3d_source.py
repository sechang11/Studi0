#!/usr/bin/env python3
"""Make source images a single-image-to-3D model can actually use.

    --stage pose              which pose words open her arms, and is the LoRA to blame
    --stage light --pose out  which light leaves no cast shadow at her feet
    --stage final             the candidates, at 1664x2432
    --stage matte --dir final BiRefNet to RGBA, then measure the alpha
    --stage views             GRADE the existing 16-view turnaround for multi-view use
    --stage mv                BUILD a multi-view set from text, one seed, one canvas
    --stage mvq               BUILD one from an image instead, so the costume is pinned
    --stage publish           assemble source/ and write RECOMMENDATION.json
    --stage report            print the measurements back

Run them in that order; each later stage reads what the earlier ones left in
studio/samples/terra_3d/_work/.

THIS TOOL HAS ARGPARSE AND DOES NOTHING AT IMPORT TIME. Seventeen of the sixty tools in
this directory run their whole job on any argument including --help; this one does not.

WHAT A RECONSTRUCTION MODEL WANTS IS NEARLY THE OPPOSITE OF A GOOD FILM FRAME.
  A-POSE OR T-POSE. An arm resting against the hip is one blob to a feed-forward
    reconstructor. There is no later step that separates them - the geometry simply never
    had two surfaces there.
  FLAT EVEN LIGHT. A hard shadow terminator is a luminance edge, and a luminance edge is
    the same signal a silhouette edge is. It gets baked in as a dent.
  PLAIN BACKGROUND, THEN ALPHA. Not white. A white plate matted to white leaves a white
    halo welded to the hair.
  WHOLE FIGURE, CENTRED, WITH MARGIN. A foot touching the frame edge is a foot the model
    reconstructs as cut off.
  ORTHOGRAPHIC-ISH. A wide lens close in makes the near hand huge; that perspective is
    baked into the mesh as a genuinely huge hand.
  WEAR RUNG 0. Damage tags do not render above rung 1 on this character anyway, and a
    figurine wants the canonical outfit.

THE VARIABLE THIS TOOL EXISTS TO MEASURE is whether her pose can be opened at all. Her
LoRA was trained on sixteen views in which the arms hang against the body in every single
one, so the training may well be what welds them. That is why the pose stage sweeps LoRA
strength alongside the pose words instead of holding it at the card's 0.50.
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

OUT = os.path.join(ROOT, "studio", "samples", "terra_3d", "source")
WORK = os.path.join(ROOT, "studio", "samples", "terra_3d", "_work")
CAST = os.path.join(ROOT, "studio", "samples", "cast", "TERRA")
COMFY_IN = os.path.expanduser("~/ComfyUI/input")

SEEDS = [4242, 1337]
Q = "masterpiece, best quality, very aesthetic, absurdres"

# Everything a film frame is allowed to have and a reconstruction source is not.
NEG = (
    "cropped, out of frame, close-up, upper body, portrait, multiple views, multiple girls, "
    "2girls, 1boy, male focus, sitting, lying, kneeling, from above, from below, dutch angle, "
    "leaning, dynamic pose, arms behind back, hand on hip, holding, orb, weapon, "
    "dramatic lighting, harsh shadow, cast shadow, backlighting, rim light, spotlight, "
    "chiaroscuro, gradient background, scenery, indoors, outdoors, cluttered background, "
    "text, watermark, signature, artist name, border, letterboxed, "
    "motion blur, blurry, depth of field, lowres, worst quality, bad anatomy, bad hands, "
    "extra arms, extra legs, missing limb, fused fingers"
)

# The pose words, as danbooru forms. "spread arms" and "outstretched arms" are real tags in
# the corpus this checkpoint learned; "arms away from body" is a description and is here as
# a control on whether description reaches the pixels at all.
POSES = {
    "down":   "arms at sides, standing",
    "spread": "spread arms, legs apart, standing",
    "tpose":  "spread arms, outstretched arms, arms to the sides, legs apart, standing",
    "out":    "outstretched arms, legs apart, standing",
    "away":   "arms at sides, arms away from body, legs apart, open hands, empty hands, standing",
}

# (positive words, extra negative words). The extra negative exists because L1 was MEASURED
# to leave a dark cast-shadow pool at her feet in the pose sweep - "no cast shadow" in the
# POSITIVE prompt is a negation, and negations do not render. The lever that works on a
# thing you do not want is the negative prompt.
LIGHTS = {
    "L0": ("", ""),
    "L1": ("soft even lighting, diffuse light, no cast shadow", ""),
    "L2": ("flat color, no shading, even lighting", ""),
    "L3": ("soft even lighting, diffuse light, ambient light",
           "shadow, drop shadow, floor, ground, reflection"),
}

FRAME = ("full body, standing, whole figure in frame, full length shot, symmetrical, "
         "centered")

# For the multi-view set. `view_verdict` on her card already established that NAMED views
# work on this project and that asking for a turnaround IN DEGREES does not, so these are
# names. (positive, extra negative).
VIEWS = [
    ("V0_front",  "facing viewer, looking at viewer, straight-on view", ""),
    ("V1_fq_l",   "three quarter view, facing to the left", "looking at viewer"),
    ("V2_side_l", "from side, profile, facing left", "looking at viewer"),
    ("V3_back",   "from behind, facing away, back",
     "looking at viewer, face, facial features"),
    ("V4_side_r", "from side, profile, facing right", "looking at viewer"),
    ("V5_fq_r",   "three quarter view, facing to the right", "looking at viewer"),
]

# THE PLATE IS A MATTING VARIABLE, NOT A DECORATION. Measured here: on the grey plate
# BiRefNet ATE A BARE FOREARM - pale skin on pale grey is not enough contrast, the arm was
# severed and the hand came out as a floating island of 1.3% of the figure area. The
# candidate that survived did so only because that seed happened to give her red sleeves.
# The plate is named in the LoRA training captions, so it is also the one background word
# the trigger will actually honour.
PLATES = {
    "grey": "plain flat grey background, simple background",
    "dark": "plain flat dark blue background, simple background",
}


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def card():
    with open(os.path.join(ROOT, "studio", "characters", "TERRA.json"), encoding="utf-8") as f:
        return json.load(f)


def positive(c, pose, light, hair="", plate="grey", view=""):
    """The danbooru name is LOAD-BEARING and stays in - measured, without it the LoRA
    alone returns a generic green-haired woman."""
    bits = [c["tags"], c.get("base_tags", ""), hair,
            (c.get("wear_tags") or [""])[0], POSES[pose], view, FRAME, LIGHTS[light][0],
            PLATES[plate], Q]
    return ", ".join(b for b in bits if b)


def negative(light, view_neg=""):
    extra = ", ".join(x for x in (LIGHTS[light][1], view_neg) if x)
    return NEG + (", " + extra if extra else "")


def graph(c, pose, light, seed, lora_st, w=832, h=1216, hires=None, hair="", plate="grey",
          view="", view_neg=""):
    """The production anime path with the IPAdapter branch REMOVED rather than zeroed.

    face_quality.py sets the IPAdapter weight to 0.0 and leaves the nodes in. That still
    loads the IPAdapter model and still requires sheet_rask.png to exist in the input
    folder. Deleting the branch and rewiring the sampler straight to the model is cheaper
    and has no residual.
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

    set_path(wf, "5.inputs.text", positive(c, pose, light, hair, plate, view))
    set_path(wf, "6.inputs.text", negative(light, view_neg))
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
    set_path(wf, "11.inputs.filename_prefix", "claude-generated/terra_3d/%s" % tag)
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
    base = "t3d_%s.png" % tag
    shutil.copy(src, os.path.join(COMFY_IN, base))

    wf = load_wf("14_birefnet_matte.json")
    set_path(wf, "1.inputs.image", base)
    set_path(wf, "8.inputs.width", w)
    set_path(wf, "8.inputs.height", h)
    set_path(wf, "10.inputs.filename_prefix", "claude-generated/terra_3d/matte/%s_rgba" % tag)
    set_path(wf, "11.inputs.filename_prefix", "claude-generated/terra_3d/matte/%s_mask" % tag)
    set_path(wf, "12.inputs.filename_prefix", "claude-generated/terra_3d/matte/%s_proof" % tag)
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
    """Connected components on a boolean array, two-pass with union-find.

    No scipy on this box. The mask is downsampled by 4 before this runs, so a stray island
    smaller than ~16 source pixels is invisible to it - which is the right threshold
    anyway, since anything smaller than that is antialias speckle rather than geometry.
    """
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


def alpha_report(path):
    """Everything about an RGBA that decides whether it is a usable 3D source.

    Reported rather than scored, because two of these are trade-offs and not faults: a
    wide antialias band is correct for hair drawn as lineart, and a few small islands are
    correct if they are the ribbon prongs.
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

    # Antialias band: pixels that are neither in nor out. Divided by the bbox perimeter it
    # is the mean edge softness in pixels, which is the number that matters - a 1px band is
    # a crisp matte, a 6px band on hair is a spike generator.
    soft = int(((a > 8) & (a < 248)).sum())
    per = 2.0 * (fh + fw)
    r["soft_px"] = soft
    r["edge_softness_px"] = round(soft / per, 2)

    # The same figure for the HAIR REGION alone - the top 32% of the figure, where matting
    # actually fails on this character.
    hy1 = y0 + max(1, int(fh * 0.32))
    ah = a[y0:hy1, :]
    solid_h = ah >= 128
    if solid_h.any():
        hxs = np.where(solid_h.any(axis=0))[0]
        hper = 2.0 * ((hy1 - y0) + (hxs.max() - hxs.min() + 1))
        r["hair_edge_softness_px"] = round(
            float(((ah > 8) & (ah < 248)).sum()) / hper, 2)

    # Colour of the semi-transparent band. If the plate leaks into it, every one of those
    # pixels carries background grey and the mesh gets a grey rind at the silhouette.
    band = (a > 40) & (a < 200)
    if band.sum() > 50:
        core = a >= 250
        bm = rgb[band].mean(axis=0)
        cm = rgb[core].mean(axis=0) if core.sum() else bm
        r["band_rgb"] = [round(float(v)) for v in bm]
        r["core_rgb"] = [round(float(v)) for v in cm]
        r["band_vs_core_dE"] = round(float(np.linalg.norm(bm - cm)), 1)

    # Stray islands, on a 4x downsample.
    small = solid[::4, ::4]
    sizes = _labels(small)
    r["islands"] = len(sizes)
    if sizes:
        r["island_sizes_px4"] = sizes[:6]
        r["stray_area_pct"] = round(100.0 * sum(sizes[1:]) / sum(sizes), 2)
    return r


def sheet(paths, labels, dst, cols=None):
    tmp = os.path.join(WORK, "_tile")
    sh("rm", "-rf", tmp)
    os.makedirs(tmp, exist_ok=True)
    for i, (p, lb) in enumerate(zip(paths, labels)):
        sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
           "scale=430:-1,drawtext=text='%s':fontcolor=yellow:fontsize=17:x=6:y=6:"
           "box=1:boxcolor=black@0.85:boxborderw=5" % lb.replace(":", "\\:").replace("'", ""),
           os.path.join(tmp, "%02d.png" % i))
    n = len(paths)
    cols = cols or min(5, n)
    rows = (n + cols - 1) // cols
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    sh("ffmpeg", "-y", "-v", "error", "-pattern_type", "glob",
       "-i", os.path.join(tmp, "*.png"), "-filter_complex",
       "tile=%dx%d:margin=6:padding=6:color=0x111111" % (cols, rows),
       "-frames:v", "1", "-q:v", "2", dst)
    return dst


# ---------------------------------------------------------------- stages

def stage_pose(c, a):
    """Can her arms be opened at all, and is the LoRA what welds them?"""
    paths, labels = [], []
    for st in (0.5, 0.25):
        for pose in POSES:
            tag = "pose_%s_l%02d" % (pose, int(st * 100))
            print("  %s" % tag, flush=True)
            p = render(graph(c, pose, "L1", SEEDS[0], st), tag, os.path.join(WORK, "pose"))
            if p:
                paths.append(p)
                labels.append("%s  lora %.2f" % (pose, st))
    dst = sheet(paths, labels, os.path.join(WORK, "sheet_pose.jpg"), cols=5)
    print("\n%s" % dst)


def stage_light(c, a):
    paths, labels = [], []
    for light in LIGHTS:
        for seed in SEEDS:
            tag = "light_%s_%s_s%d" % (a.pose, light, seed)
            print("  %s" % tag, flush=True)
            p = render(graph(c, a.pose, light, seed, a.lora), tag,
                       os.path.join(WORK, "light"))
            if p:
                paths.append(p)
                labels.append("%s  %s  s%d" % (a.pose, light, seed))
    dst = sheet(paths, labels, os.path.join(WORK, "sheet_light_%s.jpg" % a.pose), cols=2)
    print("\n%s" % dst)


# CHOSEN FROM THE TWO SWEEPS, not from taste.
#   pose=out      "outstretched arms" is the only pose word that opened her arms with real
#                 air on both sides. "spread arms" - the danbooru tag that MEANS a T-pose -
#                 did not; it returned arms near the hips at both LoRA strengths.
#   light=L3      the only arm with no cast-shadow pool at her feet that still keeps form
#                 shading. L2 also has no pool but flattens the body to unshaded colour,
#                 which removes the only volume cue a reconstructor has; it is kept as one
#                 control cell rather than as a candidate.
#   lora=0.50     the card's measured strength. 0.25 was tested and is not a free win: at
#                 "spread" it drifted off the anime engine entirely and returned a smooth
#                 3D-render doll. The LoRA was never what welded her arms - the words
#                 "arms at sides" were.
FINALS = [
    # tag,           pose,    light, seed,     lora, hair, plate
    ("A_out_L3_s1",  "out",   "L3", SEEDS[0], 0.50, "", "grey"),
    ("B_out_L3_s2",  "out",   "L3", SEEDS[1], 0.50, "", "grey"),
    ("C_out_L2_s1",  "out",   "L2", SEEDS[0], 0.50, "", "grey"),
    ("D_away_L3_s1", "away",  "L3", SEEDS[0], 0.50, "", "grey"),
    ("E_tpose_L3",   "tpose", "L3", SEEDS[0], 0.50, "", "grey"),
    ("F_tamehair",   "out",   "L3", SEEDS[0], 0.50, "ponytail, hair behind back", "grey"),
    # G and H are A and B with ONE variable changed - the plate colour - so that the
    # severed-forearm failure can be attributed rather than guessed at.
    ("G_out_dark_s1", "out",  "L3", SEEDS[0], 0.50, "", "dark"),
    ("H_out_dark_s2", "out",  "L3", SEEDS[1], 0.50, "", "dark"),
]


def stage_final(c, a):
    """The candidates, rendered LARGE. Geometry detail follows source detail.

    832x1216 base then a 0.42-denoise second pass at 2x. SDXL sampled straight at 1664x2432
    duplicates limbs; the two-pass route is the only way to get real detail at this size on
    this checkpoint, and an upscaler alone would only interpolate the detail that a 90px
    head never had.
    """
    only = set(a.only.split(",")) if a.only else None
    for tag, pose, light, seed, st, hair, plate in FINALS:
        if only and tag not in only:
            continue
        print("  %s (hires)" % tag, flush=True)
        wf = graph(c, pose, light, seed, st, hires=(1664, 2432), hair=hair, plate=plate)
        render(wf, tag, os.path.join(WORK, "final"))


def stage_views(c, a):
    """The existing 16-view turnaround, measured rather than eyeballed.

    Hunyuan3Dv2ConditioningMultiView wants the SAME subject at the SAME scale seen from
    known angles. Two things decide whether this set qualifies and both are measurable
    from the alpha: figure height per view (scale agreement) and whether the figure is
    cropped by the frame (an incomplete view is worse than a missing one).
    """
    names = ["00_front", "01_three_quarter", "02_side_left", "03_side_right",
             "04_back", "15_full_body"]
    dest = os.path.join(WORK, "views")
    rows = []
    paths, labels = [], []
    for n in names:
        src = os.path.join(CAST, n + ".png")
        if not os.path.exists(src):
            continue
        rgba, proof = matte(src, "view_" + n, dest)
        if not rgba:
            continue
        r = alpha_report(rgba)
        r["view"] = n
        rows.append(r)
        paths.append(proof or rgba)
        labels.append("%s  h=%d%%  crop=%s" % (n, r.get("figure_h_pct", 0),
                                               ",".join(r.get("touches_edge") or []) or "none"))
    with open(os.path.join(OUT, "multiview_report.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    sheet(paths, labels, os.path.join(WORK, "sheet_views.jpg"), cols=3)
    hs = [r.get("figure_h_pct", 0) for r in rows]
    print("\nfigure height as %% of frame, per view:")
    for r in rows:
        print("  %-18s %5.1f%%  crop=%s  islands=%d" % (
            r["view"], r.get("figure_h_pct", 0),
            ",".join(r.get("touches_edge") or []) or "none", r.get("islands", 0)))
    bad = [r["view"] for r in rows if r.get("touches_edge")]
    print("\nCROPPED BY THE FRAME: %s" % (", ".join(bad) or "none"))
    print("DO NOT READ THE HEIGHT COLUMN AS SCALE AGREEMENT. It saturates: a figure whose "
          "legs left the frame measures ~100%% of frame height precisely BECAUSE it is cut "
          "off. The spread is %.1f-%.1f only because %d of %d views are cropped, and a "
          "cropped view cannot be scale-matched to a complete one at all."
          % (min(hs or [0]), max(hs or [0]), len(bad), len(rows)))
    isl = [r.get("islands", 0) for r in rows]
    print("islands per view %s - these are detached hair fragments, and every one of them "
          "is a floating shell in whatever mesh consumes the view." % isl)


def normalise(rgba_paths, dst_dir, canvas=(1024, 1408), fill=0.86):
    """Put every view on ONE canvas at ONE figure height, centred, feet on a common line.

    THIS IS THE STEP THAT MAKES A MULTI-VIEW SET USABLE and it is the step the existing
    turnaround never had. A multi-view conditioner assumes the views differ ONLY in camera
    azimuth. A text-to-image model does not honour that - it re-frames every prompt - so
    the agreement has to be imposed afterwards, from the alpha, deterministically. Scale
    each view so its alpha bounding box is `fill` of the canvas height, centre it
    horizontally on the bbox centroid, and sit the bottom of the bbox on a shared baseline.

    It cannot fix a view that is CROPPED. A figure whose feet left the frame has no true
    height to normalise to, and scaling it to match the others just makes a giant. Those
    are reported and excluded rather than silently rescaled.
    """
    import numpy as np
    import PIL.Image
    CW, CH = canvas
    target_h = int(CH * fill)
    base_y = int(CH * 0.96)
    out, report = [], []
    os.makedirs(dst_dir, exist_ok=True)
    for p in rgba_paths:
        im = PIL.Image.open(p).convert("RGBA")
        a = np.asarray(im)[:, :, 3]
        ys, xs = np.where(a >= 128)
        if not len(ys):
            continue
        y0, y1, x0, x1 = int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())
        H, W = a.shape
        cropped = [k for k, v in (("top", y0), ("bottom", H - 1 - y1),
                                  ("left", x0), ("right", W - 1 - x1)) if v <= 1]
        fh = y1 - y0 + 1
        s = target_h / float(fh)
        crop = im.crop((x0, y0, x1 + 1, y1 + 1))
        nw, nh = max(1, int(round(crop.width * s))), target_h
        crop = crop.resize((nw, nh), PIL.Image.LANCZOS)
        canv = PIL.Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
        canv.paste(crop, (int((CW - nw) / 2), base_y - nh), crop)
        d = os.path.join(dst_dir, os.path.basename(p).replace("_rgba", "_mv"))
        canv.save(d)
        out.append(d)
        report.append({"src": os.path.basename(p), "scale_applied": round(s, 3),
                       "src_figure_h_px": fh, "cropped_by_frame": cropped})
    return out, report


def costume_agreement(paths):
    """Do the views agree about what she is WEARING?

    Not a similarity score between images - views of the same person from different sides
    are supposed to look different. What must NOT differ is the palette: the same garments
    in the same colours occupy roughly the same share of the figure from any angle. So this
    measures the fraction of opaque pixels falling in each of her named colour families and
    reports the SPREAD across views. A cape that is knee-length in one view and floor-length
    and shredded in another shows up here as a large swing in the red share.
    """
    import numpy as np
    import PIL.Image
    fam = {"green_hair": ((0, 90, 60), (180, 255, 220)),
           "red_cape":   ((110, 0, 0), (255, 110, 110)),
           "gold_dress": ((150, 110, 0), (255, 225, 140)),
           "skin":       ((215, 190, 165), (255, 245, 235))}
    rows = []
    for p in paths:
        arr = np.asarray(PIL.Image.open(p).convert("RGBA")).astype(np.int16)
        m = arr[:, :, 3] >= 200
        rgb = arr[:, :, :3][m]
        n = max(1, len(rgb))
        r = {"view": os.path.basename(p)}
        for k, (lo, hi) in fam.items():
            sel = np.all((rgb >= np.array(lo)) & (rgb <= np.array(hi)), axis=1)
            r[k] = round(100.0 * int(sel.sum()) / n, 1)
        rows.append(r)
    spread = {}
    for k in fam:
        v = [r[k] for r in rows]
        spread[k] = {"min": min(v), "max": max(v), "range": round(max(v) - min(v), 1)}
    return rows, spread


def stage_mv(c, a):
    """A multi-view set built to be a multi-view set, against the one that was not.

    One seed, one pose, one plate, one light, one canvas - only the view name moves. That
    is the most a text-to-image model can be asked for; it will still drift on costume
    detail, and the point of the measurement afterwards is to say by how much rather than
    to assume it did not.
    """
    src, labels = [], []
    for tag, vpos, vneg in VIEWS:
        print("  %s" % tag, flush=True)
        wf = graph(c, a.pose, "L3", a.seed, a.lora, hires=(1248, 1824),
                   plate="dark", view=vpos, view_neg=vneg)
        p = render(wf, "mv_" + tag, os.path.join(WORK, "mv_raw"))
        if p:
            src.append((tag, p))
    rgbas = []
    for tag, p in src:
        rgba, _ = matte(p, "mv_" + tag, os.path.join(WORK, "mv_rgba"))
        if rgba:
            rgbas.append(rgba)
    mv_dir = os.path.join(OUT, "multiview")
    norm, nrep = normalise(rgbas, mv_dir)
    rows, spread = costume_agreement(norm)
    alphas = [alpha_report(p) for p in norm]
    with open(os.path.join(OUT, "multiview_built.json"), "w", encoding="utf-8") as f:
        json.dump({"normalise": nrep, "palette": rows, "palette_spread": spread,
                   "alpha": alphas}, f, indent=2)
    sheet(norm, [os.path.basename(p).replace("_mv.png", "") for p in norm],
          os.path.join(WORK, "sheet_mv.jpg"), cols=3)
    print("\nscale each view needed to reach a common figure height:")
    for r in nrep:
        print("  %-22s x%.3f  cropped=%s" % (r["src"], r["scale_applied"],
                                             ",".join(r["cropped_by_frame"]) or "none"))
    print("\npalette share of the figure, per view (%):")
    for r in rows:
        print("  %-22s hair %5.1f  red %5.1f  gold %5.1f  skin %5.1f" % (
            r["view"], r["green_hair"], r["red_cape"], r["gold_dress"], r["skin"]))
    print("\nspread across views: " + json.dumps(spread))


# Views for the image-conditioned path. Prose, not danbooru tags - this graph is driven by
# a Qwen VL text encoder reading a reference image, not by an SDXL tag soup.
QVIEWS = [
    ("Q0_front",  "front view of the same person, facing the camera directly"),
    ("Q1_fq_l",   "three-quarter view of the same person, turned 45 degrees to the left"),
    ("Q2_side_l", "side view of the same person, facing left"),
    ("Q3_back",   "back view of the same person, seen from directly behind"),
    ("Q4_side_r", "side view of the same person, facing right"),
    ("Q5_fq_r",   "three-quarter view of the same person, turned 45 degrees to the right"),
]


def stage_mvq(c, a):
    """The multi-view set again, but with the costume pinned by an IMAGE instead of by words.

    WHY THIS EXISTS. The text-conditioned set (stage mv) fixed every structural fault of the
    old turnaround - nothing cropped, one scale, one plate, arms open in all six - and still
    could not hold the costume: her bodice came back gold in the front view and red in the
    other five. That is not a framing problem and no amount of prompt work fixes it, because
    the bodice colour is bistable under the LoRA-plus-danbooru-name combination and each view
    is an independent sample of that coin flip.

    An image-conditioned turnaround removes the coin flip: every view is conditioned on the
    SAME picture, so the garment is carried as pixels rather than re-drawn from a description.
    The project already owns the graph (workflows/32) and a multiple-angles LoRA for it.
    Her own card warns that this path pins the MEDIUM as hard as the identity - here that is
    the point, because the source is anime lineart and the views should stay anime lineart.
    """
    src = os.path.join(WORK, "final", a.src or "G_out_dark_s1.png")
    if not os.path.exists(src):
        raise SystemExit("no source render at %s - run --stage final first" % src)
    base = "t3d_mvq_src.png"
    shutil.copy(src, os.path.join(COMFY_IN, base))

    outs = []
    for tag, prompt in QVIEWS:
        print("  %s" % tag, flush=True)
        wf = load_wf("32_qwen_turnaround.json")
        set_path(wf, "7.inputs.image", base)
        set_path(wf, "10.inputs.prompt", prompt)
        set_path(wf, "15.inputs.seed", a.seed)
        set_path(wf, "40.inputs.strength_model", a.angles)
        p = render_at(wf, "17", "mvq_" + tag, os.path.join(WORK, "mvq_raw"))
        if p:
            outs.append((tag, p))

    rgbas = []
    for tag, p in outs:
        rgba, _ = matte(p, "mvq_" + tag, os.path.join(WORK, "mvq_rgba"))
        if rgba:
            rgbas.append(rgba)
    mv_dir = os.path.join(OUT, "multiview_qwen")
    norm, nrep = normalise(rgbas, mv_dir)
    rows, spread = costume_agreement(norm)
    with open(os.path.join(OUT, "multiview_qwen.json"), "w", encoding="utf-8") as f:
        json.dump({"source": os.path.basename(src), "angles_lora": a.angles,
                   "normalise": nrep, "palette": rows, "palette_spread": spread,
                   "alpha": [alpha_report(p) for p in norm]}, f, indent=2)
    sheet(norm, [os.path.basename(p).replace("_mv.png", "") for p in norm],
          os.path.join(WORK, "sheet_mvq.jpg"), cols=3)
    print("\npalette share of the figure, per view (%):")
    for r in rows:
        print("  %-24s hair %5.1f  red %5.1f  gold %5.1f  skin %5.1f" % (
            r["view"], r["green_hair"], r["red_cape"], r["gold_dress"], r["skin"]))
    print("\nspread across views: " + json.dumps(spread))
    print("Compare the gold and red ranges against multiview_built.json. A tighter range "
          "means the views agree about the garment; that is the whole question.")


def render_at(wf, save_node, tag, dest_dir):
    """Same as render() for a graph whose SaveImage is not node 11."""
    set_path(wf, "%s.inputs.filename_prefix" % save_node,
             "claude-generated/terra_3d/%s" % tag)
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        print("  ! %s produced nothing" % tag, file=sys.stderr)
        return None
    os.makedirs(dest_dir, exist_ok=True)
    return ensure_local(outs[0], os.path.join(dest_dir, "%s.png" % tag), required=False)


def stage_matte(c, a):
    src_dir = os.path.join(WORK, a.dir or "final")
    rows = []
    paths, labels = [], []
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
        labels.append("%s  soft=%.1fpx hair=%.1fpx isl=%d" % (
            tag, r.get("edge_softness_px", 0), r.get("hair_edge_softness_px", 0),
            r.get("islands", 0)))
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "alpha_report.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    sheet(paths, labels, os.path.join(WORK, "sheet_matte.jpg"), cols=3)
    for r in rows:
        print(json.dumps(r))


RECOMMEND = {
    "_": "WHICH FILE TO FEED WHAT. Written by studio/_tools/terra_3d_source.py --stage "
         "publish. Every claim below was measured by the stage named beside it and every "
         "image behind it was opened and looked at.",
    "single_view": {
        "use": "G_out_dark_s1_rgba.png",
        "px": "1664x2432 RGBA",
        "why": [
            "ARMS CLEAR OF THE TORSO with air on both sides for their whole length, and "
            "open hands. Measured in --stage pose: of five pose vocabularies only "
            "'outstretched arms' opened her. The danbooru tag 'spread arms', which MEANS "
            "a T-pose, returned arms near the hips at both LoRA strengths tested.",
            "LEGS AND BOOTS SEPARATE, both feet complete, nothing bridging them.",
            "NO CAST SHADOW at her feet. Measured in --stage light: the L1 arm left a "
            "shadow pool even though its POSITIVE prompt said 'no cast shadow'. Only "
            "moving the word to the NEGATIVE prompt (L3) removed it.",
            "WHOLE FIGURE, 90.0% of frame height, centre offset -0.7%, no edge touched.",
            "ALPHA IS ONE SHELL PLUS SPECKLE - stray area 0.04% of the figure.",
            "COSTUME IS THE CARD'S: gold patterned bodice, wear rung 0."
        ],
        "runner_up": "B_out_L3_s2_rgba.png - the only grey-plate candidate that mattes to "
                     "a single connected shell (islands=1), but its cape flares as a thin "
                     "sheet welded to both forearms."
    },
    "multi_view": {
        "use": "multiview_qwen/  (Q0_front, Q2_side_l, Q3_back, Q4_side_r)",
        "px": "1024x1408 RGBA, from 832x1248 renders",
        "why": [
            "COSTUME AGREES ACROSS VIEWS, which is the only thing that decides whether "
            "multi-view conditioning helps or hurts. Same gold bodice, same fringed wrap "
            "skirt, same red-and-gold boots in every view.",
            "Built image-conditioned from the single-view winner through workflow 32 plus "
            "the multiple-angles LoRA, so the garment is carried as pixels.",
            "Then normalised deterministically: one canvas, one figure height, one "
            "baseline, centred. Nothing cropped."
        ],
        "prefer_four_not_six": "Q1 and Q5 are nominally 45-degree three-quarters but came "
                               "back close to profile, so the six views do not sample the "
                               "circle evenly. The four cardinals are honest; adding the "
                               "two near-duplicates over-weights the sides.",
        "cost": "Each view is 832x1248 against the single-view candidate's 1664x2432 - "
                "about a quarter of the pixels per view. Multi-view buys angular coverage "
                "and pays for it in source detail."
    },
    "do_not_use": {
        "what": "studio/samples/cast/TERRA/ 00_front, 01_three_quarter, 02_side_left, "
                "03_side_right, 04_back, 15_full_body",
        "why": [
            "THREE OF THE SIX ARE CROPPED BY THE FRAME - 00_front and 02_side_left and "
            "03_side_right lose the legs or the feet. A cropped view cannot be "
            "scale-matched to a complete one, so the set has no common scale at all.",
            "THE COSTUME DISAGREES. The cape is smooth and short in 00_front and "
            "02_side_left and floor-length, shredded and stained in 04_back and "
            "15_full_body. Those are two different garments.",
            "ARMS ARE AGAINST THE BODY IN ALL SIXTEEN VIEWS - it is the pose the LoRA was "
            "trained on - so every view fuses arm to torso.",
            "MATTES DIRTY: 17 detached fragments on 00_front, 11 on 02_side_left. Each is "
            "a floating shell downstream."
        ]
    },
    "carry_forward_to_the_mesh_stage": [
        "HER BOOTS ARE POINTED WITH A RAISED HEEL. The ground contact is two small "
        "triangles. Whatever else happens, this figure needs a base.",
        "THE HAIR IS THE DOMINANT VOLUME - 30% of the figure from the front and 57% from "
        "behind, and it flares away from the body on both sides. It is the overhang "
        "problem and the thin-shell problem at once. 'ponytail, hair behind back' was "
        "tried in --stage final as F_tamehair and did NOT reduce it; the volume is trained "
        "into the LoRA.",
        "THE SKIRT FRINGE is drawn as many separate hanging strands. At figurine scale "
        "each is far below any printable minimum feature size."
    ]
}


def stage_publish(c, a):
    """Assemble source/ as the deliverable and record what to feed what."""
    keep = {"G_out_dark_s1_rgba.png", "B_out_L3_s2_rgba.png", "H_out_dark_s2_rgba.png",
            "C_out_L2_s1_rgba.png"}
    rej = os.path.join(OUT, "rejected")
    os.makedirs(rej, exist_ok=True)
    for n in sorted(os.listdir(OUT)):
        if n.endswith("_rgba.png") and n not in keep:
            shutil.move(os.path.join(OUT, n), os.path.join(rej, n))
    ev = os.path.join(OUT, "evidence")
    os.makedirs(ev, exist_ok=True)
    for s in ("sheet_pose.jpg", "sheet_light_out.jpg", "sheet_matte.jpg",
              "sheet_views.jpg", "sheet_mv.jpg", "sheet_mvq.jpg"):
        p = os.path.join(WORK, s)
        if os.path.exists(p):
            shutil.copy(p, os.path.join(ev, s))
    with open(os.path.join(OUT, "RECOMMENDATION.json"), "w", encoding="utf-8") as f:
        json.dump(RECOMMEND, f, indent=2)
    for root, _, files in os.walk(OUT):
        for n in sorted(files):
            p = os.path.join(root, n)
            print("  %8.1f KB  %s" % (os.path.getsize(p) / 1024.0,
                                      os.path.relpath(p, OUT)))


def stage_report(c, a):
    for name in ("alpha_report.json", "multiview_report.json"):
        p = os.path.join(OUT, name)
        if os.path.exists(p):
            print("== %s" % name)
            print(open(p, encoding="utf-8").read())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", required=True,
                    choices=["pose", "light", "final", "views", "mv", "mvq", "matte",
                             "publish", "report"])
    ap.add_argument("--pose", default="out", choices=sorted(POSES))
    ap.add_argument("--lora", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=SEEDS[0])
    ap.add_argument("--only", default=None, help="comma list of final tags")
    ap.add_argument("--dir", default=None, help="subdir of _work to matte")
    ap.add_argument("--src", default=None, help="mvq: filename in _work/final to rotate")
    ap.add_argument("--angles", type=float, default=0.85,
                    help="mvq: multiple-angles LoRA strength")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    c = card()
    {"pose": stage_pose, "light": stage_light, "final": stage_final, "views": stage_views,
     "mv": stage_mv, "mvq": stage_mvq, "matte": stage_matte,
     "publish": stage_publish, "report": stage_report}[a.stage](c, a)


if __name__ == "__main__":
    main()
