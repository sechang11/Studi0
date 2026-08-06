#!/usr/bin/env python3
"""HOW MANY PHOTOS does a character need - measured, not guessed.

    python3 studio/_tools/photo_count_probe.py --stage narrow
    python3 studio/_tools/photo_count_probe.py --stage datasets
    python3 studio/_tools/photo_count_probe.py --stage train --arm n8
    python3 studio/_tools/photo_count_probe.py --stage ipa
    python3 studio/_tools/photo_count_probe.py --stage battery --arm n8
    python3 studio/_tools/photo_count_probe.py --stage sheets

THIS TOOL HAS ARGPARSE AND DOES NOTHING AT IMPORT TIME.

THE TWO AXES.

  COUNT.  n4 -> n8 -> n16, nested subsets of the same stand-in set, every training
          hyper-parameter held constant (1000 steps, rank 16, lr 5e-4, seed 7311).
          Holding steps constant is the point: a 4-image set sees each image 250 times
          and a 16-image set sees each 62, and that difference IS what changes.

  SPREAD. n8 (eight shots differing in angle, light and outfit) against n8narrow (eight
          near-identical front shots, one outfit, one light, one framing - generated for
          this probe so the two arms differ ONLY in variety). Same count, same steps.
          TERRA memorised her costume from a one-costume set; this is the experiment
          that says whether variety or count is the lever.

  And a third thing falls out for free: n8bad, the six deliberate duds plus the two
  stress shots, is a fixed-count QUALITY contrast against n8. Without it n16 (which is
  n8 + n8bad) cannot be read, because n16 changes count AND quality at once.

ZERO-TRAINING ARM. IPAdapter PLUS FACE with one reference photograph and no LoRA at all.
Swept over weight first, because the usable band has never been measured here and giving
the arm a wrong weight would be rigging the comparison.

WHAT IS JUDGED, AND IT IS NOT A COSINE.  The stand-in carries five deliberate marks -
thin round gold glasses, a mole on the right cheek, dark brown hair just past the
shoulders with a grown-out fringe, gold stud earrings, and (in most of the set) a mustard
corduroy jacket. Four things get looked at in every battery cell:

    IDENTITY   is it recognisably her, marks intact
    STYLE      did the anime survive, or did the photograph come through
    OBEDIENCE  the battery asks for garments and places NOT in any training set. A LoRA
               that has memorised returns the training outfit instead.
    USABLE     would this frame ship

The battery is fixed and identical for every arm at the same seeds, so the sheets are
column-comparable.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.expanduser("~/shared/comfy-studio")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                              # noqa: E402
from epic import load_wf, ensure_local, submit, COMFY, HOST  # noqa: E402

STANDIN = os.path.join(ROOT, "studio", "samples", "photo2anime", "standin")
OUT = os.path.join(ROOT, "studio", "samples", "photo2anime", "count")
WORK = os.path.join(OUT, "_work")
COMFY_IN = os.path.join(COMFY, "input")
LORA_DIR = os.path.join(COMFY, "models", "loras")

TRIGGER = "stnda"

# ---------------------------------------------------------------- the person, in prose
# Byte-identical to standin_person.py FACE. Only used to GENERATE the narrow arm, so the
# eight near-identical shots are the same woman as the sixteen already on disk.
FACE = (
    "a woman in her early thirties, ordinary looking rather than glamorous, an oval face "
    "with a slightly crooked nose and uneven eyebrows, warm light-olive skin with visible "
    "pores, faint under-eye shadows and a few small blemishes, no makeup, dark brown eyes, "
    "thin round gold wire-frame glasses, a small dark mole on her right cheek about an "
    "inch below the eye, dark brown hair falling just past her shoulders, parted on the "
    "left, with a grown-out fringe tucked behind one ear"
)
WEAR_A = "a mustard yellow corduroy jacket over a plain white t-shirt"
SNAP = ("a candid amateur photograph, taken on a phone, slight sensor noise, ordinary "
        "unretouched skin")
NEG_PHOTO = ("cartoon, anime, illustration, painting, drawing, 3d render, cgi, plastic "
             "skin, doll, mannequin, wig, glamour retouching, airbrushed, beauty filter, "
             "fashion model, studio glamour, oversaturated, watermark, text, signature, "
             "deformed, extra limbs, extra fingers, fused fingers, blurry, lowres")

# The eight near-identical shots. Same framing, same light, same wall, same jacket, same
# expression. Only the seed moves. That is the definition of a narrow set.
NARROW_PROSE = ("a head and shoulders photograph, straight on to the camera, flat even "
                "indoor lighting, a plain white wall behind her, neutral expression")
NARROW_SEEDS = [8101, 8102, 8103, 8104, 8105, 8106, 8107, 8108]

# ---------------------------------------------------------------- captions
# A caption is a subtraction (turnaround.py caption()). Everything named here stays
# separable and changeable; everything NOT named - face, hair, glasses, mole, earrings -
# is absorbed by the trigger and becomes what stnda IS. That is deliberate: the marks are
# what the battery scores, so they must be welded on.
#
# view, wardrobe and backdrop are named in every caption in every arm, identically
# formatted, so no arm gets a caption advantage.
CAPTIONS = {
    "01_window_3q":       ("three quarter view facing left", "mustard corduroy jacket, white t-shirt", "plain pale grey wall, soft window daylight"),
    "02_front_flat":      ("front view", "mustard corduroy jacket, white t-shirt", "plain white wall, flat indoor light"),
    "03_profile":         ("side profile facing left", "grey marl ribbed wool sweater", "plain pale wall, soft daylight"),
    "04_3q_right":        ("three quarter view facing right", "grey marl ribbed wool sweater", "plain pale wall, soft daylight"),
    "05_kitchen_busy":    ("waist up, candid", "mustard corduroy jacket, white t-shirt", "cluttered domestic kitchen, warm ceiling light"),
    "06_outdoor_overcast": ("waist up, front view", "mustard corduroy jacket, white t-shirt", "outdoors, blurred hedge, flat overcast light"),
    "07_outdoor_sun_full": ("full body, standing", "navy and white striped shirt", "outdoors, hard midday sunlight, harsh shadows"),
    "08_fullbody_plain":  ("full body, standing, front view", "grey marl ribbed wool sweater", "plain pale grey wall, soft even light"),
    "09_seated_cafe":     ("seated, waist up, candid", "navy and white striped shirt", "cafe table, coffee cup, window light"),
    "10_selfie_wide":     ("selfie, wide angle lens", "mustard corduroy jacket, white t-shirt", "indoors, close arm length framing"),
    "11_off_axis_dim":    ("head turned away, tilted framing", "grey marl ribbed wool sweater", "dim indoor room, low light"),
    "12_mixed_light":     ("waist up", "mustard corduroy jacket, white t-shirt", "living room at dusk, warm lamp and cool window, mixed light"),
    "13_over_shoulder":   ("looking back over the shoulder, from behind", "navy and white striped shirt", "plain wall, soft light"),
    "14_no_glasses":      ("front view, glasses removed and held in one hand", "grey marl ribbed wool sweater", "plain wall, soft light"),
    "15_hair_up":         ("front view, hair tied back in a low ponytail", "navy and white striped shirt", "plain wall, soft light"),
    "16_laughing":        ("laughing, eyes closed, head tipped back", "mustard corduroy jacket, white t-shirt", "plain wall, soft light"),
}
NARROW_CAPTION = ("front view", "mustard corduroy jacket, white t-shirt",
                  "plain white wall, flat indoor light")

# ---------------------------------------------------------------- the arms
GOOD8 = ["01_window_3q", "02_front_flat", "03_profile", "04_3q_right",
         "06_outdoor_overcast", "08_fullbody_plain", "13_over_shoulder", "16_laughing"]
# The four are chosen for MAXIMUM spread inside the eight: three-quarter left, full
# profile, an outdoor waist-up and a from-behind - and all three outfits appear.
GOOD4 = ["01_window_3q", "03_profile", "06_outdoor_overcast", "13_over_shoulder"]
BAD8 = ["05_kitchen_busy", "07_outdoor_sun_full", "09_seated_cafe", "10_selfie_wide",
        "11_off_axis_dim", "12_mixed_light", "14_no_glasses", "15_hair_up"]

ARMS = {
    "n4":       dict(kind="set", ids=GOOD4,          note="4 varied"),
    "n8":       dict(kind="set", ids=GOOD8,          note="8 varied"),
    "n16":      dict(kind="set", ids=GOOD8 + BAD8,   note="16, the whole set"),
    "n8bad":    dict(kind="set", ids=BAD8,           note="8 poor/awkward, fixed-count quality control"),
    "n8narrow": dict(kind="narrow", ids=None,        note="8 near-identical fronts, fixed-count spread control"),
}
ARM_ORDER = ["n4", "n8", "n16", "n8bad", "n8narrow"]

STEPS, RANK, LR, TSEED = 1000, 16, 0.0005, 7311
TRAIN_W, TRAIN_H = 832, 1216      # one SDXL portrait bucket for every arm

# ---------------------------------------------------------------- the battery
# Every place and every garment below is absent from every training set, in every arm.
# That is the whole design: obedience is measurable only where the training set is silent.
Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG = ("1boy, male focus, masculine, beard, facial hair, lowres, worst quality, "
       "bad anatomy, bad hands, extra limbs, watermark, signature, text, multiple views, "
       "photorealistic, 3d, western comic, monochrome")

STYLES = {
    "anime": "anime screencap, clean cel shading, crisp lineart",
    "water": ("watercolor (medium), traditional media, soft washes of colour, visible "
              "paper grain, muted palette, loose ink linework"),
}

# id, style, w, h, subject-and-place, requested garment (never in training)
BATTERY = [
    ("neon_anime",  "anime", 1024, 1024,
     "standing on a rainy city street at night, neon signs, wet asphalt reflections, "
     "crowd behind her, looking at the viewer, upper body", "black leather biker jacket"),
    ("neon_water",  "water", 1024, 1024,
     "standing on a rainy city street at night, neon signs, wet asphalt reflections, "
     "crowd behind her, looking at the viewer, upper body", "black leather biker jacket"),
    ("libry_anime", "anime", 832, 1216,
     "in a tall wooden library, reaching up to a high shelf, full body, side lit by a "
     "reading lamp", "red hooded raincoat"),
    ("libry_water", "water", 832, 1216,
     "in a tall wooden library, reaching up to a high shelf, full body, side lit by a "
     "reading lamp", "red hooded raincoat"),
    ("wheat_anime", "anime", 832, 1216,
     "standing in a wheat field at sunset, big sky, wind, full body, looking at the "
     "viewer", "green knitted scarf, denim overalls"),
    ("wheat_water", "water", 832, 1216,
     "standing in a wheat field at sunset, big sky, wind, full body, looking at the "
     "viewer", "green knitted scarf, denim overalls"),
    # The face cell. A face is a pixel problem, so it is framed close and the marks are
    # not asked for in the prompt - if they appear, they came from the weights.
    ("face_anime",  "anime", 1024, 1024,
     "close-up portrait, head and shoulders, snowy mountain pass behind her, cold light, "
     "looking at the viewer", ""),
    # The 3D-source cell. This is the frame the mesher would eat, so it is scored on the
    # sculpt rules: A-pose, arms clear, flat light, plain ground.
    ("apose_anime", "anime", 832, 1216,
     "standing A-pose, full body, arms held out away from the body, hands closed, feet "
     "apart, facing the viewer, flat even shadowless light, plain flat grey background, "
     "simple background", "plain grey t-shirt and trousers"),
    # --- the two cells below were added after LOOKING at the first battery. ---
    # face_anime turned out to be a DUD CELL, and it failed identically for the no-LoRA
    # control and for IPAdapter as well as for all five LoRAs: "snowy mountain pass, cold
    # light" is a strong enough colour instruction on animagine that every arm returned a
    # white-haired blue-eyed ice character. A cell that fails for the controls is
    # measuring the prompt, not the arms. It is kept on disk as evidence and is not
    # scored. These replace it with a close framing that names no colour and no weather.
    ("faceb_anime", "anime", 1024, 1024,
     "close-up portrait, head and shoulders, indoors against a plain pale wall, soft "
     "window daylight, looking at the viewer, neutral expression", "grey t-shirt"),
    ("faceb_water", "water", 1024, 1024,
     "close-up portrait, head and shoulders, indoors against a plain pale wall, soft "
     "window daylight, looking at the viewer, neutral expression", "grey t-shirt"),
]

# Cells that need a negative the others must not get. apose_anime came back as a flat
# BLACK SILHOUETTE for the no-LoRA control and for two of the five LoRAs - animagine
# reads "flat shadowless light, plain flat grey background" as a backlit poster. A
# silhouette is worthless as a mesher source, and it is not the LoRA doing it, so the
# fixed version says so in the negative rather than being scored as a LoRA failure.
EXTRA_NEG = {
    "apose2_anime": "silhouette, backlit, dark figure, shadow figure, black shape",
}
BATTERY.append(
    ("apose2_anime", "anime", 832, 1216,
     "standing A-pose, full body, arms held out away from the body, hands closed, feet "
     "apart, facing the viewer, evenly lit from the front, face clearly visible, full "
     "colour, plain flat grey background, simple background",
     "plain grey t-shirt and trousers"))
BSEEDS = [4401, 9902]
LORA_STRENGTH = 0.8
IPA_WEIGHTS = [0.0, 0.3, 0.5, 0.7, 0.9, 1.1]
IPA_REF = "standin_count_ref.png"      # ONE photograph, the flat front shot


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def _fetch(outs, dest):
    if not outs:
        return None
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    return ensure_local(outs[0], dest, required=False)


# ---------------------------------------------------------------- narrow arm generation

def ref2i(prose, seed, w, h, tag, sub, r1, r2):
    wf = load_wf("14_qwen_edit_ref.json")
    set_path(wf, "8.inputs.image", r1)
    set_path(wf, "9.inputs.image", r2)
    set_path(wf, "10.inputs.image2", ["9", 0])
    set_path(wf, "11.inputs.image2", ["9", 0])
    set_path(wf, "10.inputs.prompt", prose)
    set_path(wf, "11.inputs.prompt", NEG_PHOTO)
    set_path(wf, "20.inputs.width", w)
    set_path(wf, "20.inputs.height", h)
    set_path(wf, "13.inputs.seed", seed)
    set_path(wf, "7.inputs.strength_model", 0.0)
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/count/%s/%s" % (sub, tag))
    _, outs = run(HOST, wf, quiet=True)
    return _fetch(outs, os.path.join(WORK, sub, tag + ".png"))


def stage_narrow():
    """Eight shots of one person that a careless friend would send you: the same selfie
    eight times. Built through the same reference-locked edit path the sixteen were, so
    the only difference between this arm and the varied arm is the variety."""
    d = os.path.join(OUT, "narrow")
    os.makedirs(d, exist_ok=True)
    paths, labels = [], []
    for i, seed in enumerate(NARROW_SEEDS):
        tag = "narrow_%02d" % (i + 1)
        prose = ("The woman in image 1. %s. She wears %s. %s Keep her face, her thin "
                 "round gold wire-frame glasses, the small mole on her right cheek, her "
                 "gold stud earrings and her hair exactly as in image 1."
                 % (NARROW_PROSE[0].upper() + NARROW_PROSE[1:], WEAR_A, SNAP))
        print("  narrow %s seed %d" % (tag, seed), flush=True)
        p = ref2i(prose, seed, 1024, 1280, tag, "narrow",
                  "standin_anchor_face.png", "standin_anchor_body.png")
        if p:
            dst = os.path.join(d, tag + ".png")
            shutil.copy(p, dst)
            paths.append(dst)
            labels.append("%s s%d" % (tag, seed))
    sheet(paths, labels, os.path.join(OUT, "contact", "narrow_arm.jpg"), 4, 420, 525)
    print("\nLOOK. These must be near-identical AND must be her. If the seeds have moved "
          "the framing or the light, this arm is not narrow and the spread test is void.")


# ---------------------------------------------------------------- datasets

def prep(src, dst):
    """Cover-crop to one SDXL portrait bucket, anchored high so the head survives.

    Every arm goes through this identically. The alternative - letting the node bucket
    mixed aspect ratios - would have made the full-body shots and the landscape duds
    train at different resolutions from the portraits, which is a second variable inside
    the arm that is supposed to isolate variety."""
    from PIL import Image
    im = Image.open(src).convert("RGB")
    w, h = im.size
    tr = TRAIN_W / float(TRAIN_H)
    if w / float(h) > tr:                       # too wide: crop width, centred
        nw = int(round(h * tr))
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:                                       # too tall: crop height, anchored HIGH
        nh = int(round(w / tr))
        top = int(round((h - nh) * 0.12))
        im = im.crop((0, top, w, top + nh))
    im.resize((TRAIN_W, TRAIN_H), Image.LANCZOS).save(dst)


def cap(view, wear, back):
    return ", ".join([TRIGGER, view, wear, back])


def stage_datasets():
    made = {}
    for arm in ARM_ORDER:
        spec = ARMS[arm]
        d = os.path.join(COMFY_IN, "cnt_" + arm)
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)
        n = 0
        if spec["kind"] == "set":
            for sid in spec["ids"]:
                src = os.path.join(STANDIN, "set", sid + ".png")
                if not os.path.exists(src):
                    raise SystemExit("missing %s" % src)
                prep(src, os.path.join(d, sid + ".png"))
                open(os.path.join(d, sid + ".txt"), "w", encoding="utf-8").write(
                    cap(*CAPTIONS[sid]) + "\n")
                n += 1
        else:
            src_d = os.path.join(OUT, "narrow")
            files = sorted(f for f in os.listdir(src_d) if f.endswith(".png"))
            if len(files) != 8:
                raise SystemExit("narrow arm has %d images, need 8 - run --stage narrow"
                                 % len(files))
            for f in files:
                prep(os.path.join(src_d, f), os.path.join(d, f))
                open(os.path.join(d, f[:-4] + ".txt"), "w", encoding="utf-8").write(
                    cap(*NARROW_CAPTION) + "\n")
                n += 1
        made[arm] = n
        print("  cnt_%-9s %2d pairs  %s" % (arm, n, spec["note"]))
    # the one photograph the zero-training arm gets
    shutil.copy(os.path.join(STANDIN, "set", "02_front_flat.png"),
                os.path.join(COMFY_IN, IPA_REF))
    print("  ipadapter reference -> ComfyUI/input/%s (02_front_flat, ONE photo)" % IPA_REF)
    json.dump(made, open(os.path.join(OUT, "datasets.json"), "w"), indent=2)


# ---------------------------------------------------------------- training

def stage_train(arms):
    os.makedirs(OUT, exist_ok=True)
    log = os.path.join(OUT, "train_log.json")
    rec = json.load(open(log)) if os.path.exists(log) else {}
    for arm in arms:
        folder = "cnt_" + arm
        d = os.path.join(COMFY_IN, folder)
        pairs = len([f for f in os.listdir(d) if f.endswith(".png")])
        wf = load_wf("33_train_character_lora.json")
        set_path(wf, "1.inputs.folder", folder)
        set_path(wf, "5.inputs.steps", STEPS)
        set_path(wf, "5.inputs.rank", RANK)
        set_path(wf, "5.inputs.learning_rate", LR)
        set_path(wf, "5.inputs.seed", TSEED)
        set_path(wf, "6.inputs.prefix", "loras/count_%s" % arm)
        print("\n%s : %d images, %d steps, rank %d, lr %s, seed %d"
              % (arm, pairs, STEPS, RANK, LR, TSEED), flush=True)
        t0 = time.time()
        pid = submit(wf)
        while True:
            time.sleep(15)
            try:
                with urllib.request.urlopen("http://%s/history/%s" % (HOST, pid),
                                            timeout=20) as r:
                    h = json.load(r) or {}
            except Exception:
                continue
            if pid in h:
                st = h[pid].get("status", {}).get("status_str")
                mins = (time.time() - t0) / 60
                print("  %s after %.1f min" % (st, mins), flush=True)
                break
            print("  ... %.0f min" % ((time.time() - t0) / 60), flush=True)
        src_d = os.path.join(COMFY, "output", "loras")
        moved = None
        for f in sorted(os.listdir(src_d)) if os.path.isdir(src_d) else []:
            if f.startswith("count_%s" % arm) and f.endswith(".safetensors"):
                dst = "count_%s.safetensors" % arm
                sh("mv", os.path.join(src_d, f), os.path.join(LORA_DIR, dst))
                moved = dst
        if not moved:
            print("  ! nothing came out of training for %s" % arm)
        else:
            print("  -> models/loras/%s" % moved)
        rec[arm] = dict(images=pairs, steps=STEPS, rank=RANK, lr=LR,
                        minutes=round(mins, 1), lora=moved)
        json.dump(rec, open(log, "w"), indent=2)


# ---------------------------------------------------------------- rendering

def positive(cell, arm):
    cid, style, w, h, place, wear = cell
    bits = ["1girl, solo"]
    # The trigger is a LoRA word. The no-LoRA control and the IPAdapter arm must NOT get
    # it: an untrained token in an SDXL prompt is not neutral, it tokenises into junk
    # subwords and steers the render, which would make both zero-training arms look worse
    # for a reason that has nothing to do with the question.
    if arm not in ("base_noref", "ipa"):
        bits.insert(0, TRIGGER)
    bits.append(STYLES[style])
    if wear:
        bits.append(wear)
    bits.append(place)
    bits.append(Q)
    return ", ".join(bits)


def build(cell, arm, lora, strength, seed, ipa_weight):
    cid, style, w, h, place, wear = cell
    wf = load_wf("22_anime_kf_ipadapter.json")
    set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
    set_path(wf, "2.inputs.image", IPA_REF)
    set_path(wf, "4.inputs.weight", float(ipa_weight))
    set_path(wf, "5.inputs.text", positive(cell, arm))
    extra = EXTRA_NEG.get(cid)
    set_path(wf, "6.inputs.text", (NEG + ", " + extra) if extra else NEG)
    set_path(wf, "8.inputs.seed", seed)
    set_path(wf, "7.inputs.width", w)
    set_path(wf, "7.inputs.height", h)
    set_path(wf, "10.inputs.width", w)
    set_path(wf, "10.inputs.height", h)
    if lora and strength > 0:
        wf["90"] = {"class_type": "LoraLoaderModelOnly",
                    "inputs": {"model": ["1", 0], "lora_name": lora,
                               "strength_model": float(strength)}}
        # IPAdapterUnifiedLoader takes the model; rewire everything that read node 1
        for nid, node in list(wf.items()):
            if nid in ("1", "90") or not isinstance(node, dict):
                continue
            for k, v in (node.get("inputs") or {}).items():
                if isinstance(v, list) and len(v) == 2 and v[0] == "1" and v[1] == 0:
                    node["inputs"][k] = ["90", 0]
    return wf


def render(cell, arm, lora, strength, seed, ipa_weight, sub, tag):
    wf = build(cell, arm, lora, strength, seed, ipa_weight)
    set_path(wf, "11.inputs.filename_prefix", "claude-generated/count/%s/%s" % (sub, tag))
    _, outs = run(HOST, wf, quiet=True)
    return _fetch(outs, os.path.join(WORK, sub, tag + ".png"))


def stage_battery(arms, ipa_weight):
    for arm in arms:
        lora = None if arm in ("base", "ipa") else "count_%s.safetensors" % arm
        if lora and not os.path.exists(os.path.join(LORA_DIR, lora)):
            print("  ! no lora for %s, skipping" % arm)
            continue
        w = float(ipa_weight) if arm == "ipa" else 0.0
        d = os.path.join(OUT, "battery", arm)
        os.makedirs(d, exist_ok=True)
        for cell in BATTERY:
            for si, seed in enumerate(BSEEDS):
                tag = "%s__%s__s%d" % (arm, cell[0], si)
                dst = os.path.join(d, "%s_s%d.png" % (cell[0], si))
                if os.path.exists(dst):
                    continue
                p = render(cell, arm if arm != "base" else "base_noref",
                           lora, LORA_STRENGTH, seed, w, "battery", tag)
                if p:
                    shutil.copy(p, dst)
                    print("  %-9s %-12s s%d ok" % (arm, cell[0], si), flush=True)
                else:
                    print("  %-9s %-12s s%d FAILED" % (arm, cell[0], si), flush=True)


def stage_ipa():
    """The zero-training arm needs an operating point before it can be compared to
    anything, and the band has never been measured on this box. Two cells - one anime,
    one watercolour - because the whole tension is that a reference SUPPRESSES STYLE, and
    that shows on the style axis, not the identity axis."""
    d = os.path.join(OUT, "ipa_sweep")
    os.makedirs(d, exist_ok=True)
    for cell in (BATTERY[0], BATTERY[5], BATTERY[6]):
        paths, labels = [], []
        for w in IPA_WEIGHTS:
            tag = "ipa_%s_w%s" % (cell[0], str(w).replace(".", ""))
            p = render(cell, "base_noref", None, 0.0, BSEEDS[0], w, "ipa", tag)
            if p:
                dst = os.path.join(d, tag + ".png")
                shutil.copy(p, dst)
                paths.append(dst)
                labels.append("IPA %.1f" % w)
                print("  %-12s weight %.1f ok" % (cell[0], w), flush=True)
        sheet(paths, labels, os.path.join(OUT, "contact", "ipa_%s.jpg" % cell[0]),
              len(IPA_WEIGHTS), 400, 480)
    print("\nLOOK. Left to right the face should arrive and the style should leave. The "
          "usable band is the columns where BOTH are still true.")


def stage_strength(arms, cell_id="faceb_anime", seeds=(BSEEDS[1],)):
    """NOT a sanity arm any more - a required one.

    The battery holds LoRA strength at 0.80 for every arm so the columns are comparable.
    Looking at it showed that 0.80 is SEED-FRAGILE: on seed 4401 the close-face cell came
    back as her in four of five arms, and on seed 9902 the same four arms returned a
    BLONDE woman with no glasses. An identity that survives one seed and not the next is
    not an identity, and a count conclusion drawn at a single strength would be measuring
    that fragility rather than the dataset.

    So this sweeps strength on the hostile seed. If the arms separate the same way at
    every strength, the count result stands; if the ordering changes with strength, the
    honest answer is that strength and count trade off and both have to be reported."""
    d = os.path.join(OUT, "strength")
    os.makedirs(d, exist_ok=True)
    cell = [c for c in BATTERY if c[0] == cell_id][0]
    for arm in arms:
        lora = "count_%s.safetensors" % arm
        paths, labels = [], []
        for st in (0.4, 0.6, 0.8, 1.0):
            for seed in seeds:
                tag = "st_%s_%s_%d" % (arm, str(st).replace(".", ""), seed)
                p = render(cell, arm, lora, st, seed, 0.0, "strength", tag)
                if p:
                    dst = os.path.join(d, tag + ".png")
                    shutil.copy(p, dst)
                    paths.append(dst)
                    labels.append("%s @ %.1f" % (arm, st))
                    print("  %-9s strength %.1f seed %d ok" % (arm, st, seed), flush=True)
        sheet(paths, labels, os.path.join(OUT, "contact", "strength_%s.jpg" % arm),
              4 * len(seeds), 620, 620)


# ---------------------------------------------------------------- sheets

def sheet(paths, labels, dst, cols, cw=480, ch=640):
    """Contact sheet with the cell count ASSERTED from the output pixels.

    tile= is a single-stream filter: handing ffmpeg N separate -i files and one tile=
    consumes input 0 and silently emits a sheet of black cells. So cells are written as a
    numbered SEQUENCE and read back through the image2 demuxer. tile= also drops cells of
    differing size, so every cell is scaled AND padded to exactly cw x ch first, and the
    grid is filled out to a whole rectangle. None of that is visible in the output, so
    the finished image is measured against the grid arithmetic and this raises if it is
    short."""
    if not paths:
        return None
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = os.path.join(WORK, "_sheet")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    n = 0
    for p, lab in zip(paths, labels):
        c = os.path.join(tmp, "cell_%03d.png" % n)
        sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
           "scale=%d:%d:force_original_aspect_ratio=decrease,"
           "pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=0x101010,"
           "drawtext=text='%s':fontcolor=yellow:fontsize=22:x=8:y=8:"
           "box=1:boxcolor=black@0.85:boxborderw=5"
           % (cw, ch, cw, ch, lab.replace(":", "\\:").replace("'", "")), c)
        if os.path.exists(c):
            n += 1
        else:
            print("  cell failed for %s" % p)
    real = n
    rows = (n + cols - 1) // cols
    while n < rows * cols:
        sh("ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
           "color=c=0x101010:s=%dx%d" % (cw, ch), "-frames:v", "1",
           os.path.join(tmp, "cell_%03d.png" % n))
        n += 1
    m, pad = 8, 8
    sh("ffmpeg", "-y", "-v", "error", "-framerate", "1", "-start_number", "0",
       "-i", os.path.join(tmp, "cell_%03d.png"),
       "-vf", "tile=%dx%d:margin=%d:padding=%d:color=0x101010" % (cols, rows, m, pad),
       "-frames:v", "1", "-q:v", "3", dst)
    if not os.path.exists(dst):
        raise SystemExit("contact sheet failed: %s" % dst)
    want = "%d,%d" % (cols * cw + (cols - 1) * pad + 2 * m,
                      rows * ch + (rows - 1) * pad + 2 * m)
    got = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height", "-of", "csv=p=0", dst).stdout.strip()
    if got != want:
        raise SystemExit("sheet %s is %s but the %dx%d grid must be %s - cells dropped"
                         % (dst, got, cols, rows, want))
    print("  sheet %s  (%d real cells, %s px - verified)" % (dst, real, got))
    return dst


def stage_sheets(arm_cols):
    """ONE SHEET PER BATTERY CELL, one column per arm. That is the only layout in which
    the question can actually be answered by looking: the seed, the prompt, the style and
    the place are identical across the row and the ONLY thing that changes left to right
    is how many photographs went in."""
    for cell in BATTERY:
        for si in range(len(BSEEDS)):
            paths, labels = [], []
            for arm in arm_cols:
                p = os.path.join(OUT, "battery", arm, "%s_s%d.png" % (cell[0], si))
                if os.path.exists(p):
                    paths.append(p)
                    labels.append("%s %s" % (arm, ARMS.get(arm, {}).get("note", "")[:18]))
            if paths:
                # The face cells are scored on a wire spectacle frame and a mole. At the
                # 430px cell the rest of the battery uses, neither is resolvable and the
                # sheet would be decorative rather than evidence.
                big = cell[0].startswith("face")
                sheet(paths, labels,
                      os.path.join(OUT, "contact", "cell_%s_s%d.jpg" % (cell[0], si)),
                      len(paths), 700 if big else 430, 700 if big else 520)


def stage_report():
    """The verdicts below were set BY LOOKING at the sheets this tool wrote, one cell at
    a time, and they are scored on the stand-in's concrete marks rather than on any
    embedding. The scoring column that decides everything is `glasses_at`: the lowest LoRA
    strength at which the thin round gold spectacle frame appears on the close-face cell.
    It is the one mark that is unambiguous at a glance, it is never asked for in any
    battery prompt, and it is absent from the no-LoRA control - so when it appears it came
    out of the weights and nowhere else."""
    r = {
        "question": "how many photographs does a character need",
        "subject": "STANDIN-A, synthetic, studio/samples/photo2anime/standin",
        "engine": "animagine-xl-4.0 (SDXL). LoRAs trained on PHOTOGRAPHS, rendered as anime.",
        "held_constant": {"steps": STEPS, "rank": RANK, "lr": LR, "seed": TSEED,
                          "train_res": "%dx%d" % (TRAIN_W, TRAIN_H),
                          "minutes_each": "10.0 - 13.8",
                          "battery_strength": LORA_STRENGTH,
                          "captions": "trigger, view, wardrobe, backdrop - identical form in every arm"},
        "arms": {k: ARMS[k]["note"] for k in ARM_ORDER},
        "battery": "%d cells x %d seeds x 7 arms" % (len(BATTERY), len(BSEEDS)),
        "verdicts": {
            "n4": {"glasses_at": 0.8, "anime_survives_at_that_strength": True,
                   "face": "adult, ordinary, hers", "note":
                   "identical to n8 on the close-face cell. Weaker on the medium shots."},
            "n8": {"glasses_at": 0.8, "anime_survives_at_that_strength": True,
                   "face": "adult, ordinary, hers", "note": "the knee. Cheapest arm that is fully hers."},
            "n16": {"glasses_at": 0.8, "anime_survives_at_that_strength": True,
                    "face": "adult, ordinary, hers - the most consistent across cells",
                    "note": "better than n8 only in robustness across seeds and scenes."},
            "n8bad": {"glasses_at": 0.8, "anime_survives_at_that_strength": False,
                      "face": "young, idealised, NOT her age or build",
                      "note": "same count as n8, poor sources. Marks arrive, the person does not."},
            "n8narrow": {"glasses_at": 1.0, "anime_survives_at_that_strength": False,
                         "face": "generic young anime girl, not her",
                         "note": "THE RESULT. Same count as n8, same steps, more close "
                                 "face pixels than any other arm, and it never becomes her."},
            "ipa_zero_training": {"band": "0.5 - 0.7", "glasses_at": "0.5-0.7 (scene-dependent)",
                                  "note": "marks transfer, the person does not. At 0.9+ the "
                                          "reference photo's white wall replaces the scene "
                                          "and the composition breaks."},
        },
        "dud_cells_kept_as_evidence": {
            "face_anime": "failed identically for the no-LoRA control and for IPAdapter - "
                          "the prompt, not the arms. Replaced by faceb_anime/faceb_water.",
            "apose_anime": "black silhouette for the control and 2 of 5 LoRAs. Replaced by "
                           "apose2_anime with a silhouette negative.",
        },
        "answers": {
            "printable_figurine": 4,
            "usable_film_character": 8,
            "diminishing_returns_after": 8,
            "vary_in": ["angle - front, both three-quarters, full profile, from behind",
                        "distance - at least one full body and one close head-and-shoulders",
                        "light - window, flat indoor, outdoor overcast",
                        "outfit - AT LEAST TWO, or the trigger absorbs the clothes"],
            "count_is_the_wrong_axis": "8 narrow beat by 4 varied. Spread dominates count.",
        },
    }
    p = os.path.join(OUT, "RESULTS.json")
    json.dump(r, open(p, "w", encoding="utf-8"), indent=2)
    print(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["narrow", "datasets", "train", "battery", "ipa",
                             "strength", "sheets", "report"])
    ap.add_argument("--arm", nargs="+")
    ap.add_argument("--ipa-weight", type=float, default=0.7)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    if a.stage == "narrow":
        stage_narrow()
    elif a.stage == "datasets":
        stage_datasets()
    elif a.stage == "train":
        stage_train(a.arm or ARM_ORDER)
    elif a.stage == "battery":
        stage_battery(a.arm or (["base", "ipa"] + ARM_ORDER), a.ipa_weight)
    elif a.stage == "ipa":
        stage_ipa()
    elif a.stage == "strength":
        stage_strength(a.arm or ARM_ORDER)
    elif a.stage == "sheets":
        stage_sheets(a.arm or (["base", "ipa"] + ARM_ORDER))
    elif a.stage == "report":
        stage_report()


if __name__ == "__main__":
    main()
