#!/usr/bin/env python3
"""terra_views.py - EVERY ANGLE, EVERY EXPRESSION, EVERY SIZE, AND WHERE SHE STOPS BEING HERSELF.

    python3 studio/_tools/terra_views.py yaw          24 camera angles, 15 degrees apart
    python3 studio/_tools/terra_views.py yawprobe     4 ways to ask for an angle in NUMBERS
    python3 studio/_tools/terra_views.py octants      8 NAMED views, full figure
    python3 studio/_tools/terra_views.py elevation    camera height x yaw
    python3 studio/_tools/terra_views.py frames       6 shot sizes x 3 seeds
    python3 studio/_tools/terra_views.py emotions     all 27 emotion cards x 2 seeds
    python3 studio/_tools/terra_views.py measure      CLIP-ViT-H similarity over everything
    python3 studio/_tools/terra_views.py sheets       contact sheets, numbers burnt in
    python3 studio/_tools/terra_views.py all

`measure` and `sheets` need numpy and torch, so run the whole thing under the ComfyUI venv:

    ~/ComfyUI/venv/bin/python3 studio/_tools/terra_views.py all

WHY THIS TOOL EXISTS

turnaround.py answers "can I get 16 consistent views to train on". That is a TRAINING
question and the set is sized for a trainer, not for a reader. This answers a DIRECTOR's
question instead: before a shot is written, what does she look like from there, at that
size, feeling that - and at which of those does she stop being recognisably her.

The failures are the point. A dossier that only lists what works sends a director
half way into a scene before the limit shows up. Every stage here is built so a
failure is visible rather than averaged away.

TWO ENGINES, ON PURPOSE, BECAUSE THEY ANSWER DIFFERENT QUESTIONS

  yaw / octants / elevation   Qwen-Image-Edit 2511 + the multiple-angles LoRA, re-posing
                              her ONE reference sheet. This is a reference asset: the
                              same drawing seen from somewhere else. It is the only path
                              that can be asked for a specific number of degrees.

  frames / emotions           animagine-xl-4.0 + her trained character LoRA at the
                              measured 0.5, IPAdapter at 0.0. This is the PRODUCTION
                              path - what compile.py actually emits for a film - so a
                              limit found here is a limit a real shot will hit.

Mixing them in one tool is deliberate and the sheets are labelled with which is which.
No claim crosses between them.

HOW IDENTITY IS MEASURED, AND WHAT THE NUMBER IS NOT

Every cell is embedded with the CLIP-ViT-H-14 vision tower already on this box - the same
encoder IPAdapter uses to carry a face - and compared by cosine similarity. There is no
face recogniser installed here and installing one is not this task's to do, so:

    THIS IS A WHOLE-FRAME SIMILARITY, NOT A FACE ID SCORE.

Used naively it would be worthless, because on a yaw sweep it falls simply because the
pose changed. So each stage uses it in the one way that is not confounded:

  yaw, octants, elevation   similarity TO THE FRONT VIEW. Pose is the thing that varied,
                            so a low number is expected and only the SHAPE of the curve
                            is read - a cliff between two neighbouring angles is a
                            finding, a smooth slope is not.

  frames                    CROSS-SEED similarity WITHIN one shot size. Both cells have
                            the identical framing and differ only in seed, so framing
                            cancels out and what is left is "how reliably is she the
                            same woman at this size". That is the actual question.

  emotions                  each emotion against NEUTRAL at the same seed and framing
                            (how far this expression moves her), and the same emotion
                            across two seeds (whether it moves her somewhere REPEATABLE).
                            A big move that is repeatable is a performance. A big move
                            that is not is the character coming apart.

And then every sheet is LOOKED AT, because a number cannot tell you that the thing which
went is her jaw.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)

# ---------------------------------------------------------------------------
# the sweeps
# ---------------------------------------------------------------------------

# The yaw circle asks for ONE pinned framing, because a turnaround that changes shot size
# as it turns is measuring two things at once - exactly the bug turnaround.py recorded
# getting bitten by, where "side view ... full profile" was read as FULL BODY and those
# two views lost the costume while every other view held it.
#
# MEASURED, AND IT DOES NOT HOLD ON THIS PATH: 23 of the 24 yaw cells came back FULL
# BODY anyway. Only the elevation stage's worm/front cell honoured "waist up". So on
# Qwen-Image-Edit the framing words in an edit prompt are a suggestion, and the shot size
# is really being set by the source image - which is a full-figure sheet. If a set needs
# a particular crop, crop it afterwards; do not ask for it here and assume you got it.
YAW_FRAME = "head and shoulders, waist up, neutral expression"
YAW_STEP = 15
YAW_N = 24                      # 24 x 15 = the full circle

# THE WORDING OF THE SWEEP IS ITSELF A MEASURED RESULT - see YAW_PHRASINGS below and
# sheet_yawprobe.jpg. The first version of this line read "rotate the camera %d degrees
# CLOCKWISE around the same person" and it did something worse than fail: at 75, 90, 105,
# 180, 195, 225, 255, 270 and 285 degrees it ROLLED THE WHOLE PICTURE ONTO ITS SIDE, so
# she is lying horizontally in frame, and at several of those it drew her twice. The word
# "rotate ... degrees" is read as an image transform. That set is kept as evidence at
# yaw_rotate_failed/ and sheet_yaw_rotate_failed.jpg rather than deleted, because the
# next person to reach for degrees needs to see what it looks like when it goes wrong.
#
# The adopted wording asks for an ORBIT and explicitly pins her upright. It never rolls.
# It does NOT honour the number either - see the findings - but it fails legibly.
YAW_TEMPLATE = ("the camera orbits %d degrees to the right around the same person, "
                "she stays upright and centred in frame")

# The named views are a SEPARATE set with a separate job: a full-figure turnaround an
# animator can work from. They are NOT a control for the degree sweep - the framing
# differs, so nothing may be concluded by reading one against the other.
OCTANTS = [
    ("front",        "front view of the same person, facing the camera directly"),
    ("front_3q_l",   "three-quarter view of the same person, turned slightly to her left"),
    ("profile_l",    "full profile of the same person facing left, side view"),
    ("back_3q_l",    "rear three-quarter view of the same person, seen from behind and to her left"),
    ("back",         "the same person seen from directly behind, back of the head and back of the body"),
    ("back_3q_r",    "rear three-quarter view of the same person, seen from behind and to her right"),
    ("profile_r",    "full profile of the same person facing right, side view"),
    ("front_3q_r",   "three-quarter view of the same person, turned slightly to her right"),
]
OCTANT_FRAME = "full body, head to feet visible, standing, plain flat grey background"

# Camera HEIGHT, which is a different axis from yaw and has never been swept here. The
# existing set has one low_angle and one high_angle and nothing at the extremes.
ELEVATIONS = [
    ("worm",  "seen from directly below, extreme worm eye view, camera on the floor looking straight up"),
    ("low",   "seen from a low camera angle looking up at her"),
    ("eye",   "seen from eye level, camera level with her face"),
    ("high",  "seen from a high camera angle looking down at her"),
    ("bird",  "seen from directly above, extreme bird eye view, camera on the ceiling looking straight down"),
]
ELEV_YAWS = [
    ("front", "facing the camera"),
    ("3q",    "turned three-quarters to her left"),
    ("back",  "with her back to the camera"),
]

# THE FRAMING LADDER. Six sizes, monotone from "the face fills the frame" to "she is a
# small figure in a room". Written in the checkpoint's own vocabulary - these are
# danbooru framing tags, which is what animagine was trained on - because the model
# renders nouns and "a medium shot" is not one of its nouns.
FRAMINGS = [
    ("1_extreme_close", "extreme close-up, eye focus, face fills the frame"),
    ("2_close",         "close-up, portrait, head only"),
    ("3_medium_close",  "portrait, upper body, head and shoulders"),
    ("4_medium",        "cowboy shot, waist up"),
    ("5_wide",          "full body, standing, whole figure in frame"),
    ("6_full",          "wide shot, full body, small in frame, the whole hall visible"),
]
FRAME_SEEDS = [4242, 7411, 9090]

# THE PLACE IS NOT OPTIONAL FOR THE LADDER. A wide shot against a plain grey backdrop is
# not a wide shot, it is a small figure on grey - the size axis would collapse because
# there is nothing for her to be small IN. One place, held constant, so the only thing
# that varies down the ladder is how much of her there is.
PLACE = "ornate stone hall, tall windows, banners"

EMOTION_FRAME = "portrait, upper body"
EMOTION_SEEDS = [4242, 7411]

# Battle-tested on this character in terra_check.py. The qwen path gets NO negative:
# Qwen ignores it at cfg 1.0 with the Lightning LoRA - measured byte-identical output
# with and without - so writing one there would be a lie in the log.
NEG = ("1boy, male focus, masculine, beard, multiple girls, lowres, worst quality, "
       "bad anatomy, bad hands, watermark, text, multiple views")
Q = "masterpiece, best quality, very aesthetic, absurdres"

QWEN_WF = "32_qwen_turnaround.json"
ANIME_WF = "22_anime_kf_ipadapter.json"
CKPT = "animagine-xl-4.0.safetensors"


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def out_dir(cid):
    return os.path.join(STUDIO, "samples", "cast", cid.lower() + "_views")


def stage_dir(cid, stage):
    d = os.path.join(out_dir(cid), stage)
    os.makedirs(d, exist_ok=True)
    return d


def card(cid):
    p = os.path.join(STUDIO, "characters", cid + ".json")
    if not os.path.exists(p):
        raise SystemExit("no character card at %s" % p)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------

def _studio_imports():
    """Imported late and only when rendering.

    scripts/comfy.py is the studio's HTTP client and it SHADOWS ComfyUI's own `comfy`
    package. The measure stage needs the real one. Keeping both out of the module top
    level is what lets one process do rendering and a different one do embedding without
    either import fighting the other.
    """
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    sys.path.insert(0, STUDIO)
    os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
    from comfy import run, set_path                      # noqa: E402
    from epic import load_wf, ensure_local, COMFY, HOST  # noqa: E402
    import compose                                       # noqa: E402
    return run, set_path, load_wf, ensure_local, COMFY, HOST, compose


def qwen_cell(mods, src_name, prompt, seed, dst, force=False):
    """One Qwen-Image-Edit re-pose of the reference sheet."""
    run, set_path, load_wf, ensure_local, COMFY, HOST, _ = mods
    if os.path.exists(dst) and not force:
        return "skip"
    # ensure_local RETURNS EARLY WHEN THE DESTINATION EXISTS. That is a landmine for a
    # probe that names scratch files after the cell: the second run re-tiles the FIRST
    # run's pixels and reads as "the change did nothing". Every destination here is the
    # cell's own final file and is deleted first, so there is nothing stale to return.
    if os.path.exists(dst):
        os.remove(dst)
    wf = load_wf(QWEN_WF)
    set_path(wf, "7.inputs.image", src_name)
    set_path(wf, "10.inputs.prompt", prompt)
    set_path(wf, "15.inputs.seed", seed)
    set_path(wf, "17.inputs.filename_prefix",
             "claude-generated/terra_views/%s" % os.path.basename(dst)[:-4])
    try:
        _, outs = run(HOST, wf, quiet=True)
    except Exception as e:
        print("    FAILED %s" % str(e)[:110])
        return "fail"
    if not outs or not ensure_local(outs[0], dst, required=False):
        return "fail"
    return "made"


def anime_cell(mods, prompt, neg, seed, lora, strength, dst, force=False):
    """One animagine render with the character LoRA and no IPAdapter."""
    run, set_path, load_wf, ensure_local, COMFY, HOST, _ = mods
    if os.path.exists(dst) and not force:
        return "skip"
    if os.path.exists(dst):
        os.remove(dst)
    wf = load_wf(ANIME_WF)
    set_path(wf, "1.inputs.ckpt_name", CKPT)
    # IPAdapter at ZERO. A reference sheet was MEASURED to suppress the style layer -
    # four different styles came back as one render repeated - and the same suppression
    # would flatten an expression sweep into 27 copies of one face. The LoRA carries her.
    set_path(wf, "4.inputs.weight", 0.0)
    set_path(wf, "5.inputs.text", prompt)
    set_path(wf, "6.inputs.text", neg)
    set_path(wf, "8.inputs.seed", seed)
    for n in ("7", "10"):
        set_path(wf, "%s.inputs.width" % n, 1024)
        set_path(wf, "%s.inputs.height" % n, 1024)
    if lora and strength > 0:
        wf["90"] = {"class_type": "LoraLoaderModelOnly",
                    "inputs": {"model": ["1", 0], "lora_name": lora,
                               "strength_model": float(strength)}}
        for nid, node in list(wf.items()):
            if nid in ("1", "90") or not isinstance(node, dict):
                continue
            for k, v in (node.get("inputs") or {}).items():
                if isinstance(v, list) and len(v) == 2 and v[0] == "1" and v[1] == 0:
                    node["inputs"][k] = ["90", 0]
    set_path(wf, "11.inputs.filename_prefix",
             "claude-generated/terra_views/%s" % os.path.basename(dst)[:-4])
    try:
        _, outs = run(HOST, wf, quiet=True)
    except Exception as e:
        print("    FAILED %s" % str(e)[:110])
        return "fail"
    if not outs or not ensure_local(outs[0], dst, required=False):
        return "fail"
    return "made"


def stage_source(mods, c, cid):
    """Qwen-Image-Edit can only LoadImage from ComfyUI's own input dir."""
    _, _, _, _, COMFY, _, _ = mods
    sheet = c.get("sheet")
    if not sheet:
        raise SystemExit("%s has no `sheet` to turn around" % cid)
    src = os.path.join(COMFY, "input", sheet)
    if not os.path.exists(src):
        raise SystemExit("sheet not found at %s" % src)
    name = "%s_views_src.png" % cid.lower()
    sh("cp", src, os.path.join(COMFY, "input", name))
    return name


# ---------------------------------------------------------------------------
# stages
# ---------------------------------------------------------------------------

def do_yaw(mods, c, cid, force):
    d = stage_dir(cid, "yaw")
    src = stage_source(mods, c, cid)
    print("yaw: %d steps of %d degrees, framing pinned to %r" % (YAW_N, YAW_STEP, YAW_FRAME))
    counts = {}
    for i in range(YAW_N):
        deg = i * YAW_STEP
        # UNIFORM PHRASING FOR EVERY STEP, including the cardinals. It is tempting to
        # help 90 and 180 along with the words "profile" and "from behind" - they are
        # the views a dossier most needs - but then the cardinals get a better prompt
        # than their neighbours and the sweep stops measuring the angle and starts
        # measuring the wording. If degrees do not work, that is the finding.
        p = "%s, %s, plain flat grey background" % (YAW_TEMPLATE % deg, YAW_FRAME)
        dst = os.path.join(d, "yaw_%03d.png" % deg)
        r = qwen_cell(mods, src, p, 1100 + i, dst, force)
        counts[r] = counts.get(r, 0) + 1
        print("  %03d deg  %s" % (deg, r), flush=True)
    return counts


# FOUR WAYS TO ASK FOR AN ANGLE THAT IS NOT A NAME. Added after looking at the first yaw
# sweep, which did something worse than fail: at 75, 90 and 105 degrees it came back with
# the WHOLE PICTURE ROLLED ON ITS SIDE - she is lying horizontally in frame, upright
# relative to nothing. The word "rotate ... degrees" was read as an image transform, not
# as a camera move around a subject. That is a plausible enough reading of the English
# that it is worth finding out whether ANY numeric phrasing orbits, before concluding
# that degrees are unavailable on this path.
YAW_PHRASINGS = [
    ("rotate", "rotate the camera %d degrees clockwise around the same person, "
               "starting from directly in front of her"),
    ("orbit",  "the camera orbits %d degrees to the right around the same person, "
               "she stays upright and centred in frame"),
    ("subject", "the same person turns %d degrees to her left where she stands, "
                "the camera does not move and stays level"),
    ("sheet",  "turnaround sheet frame: the same person seen at a %d degree angle "
               "between the front view and the back view, standing upright"),
]
YAW_PROBE_ANGLES = [45, 135, 225]


def do_yawprobe(mods, c, cid, force):
    d = stage_dir(cid, "yawprobe")
    src = stage_source(mods, c, cid)
    print("yawprobe: %d phrasings x %d angles" % (len(YAW_PHRASINGS), len(YAW_PROBE_ANGLES)))
    counts = {}
    i = 0
    for pid, tmpl in YAW_PHRASINGS:
        for deg in YAW_PROBE_ANGLES:
            p = "%s, %s, plain flat grey background" % (tmpl % deg, YAW_FRAME)
            dst = os.path.join(d, "%s_%03d.png" % (pid, deg))
            r = qwen_cell(mods, src, p, 1500 + i, dst, force)
            counts[r] = counts.get(r, 0) + 1
            print("  %-8s %03d  %s" % (pid, deg, r), flush=True)
            i += 1
    return counts


def do_octants(mods, c, cid, force):
    d = stage_dir(cid, "octants")
    src = stage_source(mods, c, cid)
    print("octants: 8 named views, %r" % OCTANT_FRAME)
    counts = {}
    for i, (vid, prose) in enumerate(OCTANTS):
        p = "%s, %s" % (prose, OCTANT_FRAME)
        dst = os.path.join(d, "%d_%s.png" % (i, vid))
        r = qwen_cell(mods, src, p, 1200 + i, dst, force)
        counts[r] = counts.get(r, 0) + 1
        print("  %-12s %s" % (vid, r), flush=True)
    return counts


def do_elevation(mods, c, cid, force):
    d = stage_dir(cid, "elevation")
    src = stage_source(mods, c, cid)
    print("elevation: %d heights x %d yaws, waist up; plus %d heights full body"
          % (len(ELEVATIONS), len(ELEV_YAWS), len(ELEVATIONS)))
    counts = {}
    i = 0
    for ei, (eid, eprose) in enumerate(ELEVATIONS):
        for yi, (yid, yprose) in enumerate(ELEV_YAWS):
            p = ("the same person %s, %s, %s, plain flat grey background"
                 % (yprose, eprose, YAW_FRAME))
            dst = os.path.join(d, "wu_%d%s_%s.png" % (ei, eid, yid))
            r = qwen_cell(mods, src, p, 1300 + i, dst, force)
            counts[r] = counts.get(r, 0) + 1
            print("  waist-up %-5s %-5s %s" % (eid, yid, r), flush=True)
            i += 1
    # The whole-figure row. Worm and bird eye are fundamentally about a BODY being
    # foreshortened, and a waist-up crop cannot show that.
    for ei, (eid, eprose) in enumerate(ELEVATIONS):
        p = ("the same person facing the camera, %s, %s" % (eprose, OCTANT_FRAME))
        dst = os.path.join(d, "fb_%d%s_front.png" % (ei, eid))
        r = qwen_cell(mods, src, p, 1400 + ei, dst, force)
        counts[r] = counts.get(r, 0) + 1
        print("  full-body %-5s front %s" % (eid, r), flush=True)
    return counts


def _anime_prompt(compose, libs, cid, desc, emotion=None, strip_name=False):
    r = compose.resolve(libs, {"character": cid, "engine": "anime", "wear": 0,
                               "emotion": emotion or "", "desc": desc,
                               "place": PLACE, "output": "still"})
    p = r["prompt"]
    if strip_name:
        p = ", ".join(x for x in p.split(", ")
                      if "terra branford" not in x and "final fantasy" not in x)
    return p, r


def do_frames(mods, c, cid, force):
    d = stage_dir(cid, "frames")
    compose = mods[6]
    libs = compose.load_libs()
    lora = c.get("lora")
    st = float(c.get("lora_strength_measured") or 0.5)
    print("frames: %d sizes x %d seeds, LoRA %s at %.2f"
          % (len(FRAMINGS), len(FRAME_SEEDS), lora, st))
    counts = {}
    for fid, desc in FRAMINGS:
        for seed in FRAME_SEEDS:
            p, _ = _anime_prompt(compose, libs, cid, desc, "neutral")
            dst = os.path.join(d, "%s_s%d.png" % (fid, seed))
            r = anime_cell(mods, p, NEG, seed, lora, st, dst, force)
            counts[r] = counts.get(r, 0) + 1
            print("  %-16s seed %-5d %s" % (fid, seed, r), flush=True)
    return counts


def do_emotions(mods, c, cid, force):
    d = stage_dir(cid, "emotions")
    compose = mods[6]
    libs = compose.load_libs()
    lora = c.get("lora")
    st = float(c.get("lora_strength_measured") or 0.5)
    ids = sorted(libs.get("emotions") or {})
    print("emotions: %d cards x %d seeds at %r" % (len(ids), len(EMOTION_SEEDS), EMOTION_FRAME))
    counts = {}
    for eid in ids:
        results = []
        for seed in EMOTION_SEEDS:
            # The emotion cards are used EXACTLY AS AUTHORED - compose.resolve pulls
            # face, eyes, mouth and body straight off the card. No rewording, because
            # the question is whether the library as written produces 27 distinct faces,
            # not whether 27 faces can be coaxed out of this checkpoint by someone
            # rewriting the cards on the way past.
            p, _ = _anime_prompt(compose, libs, cid, EMOTION_FRAME, eid)
            dst = os.path.join(d, "%s_s%d.png" % (eid, seed))
            r = anime_cell(mods, p, NEG, seed, lora, st, dst, force)
            counts[r] = counts.get(r, 0) + 1
            results.append(r)
        print("  %-14s %s" % (eid, " ".join(results)), flush=True)
    return counts


# ---------------------------------------------------------------------------
# measurement
# ---------------------------------------------------------------------------

def _embed_worker(manifest_path, out_path):
    """Runs in its own process with ComfyUI on the path and the GPU hidden.

    The GPU is hidden because ComfyUI is holding ~15 GB of it and a 630M-parameter
    vision tower asking for another 20 MB is how you OOM a probe against your own
    renderer. CLIP-ViT-H on CPU is a few seconds an image and this is not a hot loop.
    """
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    comfy_root = os.path.expanduser("~/ComfyUI")
    sys.path.insert(0, comfy_root)
    os.chdir(comfy_root)
    # comfy.model_management asks torch for a CUDA device AT IMPORT TIME and dies if
    # there is not one, so hiding the GPU is not enough on its own - it also has to be
    # TOLD, and the only channel for that is ComfyUI's own argv parser. This process is
    # not ComfyUI and has no other use for argv, so overwriting it is safe.
    #
    # And argv alone is not enough either: comfy/cli_args.py parses the REAL argv only if
    # comfy.options.args_parsing has been switched on, which main.py does and an importer
    # does not - otherwise it parses an empty list and every flag silently defaults. So
    # the switch has to be thrown by hand, before anything under comfy/ is imported.
    sys.argv = [sys.argv[0], "--cpu"]
    import comfy.options
    comfy.options.enable_args_parsing()
    import numpy as np
    import torch
    from PIL import Image
    import comfy.clip_vision as clip_vision

    model_p = os.path.join(comfy_root, "models", "clip_vision",
                           "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors")
    m = clip_vision.load(model_p)
    with open(manifest_path, encoding="utf-8") as f:
        paths = json.load(f)
    out = {}
    for i, p in enumerate(paths):
        try:
            im = Image.open(p).convert("RGB")
            a = np.array(im).astype(np.float32) / 255.0
            t = torch.from_numpy(a)[None, ]
            with torch.no_grad():
                e = m.encode_image(t)["image_embeds"].detach().flatten().float().cpu().numpy()
            e = e / (float(np.linalg.norm(e)) + 1e-9)
            out[p] = [float(x) for x in e]
        except Exception as ex:
            print("  embed failed %s: %s" % (os.path.basename(p), str(ex)[:80]))
        if (i + 1) % 20 == 0:
            print("  embedded %d/%d" % (i + 1, len(paths)), flush=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f)
    print("embedded %d/%d" % (len(out), len(paths)))


def _all_pngs(cid):
    paths = []
    for stage in ("yaw", "octants", "elevation", "frames", "emotions"):
        # yawprobe is deliberately absent: it is four different prompts, so a similarity
        # between its cells would be measuring the wording and nothing else.
        d = os.path.join(out_dir(cid), stage)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".png"):
                paths.append(os.path.join(d, fn))
    return paths


def do_measure(cid):
    paths = _all_pngs(cid)
    if not paths:
        raise SystemExit("nothing rendered yet")
    work = os.path.join(out_dir(cid), "_embed")
    os.makedirs(work, exist_ok=True)
    man, emb = os.path.join(work, "manifest.json"), os.path.join(work, "embeds.json")
    with open(man, "w", encoding="utf-8") as f:
        json.dump(paths, f)
    print("embedding %d images on CPU with CLIP-ViT-H-14" % len(paths))
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "_embed", man, emb])
    if r.returncode != 0 or not os.path.exists(emb):
        raise SystemExit("embedding failed")
    with open(emb, encoding="utf-8") as f:
        E = json.load(f)

    def cos(a, b):
        if a not in E or b not in E:
            return None
        x, y = E[a], E[b]
        return round(sum(p * q for p, q in zip(x, y)), 4)

    d = lambda s, n: os.path.join(out_dir(cid), s, n)
    M = {"_what": "cosine similarity of CLIP-ViT-H-14 image embeddings. WHOLE FRAME, "
                  "not a face ID score - read the note in the tool docstring before "
                  "quoting any of these.",
         "_sheets": {
             "sheet_yaw.jpg":
                 "yaw/ - 24 camera angles 15 degrees apart, Qwen-Image-Edit from the "
                 "reference sheet, one uniform prompt with only the number changing. "
                 "Compare against sheet_yawprobe.jpg before reading it.",
             "sheet_yawprobe.jpg":
                 "yawprobe/ - the same three angles asked for in four different English "
                 "phrasings. This is the control that says what the number in the yaw "
                 "sweep is actually doing.",
             "sheet_yaw_rotate_failed.jpg":
                 "yaw_rotate_failed/ - KEPT DELIBERATELY. The first yaw sweep, phrased "
                 "'rotate the camera N degrees clockwise'. Nine of its 24 cells are the "
                 "whole picture rolled onto its side and several draw her twice.",
             "sheet_octants.jpg":
                 "octants/ - 8 NAMED views at full figure. The turnaround an animator "
                 "would work from.",
             "sheet_elevation.jpg":
                 "elevation/ - 5 camera heights x 3 yaws at waist-up, plus the 5 heights "
                 "at full figure.",
             "sheet_frames.jpg":
                 "frames/ - the shot-size ladder, 6 sizes x 3 seeds, on the PRODUCTION "
                 "path (animagine + her character LoRA at 0.5). Rows are sizes, columns "
                 "are seeds, so identity drift reads left-to-right.",
             "sheet_emotions_s4242.jpg / sheet_emotions_s7411.jpg":
                 "emotions/ - all 27 emotion cards as authored, one sheet per seed. Read "
                 "the two side by side: an expression that is different between them is "
                 "not directable."},
         "yaw_vs_front": {}, "octant_vs_front": {}, "elevation_vs_eye_front": {},
         "frames_cross_seed": {}, "frames_vs_medium_close": {},
         "emotion_vs_neutral": {}, "emotion_cross_seed": {}}

    ref = d("yaw", "yaw_000.png")
    for i in range(YAW_N):
        deg = i * YAW_STEP
        v = cos(ref, d("yaw", "yaw_%03d.png" % deg))
        if v is not None:
            M["yaw_vs_front"]["%03d" % deg] = v

    oref = d("octants", "0_front.png")
    for i, (vid, _) in enumerate(OCTANTS):
        v = cos(oref, d("octants", "%d_%s.png" % (i, vid)))
        if v is not None:
            M["octant_vs_front"][vid] = v

    eref = d("elevation", "wu_2eye_front.png")
    for ei, (eid, _) in enumerate(ELEVATIONS):
        for yid, _ in ELEV_YAWS:
            v = cos(eref, d("elevation", "wu_%d%s_%s.png" % (ei, eid, yid)))
            if v is not None:
                M["elevation_vs_eye_front"]["waistup_%s_%s" % (eid, yid)] = v
        v = cos(eref, d("elevation", "fb_%d%s_front.png" % (ei, eid)))
        if v is not None:
            M["elevation_vs_eye_front"]["fullbody_%s_front" % eid] = v

    mid = "3_medium_close"
    for fid, _ in FRAMINGS:
        vals = []
        for i in range(len(FRAME_SEEDS)):
            for j in range(i + 1, len(FRAME_SEEDS)):
                v = cos(d("frames", "%s_s%d.png" % (fid, FRAME_SEEDS[i])),
                        d("frames", "%s_s%d.png" % (fid, FRAME_SEEDS[j])))
                if v is not None:
                    vals.append(v)
        if vals:
            M["frames_cross_seed"][fid] = {"mean": round(sum(vals) / len(vals), 4),
                                           "min": min(vals), "pairs": vals}
        v = cos(d("frames", "%s_s%d.png" % (mid, FRAME_SEEDS[0])),
                d("frames", "%s_s%d.png" % (fid, FRAME_SEEDS[0])))
        if v is not None:
            M["frames_vs_medium_close"][fid] = v

    emo_dir = os.path.join(out_dir(cid), "emotions")
    ids = sorted(set(fn.rsplit("_s", 1)[0] for fn in os.listdir(emo_dir)
                     if fn.endswith(".png"))) if os.path.isdir(emo_dir) else []
    for eid in ids:
        vs = []
        for seed in EMOTION_SEEDS:
            v = cos(d("emotions", "neutral_s%d.png" % seed),
                    d("emotions", "%s_s%d.png" % (eid, seed)))
            if v is not None:
                vs.append(v)
        if vs:
            M["emotion_vs_neutral"][eid] = round(sum(vs) / len(vs), 4)
        if len(EMOTION_SEEDS) > 1:
            v = cos(d("emotions", "%s_s%d.png" % (eid, EMOTION_SEEDS[0])),
                    d("emotions", "%s_s%d.png" % (eid, EMOTION_SEEDS[1])))
            if v is not None:
                M["emotion_cross_seed"][eid] = v

    dst = os.path.join(out_dir(cid), "measurements.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(M, f, indent=2, sort_keys=True)
    print("\n%s" % dst)
    for k in ("frames_cross_seed",):
        print("  %s:" % k)
        for a, b in sorted(M[k].items()):
            print("    %-18s mean %.4f  min %.4f" % (a, b["mean"], b["min"]))
    return M


# ---------------------------------------------------------------------------
# contact sheets
# ---------------------------------------------------------------------------

def _label(src, text, dst, size=430):
    """Burn the label - and the number - onto the tile.

    The number goes on the PICTURE rather than into a table beside it because the whole
    point is to read them together: a similarity of 0.71 means nothing until you can see
    that the 0.71 is a different woman.
    """
    text = text.replace(":", " ").replace("'", "").replace("\\", " ")
    vf = ("scale=%d:%d:force_original_aspect_ratio=decrease,"
          "pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=0x111111,"
          "drawtext=text='%s':fontcolor=yellow:fontsize=20:x=6:y=6:"
          "box=1:boxcolor=black@0.85:boxborderw=5" % (size, size, size, size, text))
    sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vf", vf, dst)
    return os.path.exists(dst)


def _tile(tmp, n, cols, dst):
    if not n:
        return None
    rows = (n + cols - 1) // cols
    r = sh("ffmpeg", "-y", "-v", "error", "-pattern_type", "glob", "-i",
           os.path.join(tmp, "*.png"), "-filter_complex",
           "tile=%dx%d:margin=6:padding=6:color=0x111111" % (cols, rows),
           "-frames:v", "1", "-q:v", "3", dst)
    if not os.path.exists(dst):
        print("  tile failed for %s: %s" % (dst, (r.stderr or "")[-200:]))
        return None
    return dst


def _fresh(cid, name):
    t = os.path.join(out_dir(cid), "_tiles", name)
    sh("rm", "-rf", t)
    os.makedirs(t, exist_ok=True)
    return t


def do_sheets(cid):
    O = out_dir(cid)
    mp = os.path.join(O, "measurements.json")
    M = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
    made = []

    # yaw
    src = os.path.join(O, "yaw")
    if os.path.isdir(src):
        t = _fresh(cid, "yaw")
        n = 0
        for i in range(YAW_N):
            deg = i * YAW_STEP
            p = os.path.join(src, "yaw_%03d.png" % deg)
            if not os.path.exists(p):
                continue
            sim = M.get("yaw_vs_front", {}).get("%03d" % deg)
            lab = "%d deg" % deg + ("  sim %.3f" % sim if sim is not None else "")
            if _label(p, lab, os.path.join(t, "%02d.png" % n)):
                n += 1
        r = _tile(t, n, 6, os.path.join(O, "sheet_yaw.jpg"))
        if r:
            made.append(r)

    # yawprobe - one row per phrasing
    src = os.path.join(O, "yawprobe")
    if os.path.isdir(src):
        t = _fresh(cid, "yawprobe")
        n = 0
        for pid, _ in YAW_PHRASINGS:
            for deg in YAW_PROBE_ANGLES:
                p = os.path.join(src, "%s_%03d.png" % (pid, deg))
                if not os.path.exists(p):
                    continue
                if _label(p, "%s %d deg" % (pid, deg), os.path.join(t, "%02d.png" % n)):
                    n += 1
        r = _tile(t, n, len(YAW_PROBE_ANGLES), os.path.join(O, "sheet_yawprobe.jpg"))
        if r:
            made.append(r)

    # octants
    src = os.path.join(O, "octants")
    if os.path.isdir(src):
        t = _fresh(cid, "octants")
        n = 0
        for i, (vid, _) in enumerate(OCTANTS):
            p = os.path.join(src, "%d_%s.png" % (i, vid))
            if not os.path.exists(p):
                continue
            sim = M.get("octant_vs_front", {}).get(vid)
            lab = vid.replace("_", " ") + ("  sim %.3f" % sim if sim is not None else "")
            if _label(p, lab, os.path.join(t, "%02d.png" % n)):
                n += 1
        r = _tile(t, n, 4, os.path.join(O, "sheet_octants.jpg"))
        if r:
            made.append(r)

    # elevation - one row per height, waist-up yaws then the full body cell
    src = os.path.join(O, "elevation")
    if os.path.isdir(src):
        t = _fresh(cid, "elevation")
        n = 0
        for ei, (eid, _) in enumerate(ELEVATIONS):
            cells = [("wu_%d%s_%s.png" % (ei, eid, y), "%s %s" % (eid, y))
                     for y, _ in ELEV_YAWS]
            cells.append(("fb_%d%s_front.png" % (ei, eid), "%s full body" % eid))
            for fn, lab in cells:
                p = os.path.join(src, fn)
                if not os.path.exists(p):
                    continue
                key = ("waistup_%s_%s" % (eid, fn.rsplit("_", 1)[1][:-4])
                       if fn.startswith("wu_") else "fullbody_%s_front" % eid)
                sim = M.get("elevation_vs_eye_front", {}).get(key)
                if sim is not None:
                    lab += "  sim %.3f" % sim
                if _label(p, lab, os.path.join(t, "%02d.png" % n)):
                    n += 1
        r = _tile(t, n, 4, os.path.join(O, "sheet_elevation.jpg"))
        if r:
            made.append(r)

    # frames - one row per shot size, one column per seed
    src = os.path.join(O, "frames")
    if os.path.isdir(src):
        t = _fresh(cid, "frames")
        n = 0
        for fid, _ in FRAMINGS:
            cs = M.get("frames_cross_seed", {}).get(fid) or {}
            for seed in FRAME_SEEDS:
                p = os.path.join(src, "%s_s%d.png" % (fid, seed))
                if not os.path.exists(p):
                    continue
                lab = "%s s%d" % (fid, seed)
                if cs:
                    lab += "  xseed %.3f" % cs["mean"]
                if _label(p, lab, os.path.join(t, "%02d.png" % n)):
                    n += 1
        r = _tile(t, n, len(FRAME_SEEDS), os.path.join(O, "sheet_frames.jpg"))
        if r:
            made.append(r)

    # emotions - two sheets, one per seed, so a whole seed can be read as a set
    src = os.path.join(O, "emotions")
    if os.path.isdir(src):
        ids = sorted(set(fn.rsplit("_s", 1)[0] for fn in os.listdir(src)
                         if fn.endswith(".png")))
        for seed in EMOTION_SEEDS:
            t = _fresh(cid, "emo%d" % seed)
            n = 0
            for eid in ids:
                p = os.path.join(src, "%s_s%d.png" % (eid, seed))
                if not os.path.exists(p):
                    continue
                dn = M.get("emotion_vs_neutral", {}).get(eid)
                xs = M.get("emotion_cross_seed", {}).get(eid)
                lab = eid
                if dn is not None:
                    lab += "  vN %.3f" % dn
                if xs is not None:
                    lab += "  xs %.3f" % xs
                if _label(p, lab, os.path.join(t, "%02d.png" % n), size=380):
                    n += 1
            r = _tile(t, n, 6, os.path.join(O, "sheet_emotions_s%d.jpg" % seed))
            if r:
                made.append(r)

    # The per-tile labelled PNGs are scratch and there are ~150 of them. Leaving them
    # in the dossier directory makes it unreadable, which defeats the point of a dossier.
    sh("rm", "-rf", os.path.join(O, "_tiles"))
    for p in made:
        print("  %s  %.0f KB" % (p, os.path.getsize(p) / 1024))
    return made


# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "_embed":
        return _embed_worker(sys.argv[2], sys.argv[3])

    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["yaw", "yawprobe", "octants", "elevation", "frames",
                                      "emotions", "measure", "sheets", "all"])
    ap.add_argument("--character", default="TERRA")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    cid = a.character.upper()
    c = card(cid)
    os.makedirs(out_dir(cid), exist_ok=True)

    render = a.stage in ("yaw", "yawprobe", "octants", "elevation", "frames",
                         "emotions", "all")
    mods = _studio_imports() if render else None

    if a.stage in ("yaw", "all"):
        do_yaw(mods, c, cid, a.force)
    if a.stage in ("yawprobe", "all"):
        do_yawprobe(mods, c, cid, a.force)
    if a.stage in ("octants", "all"):
        do_octants(mods, c, cid, a.force)
    if a.stage in ("elevation", "all"):
        do_elevation(mods, c, cid, a.force)
    if a.stage in ("frames", "all"):
        do_frames(mods, c, cid, a.force)
    if a.stage in ("emotions", "all"):
        do_emotions(mods, c, cid, a.force)
    if a.stage in ("measure", "all"):
        do_measure(cid)
    if a.stage in ("sheets", "all"):
        do_sheets(cid)


if __name__ == "__main__":
    main()
