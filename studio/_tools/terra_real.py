#!/usr/bin/env python3
"""Make a photoreal reference sheet that reads as a PHOTOGRAPH OF A PERSON, not a render.

WHY THIS TOOL EXISTS. The user has twice said TERRA's realistic version is not good enough.
Her card already contains the right diagnosis of the FRAMING problem (a face rendered at 90
pixels stays a 90-pixel face) and the right diagnosis of the SHEET problem (a body-only
sheet loses the face, a face-only sheet loses the costume, the composite keeps both). Both
are fixed. She still looks like a render. So the remaining fault is somewhere else, and the
place nobody has looked is INSIDE THE SHEET ITSELF.

THE OBSERVATION THAT STARTED THIS. studio/samples/cast/terra_photo_face.jpg has four arms.
Arms B and C go through the sheet and produce smooth, waxy, poreless skin. Arm D was the
control - a close portrait with NO sheet at all - and it is the only cell in the strip that
looks like a photograph: pores, stray hairs, an ordinary asymmetric face. The card reads D
as a failure because it is a different woman. It is also the best PHOTOGRAPH in the strip,
and that half of the result was never acted on.

That gives the hypothesis this tool tests: THE SHEET TRANSMITS ITS SURFACE, NOT JUST ITS
IDENTITY AND ITS MEDIUM. The current sheet was itself made through the edit path and is
smooth, so everything conditioned on it is smooth. If that is true, the fix is not a better
prompt downstream - it is a sheet whose face panel was made on the t2i path, where the skin
is real, and then never smoothed.

WHAT IS ALREADY MEASURED AND IS NOT RE-DERIVED HERE:
  - close framing beats everything else for face quality (photo_face_verdict)
  - Lightning off at 20 steps is marginal for 7x the cost (photo_face_verdict)
  - the sheet pins the MEDIUM as hard as the identity (realism_verdict)
  - a composite face+body sheet beats either panel alone (sheet_photo_note)
  - the character LoRA is animagine-locked and does nothing on qwen (sheet_photo_note)

WHAT THIS SWEEPS, none of which has been tried:
  hair       five treatments of green, because green hair is the single hardest thing here
             to make read as hair rather than as a wig
  light/lens six, from soft window through hard single-source to backlit low sun
  grade      five stock and grade languages
  expression six, because every photoreal render of her so far is a dead frontal stare and
             that alone may be most of why they read as lifeless
  sheets     SEVERAL composite sheets from DIFFERENT base portraits, not one
  negative   the workflow default negative on the edit path contains the words
             "photorealistic, 3d render" and scripts/short.py never overwrites it. Every
             reference keyframe this project has ever rendered has been asking the sampler
             NOT to be photographic. That is measured here as its own arm rather than
             assumed.

THE ONE THING THAT MAKES A SHEET INTERNALLY CONSISTENT. The current composite is two
independently generated women hstacked together - look at the jaw. The body panel here is
generated FROM the chosen face panel through the edit path, so both halves are one person
by construction.

STAGES, each its own subcommand, each writing a contact sheet that has to be LOOKED AT:

  portraits   hair x light, one seed          -> pick a hair and two or three lights
  moods       grade x expression at a winner  -> pick the grade and the gaze
  finals      the chosen combinations x seeds -> the candidate base portraits
  bodies      costume panels generated FROM each base portrait (one person, guaranteed)
  sheets      composite each face+body into a candidate sheet
  probe       every candidate sheet through the real downstream path, plus the negative
              arm and a no-sheet control, which is the only test that matters
  facepass    face-detail pass with a paste-back that is checked at 1:1
  install     write the winner into TERRA.json - photo and realism fields ONLY

Nothing runs at import. Every stage needs an explicit subcommand; handing this file --help
prints help and renders nothing, which is not true of 17 other tools in this directory.

    python3 studio/_tools/terra_real.py portraits
    python3 studio/_tools/terra_real.py sheets --pairs a1:b1,a2:b2
    python3 studio/_tools/terra_real.py probe --sheets cand_a,cand_b
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request

ROOT = os.path.expanduser("~/shared/comfy-studio")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import set_path                                    # noqa: E402
from epic import load_wf, ensure_local, submit, wait_all, HOST  # noqa: E402

from PIL import Image, ImageStat                              # noqa: E402

COMFY_IN = os.path.expanduser("~/ComfyUI/input")
OUT = os.path.join(ROOT, "studio", "samples", "cast", "terra_real")
WORK = "/tmp/terra_real"
PREFIX = "claude-generated/terra_real"

T2I = "13_qwen_t2i_styled.json"
REF = "14_qwen_edit_ref.json"

SEED = 4242

# ── vocabulary ───────────────────────────────────────────────────────────────
#
# IDENT is held constant across every cell so the sweep is about treatment and not about
# who turned up. It is deliberately close to the face already in sheet_photo_terra.png -
# this is meant to be a better photograph of the same woman, not a recast.
IDENT = ("a young woman in her early twenties, oval face with a soft jaw, straight nose, "
         "wide-set grey-green eyes under level dark brows, pale skin")

# The realism nouns. Adjectives like "photorealistic" do nothing; a pore is a thing that
# can be drawn. This tail is on every cell in the sweep.
TAIL = ("Visible skin pores and fine facial down along the jaw, a few flyaway hairs lit "
        "from behind, a catchlight in both eyes, natural asymmetry between the two sides "
        "of the face, unretouched, no makeup, 35mm colour negative grain.")

# The negative a photograph actually wants. The workflow default on the edit path negates
# "photorealistic, 3d render", which on a photoreal job is fighting the brief.
NEG_PHOTO = ("cgi, 3d render, digital painting, illustration, anime, cartoon, smooth "
             "plastic skin, airbrushed, beauty retouching, doll, mannequin, wig, cosplay, "
             "costume party, flat frontal flash, studio strobe, oversaturated, watermark, "
             "text, extra fingers, deformed hands")

HAIR = {
    "roots": "Her hair is dyed a deep forest green and grown out, with two inches of dark "
             "brown roots showing at the parting.",
    "faded": "Her hair is green dye faded down to a dry sage, warmer and lighter at the "
             "ends where it has lifted, the colour clearly months old.",
    "nearblack": "Her hair is so dark a green it reads black in the shadow and only shows "
                 "its colour where the light strikes it directly.",
    "subtle": "Her hair is dark brown with a green cast that only appears in the "
              "highlights, easy to miss indoors.",
    "saturated": "Her hair is a saturated deep green, long and loose.",
}

LIGHT = {
    "win85": "85mm at f/2. Soft north window light from camera-left, deep falloff into the "
             "shadow side of the face.",
    "comp135": "135mm at f/2.8, long-lens compression, background thrown far out of focus. "
               "Flat overcast daylight, even and slightly cool.",
    "hard50": "50mm at f/1.8. One hard source high and camera-right, a crisp shadow edge "
              "running down the cheek, the rest of the frame falling to black.",
    "lowsun": "85mm at f/2, backlit by a low evening sun that rims the hair and blows out "
              "behind her, a weak bounce filling the face from below.",
    "practical": "50mm at f/1.4, lit only by a practical lamp just out of frame at her eye "
                 "level, warm falloff, everything past her going dark.",
    "env35": "35mm at f/2.8. She is off-centre and the room is in the shot, daylight "
             "arriving from a doorway behind her.",
}

GRADE = {
    "portra": "Shot on Kodak Portra 400. Warm skin, low contrast, gentle grain.",
    "cinestill": "Shot on CineStill 800T. Cool tungsten cast, red halation blooming around "
                 "the highlights, coarse grain.",
    "bleach": "Bleach bypass. Desaturated, hard blacks, silver in the highlights.",
    "tealorange": "Graded teal in the shadows and orange in the skin, modern digital "
                  "cinema, clean.",
    "ektar": "Shot on Ektachrome. Clean neutral colour, fine grain, high micro-contrast.",
}

EXPR = {
    "offleft": "She is looking off camera-left at something out of frame, lips slightly "
               "parted, mid-thought.",
    "halfsmile": "A small tired half-smile, eyes lowered.",
    "midturn": "Caught mid-turn - her eyes have not arrived at the lens yet and her hair "
               "is still moving.",
    "set": "Jaw set, chin a fraction down, looking straight into the lens, unimpressed.",
    "laugh": "Laughing, eyes creased almost shut, head tipped back a little.",
    "spent": "Exhausted, eyes unfocused somewhere past the camera, mouth slack.",
}

# The wardrobe, in MATERIALS. Named as cloth rather than as colour, which is the fix that
# turned the first cosplay sheet into a costume department (see sheet_photo_verdict).
WARDROBE = ("a heavy raw-silk tabard in faded ochre with a woven red and indigo border, a "
            "soft wool cape in dull carmine pinned at one shoulder, a wide belt of worn "
            "brown leather, and tall scuffed brown boots")

# ── plumbing ─────────────────────────────────────────────────────────────────


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def card():
    with open(os.path.join(ROOT, "studio", "characters", "TERRA.json"), encoding="utf-8") as f:
        return json.load(f)


def t2i_wf(tag, prompt, w, h, seed, neg=None, steps=None, cfg=None):
    wf = load_wf(T2I)
    set_path(wf, "10.inputs.text", prompt)
    set_path(wf, "11.inputs.text", neg if neg is not None else NEG_PHOTO)
    set_path(wf, "12.inputs.width", w)
    set_path(wf, "12.inputs.height", h)
    set_path(wf, "13.inputs.seed", seed)
    if steps:
        set_path(wf, "13.inputs.steps", steps)
    if cfg is not None:
        set_path(wf, "13.inputs.cfg", cfg)
    if steps and steps > 8:
        # Dropping Lightning is the only way more steps buys anything; the 4-step schedule
        # ignores them. Measured as marginal for 7x cost, so this is opt-in only.
        set_path(wf, "4.inputs.strength_model", 0.0)
    set_path(wf, "7.inputs.strength_model", 0.0)   # never a style LoRA on a photo job
    set_path(wf, "15.inputs.filename_prefix", "%s/%s" % (PREFIX, tag))
    return wf


def ref_wf(tag, prompt, refs, w, h, seed, neg=None, denoise=1.0, steps=None):
    """The edit path. `refs` are filenames already sitting in ComfyUI/input.

    neg=None keeps the WORKFLOW DEFAULT, which is what scripts/short.py does today and
    which contains the words "photorealistic, 3d render". That is an arm, not an oversight.
    """
    wf = load_wf(REF)
    slots = ["8", "9", "16"]
    for n, name in enumerate(refs[:3], start=1):
        node = slots[n - 1]
        if node not in wf:
            wf[node] = {"class_type": "LoadImage",
                        "inputs": {"image": name, "upload": "image"}}
        set_path(wf, "%s.inputs.image" % node, name)
        for enc in ("10", "11"):
            wf[enc]["inputs"]["image%d" % n] = [node, 0]
    for n in range(len(refs[:3]) + 1, 4):
        for enc in ("10", "11"):
            wf[enc]["inputs"].pop("image%d" % n, None)
    set_path(wf, "10.inputs.prompt", prompt)
    if neg is not None:
        set_path(wf, "11.inputs.prompt", neg)
    set_path(wf, "13.inputs.seed", seed)
    if denoise < 1.0:
        # EDIT mode: the reference becomes the canvas. Node 12 is the VAEEncode of ref 1.
        set_path(wf, "13.inputs.latent_image", ["12", 0])
        set_path(wf, "13.inputs.denoise", denoise)
        # At 4 Lightning steps a denoise of 0.4 buys ONE step, which is nothing. Scale the
        # step count so the pass actually gets iterations to spend.
        set_path(wf, "13.inputs.steps", steps or max(4, int(round(4 / max(denoise, 0.1)))))
    else:
        set_path(wf, "20.inputs.width", w)
        set_path(wf, "20.inputs.height", h)
        if steps:
            set_path(wf, "13.inputs.steps", steps)
    set_path(wf, "7.inputs.strength_model", 0.0)
    set_path(wf, "15.inputs.filename_prefix", "%s/%s" % (PREFIX, tag))
    return wf


def batch(jobs, label):
    """Submit the whole batch, wait once, return {tag: local png path}.

    Submitting up front keeps the queue contiguous so the model loads once - the same
    reason epic.wait_all exists.
    """
    os.makedirs(WORK, exist_ok=True)
    pairs = []
    for tag, wf in jobs:
        pairs.append((tag, submit(wf)))
    wait_all([p for _, p in pairs], label)
    got = {}
    for tag, pid in pairs:
        try:
            h = json.load(urllib.request.urlopen(
                "http://%s/history/%s" % (HOST, pid), timeout=60))
        except Exception:
            continue
        e = h.get(pid) or {}
        for _, out in (e.get("outputs") or {}).items():
            for f in out.get("images", []):
                rel = ("%s/%s" % (f.get("subfolder", ""), f["filename"])).lstrip("/")
                loc = ensure_local(rel, os.path.join(WORK, tag + ".png"), required=False)
                if loc:
                    got[tag] = loc
    return got


def montage(cells, dst, cols, cell_w=460):
    """Labelled contact sheet via ImageMagick.

    NOT ffmpeg tile= with a glob: that silently drops cells when the inputs differ in size,
    and cells here differ in size by design.
    """
    if not cells:
        raise SystemExit("nothing to montage")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    args = ["magick", "montage"]
    for label, path in cells:
        args += ["-label", label, path]
    args += ["-tile", "%dx" % cols, "-geometry", "%dx+5+5" % cell_w,
             "-background", "#111111", "-fill", "#ffe066", "-pointsize", "17", dst]
    r = sh(*args)
    if r.returncode:
        raise SystemExit("montage failed: %s" % r.stderr[-400:])
    print("  wrote %s (%d cells)" % (dst, len(cells)))
    return dst


def stage_ok(got, want):
    miss = [t for t in want if t not in got]
    if miss:
        print("  ! missing %d/%d: %s" % (len(miss), len(want), ", ".join(miss[:8])))


# ── stage: portraits ─────────────────────────────────────────────────────────


# The one prop she carries. Named as a real object with a real material, because the model
# renders nouns: "red hair ribbon" on a photoreal path gets a costume-shop bow, a narrow
# oxblood grosgrain ribbon gets a ribbon. It is the only piece of her anime identity
# vocabulary that has to survive into a photograph, so it is a flag rather than a constant.
RIBBON = ("A narrow oxblood grosgrain ribbon is tied at the crown of her head, its two "
          "ends falling behind her shoulder.")


def face_prompt(hair, light, grade, expr, extra=""):
    return " ".join([LIGHT[light], "A close portrait of " + IDENT + ".", HAIR[hair],
                     EXPR[expr], extra, GRADE[grade], TAIL])


def cmd_portraits(a):
    """hair x light. Everything else pinned. The question is only: which green reads as
    hair and not as a wig, and which light gives a face with a surface."""
    jobs, want = [], []
    for h in HAIR:
        for l in LIGHT:
            tag = "p_%s_%s" % (h, l)
            want.append(tag)
            jobs.append((tag, t2i_wf(tag, face_prompt(h, l, "portra", "offleft"),
                                     1024, 1280, a.seed)))
    got = batch(jobs, "portraits")
    stage_ok(got, want)
    for h in HAIR:
        cells = [("%s / %s" % (h, l), got["p_%s_%s" % (h, l)])
                 for l in LIGHT if "p_%s_%s" % (h, l) in got]
        montage(cells, os.path.join(OUT, "01_portraits_%s.jpg" % h), 3, 620)


def cmd_moods(a):
    """grade x expression at a chosen hair and light. Thirty cells, one seed."""
    jobs, want = [], []
    for g in GRADE:
        for e in EXPR:
            tag = "m_%s_%s" % (g, e)
            want.append(tag)
            jobs.append((tag, t2i_wf(tag, face_prompt(a.hair, a.light, g, e),
                                     1024, 1280, a.seed)))
    got = batch(jobs, "moods")
    stage_ok(got, want)
    for g in GRADE:
        cells = [("%s / %s" % (g, e), got["m_%s_%s" % (g, e)])
                 for e in EXPR if "m_%s_%s" % (g, e) in got]
        montage(cells, os.path.join(OUT, "02_moods_%s.jpg" % g), 3, 620)


def cmd_finals(a):
    """The chosen combinations, each at several seeds. --combo hair:light:grade:expr,..."""
    combos = [c.split(":") for c in a.combos.split(",")]
    seeds = [int(s) for s in a.seeds.split(",")]
    jobs, want = [], []
    extra = RIBBON if a.ribbon else ""
    for h, l, g, e in combos:
        for s in seeds:
            tag = "f_%s_%s_%s_%s_s%d%s" % (h, l, g, e, s, "_rib" if a.ribbon else "")
            want.append(tag)
            jobs.append((tag, t2i_wf(tag, face_prompt(h, l, g, e, extra), 1024, 1280, s)))
    got = batch(jobs, "finals")
    stage_ok(got, want)
    cells = [(t.replace("f_", ""), got[t]) for t in want if t in got]
    montage(cells, os.path.join(OUT, "03_finals.jpg"), len(seeds), 560)
    for t in want:
        if t in got:
            shutil.copy(got[t], os.path.join(COMFY_IN, "tr_%s.png" % t))
    print("  base portraits staged into ComfyUI/input as tr_<tag>.png")


# ── stage: bodies ────────────────────────────────────────────────────────────


def cmd_bodies(a):
    """Costume panels generated FROM each base portrait through the edit path.

    This is the fix for the defect visible in the CURRENT composite sheet: its two panels
    are two independently generated women hstacked together, so the sheet teaches Qwen-Edit
    two different faces. Generating the body from the face makes the sheet one person by
    construction.
    """
    bases = a.bases.split(",")
    # FRAMING IS THE VARIABLE THAT MATTERS IN THIS PANEL. A full-length figure in a large
    # room puts the costume at a fraction of the panel and the head at a fraction of that,
    # and the sheet can only teach what is legible in it. The three-quarter crop is the
    # same wardrobe at roughly twice the linear scale.
    FRAMING = {
        "full": ("A full-length photograph of this exact woman, her whole body in frame "
                 "from the boots up."),
        "threequarter": ("A three-quarter-length photograph of this exact woman, framed "
                         "from mid-thigh up so the garment fills the frame."),
        # MEASURED NEED, not a guess. With a close face panel and a standing-figure panel,
        # a CLOSE downstream shot came back with the wardrobe missing - the collar was
        # only a few pixels tall in the sheet, so there was nothing legible for the edit
        # path to carry into a head-and-shoulders frame. This panel is the missing link
        # between the two scales.
        "bust": ("A head-and-shoulders photograph of this exact woman, framed from the "
                 "top of the chest up so the neckline, the woven collar band and the "
                 "shoulder of the garment are all clearly legible."),
    }
    prompt = ("%s Same face, same hair. She stands three-quarters to camera with her "
              "weight on one hip and one hand at her belt. She wears %s. %s %s Warm grey "
              "seamless behind her." % (FRAMING[a.framing], WARDROBE, LIGHT["win85"], TAIL))
    negarms = (("photoneg", NEG_PHOTO), ("wfneg", None)) if a.negarm else (("photoneg", NEG_PHOTO),)
    jobs, want = [], []
    for b in bases:
        src = "tr_%s.png" % b
        suffix = {"full": "", "threequarter": "_tq", "bust": "_bust"}[a.framing]
        for negname, neg in negarms:
            tag = "b_%s_%s%s" % (b, negname, suffix)
            want.append(tag)
            jobs.append((tag, ref_wf(tag, prompt, [src], 896, 1344, a.seed, neg=neg)))
    got = batch(jobs, "bodies")
    stage_ok(got, want)
    cells = [(t.replace("b_", ""), got[t]) for t in want if t in got]
    montage(cells, os.path.join(OUT, "04_bodies_%s.jpg" % a.framing), 4, 480)
    for t in want:
        if t in got:
            shutil.copy(got[t], os.path.join(COMFY_IN, "tr_%s.png" % t))


# ── stage: sheets ────────────────────────────────────────────────────────────


def compose_sheet(panel_pngs, dst, height=1216, gap=0):
    """hstack N panels at one common height, PIL not ffmpeg.

    Qwen-Edit conditions on the whole image and takes whatever is legible in it, so every
    panel has to be legible at the same time - hence one common HEIGHT rather than one
    common width, and hence a hard cap on how many panels are worth having: each one added
    makes all the others narrower once the sheet is scaled to the sampler's working size.
    """
    ims = []
    for p in panel_pngs:
        im = Image.open(p).convert("RGB")
        w = int(round(im.width * height / im.height))
        ims.append(im.resize((w, height), Image.LANCZOS))
    total = sum(i.width for i in ims) + gap * (len(ims) - 1)
    out = Image.new("RGB", (total, height), (17, 17, 17))
    x = 0
    for i in ims:
        out.paste(i, (x, 0))
        x += i.width + gap
    out.save(dst)
    return dst


def cmd_sheets(a):
    """--pairs face:body[:third],...  Builds one candidate sheet per group and stages it."""
    made = []
    for group in a.pairs.split(","):
        parts = group.split(":")
        name = "sheet_%s%s.png" % (parts[0], a.suffix)
        dst = os.path.join(WORK, name)
        compose_sheet([os.path.join(WORK, p + ".png") for p in parts], dst, a.height)
        shutil.copy(dst, os.path.join(COMFY_IN, name))
        shutil.copy(dst, os.path.join(OUT, name))
        made.append((name, dst))
        print("  %s  %s  (%d panels)" % (name, Image.open(dst).size, len(parts)))
    montage(made, os.path.join(OUT, "05_sheets%s.jpg" % a.suffix), 2, 900)


# ── stage: probe ─────────────────────────────────────────────────────────────
#
# The only test that matters. A sheet is not judged as a picture, it is judged by what
# comes out the other end of the path the app actually uses.

PROBES = [
    ("close", "A close portrait of this exact woman, head and shoulders, three-quarters to "
              "camera, looking off camera-left. Soft window light from camera-left, deep "
              "falloff on the shadow side. " + TAIL, 1024, 1280),
    ("hall", "This exact woman standing in a cold stone hall, a shaft of daylight from a "
             "high window falling across her, dust in the air, the room dark behind her. "
             "Three-quarter body, 50mm. She wears " + WARDROBE + ". " + TAIL, 896, 1344),
    ("street", "This exact woman walking through a wet market street at dusk, practical "
               "lanterns behind her going out of focus, caught mid-stride and not looking "
               "at the camera. 85mm at f/2. She wears " + WARDROBE + ". " + TAIL,
     896, 1344),
]


def cmd_probe(a):
    """Every candidate sheet down the real path, against the current sheet and a no-sheet
    control, with the workflow-default negative as its own arm."""
    sheets = [s.strip() for s in a.sheets.split(",") if s.strip()]
    arms = []
    for s in sheets:
        arms.append((s, s + ".png", NEG_PHOTO, "photoneg"))
    if a.include_current:
        arms.append(("CURRENT", card().get("sheet_photo"), NEG_PHOTO, "photoneg"))
        arms.append(("CURRENT", card().get("sheet_photo"), None, "wfneg"))
    if sheets and a.negarm:
        arms.append((sheets[0], sheets[0] + ".png", None, "wfneg"))

    jobs, want = [], []
    for pid, prompt, w, h in PROBES:
        for name, ref, neg, negname in arms:
            tag = "q_%s_%s_%s" % (pid, name, negname)
            want.append((pid, tag, "%s / %s" % (name, negname)))
            jobs.append((tag, ref_wf(tag, prompt, [ref], w, h, a.seed, neg=neg)))
        if a.control:
            tag = "q_%s_NOSHEET" % pid
            want.append((pid, tag, "NO SHEET (t2i control)"))
            jobs.append((tag, t2i_wf(tag, prompt.replace("this exact woman", IDENT) + " " +
                                     HAIR[a.hair], w, h, a.seed)))
    got = batch(jobs, "probe")
    stage_ok(got, [t for _, t, _ in want])
    for pid in [p[0] for p in PROBES]:
        cells = [(lab, got[t]) for p, t, lab in want if p == pid and t in got]
        # SUFFIX, because a later single-sheet run of this stage overwrote the multi-sheet
        # comparison it had just been used to make. Contact sheets are the evidence a
        # verdict cites; a stage that silently replaces one is a stage that can erase the
        # reason a decision was taken.
        montage(cells, os.path.join(OUT, "06_probe_%s%s.jpg" % (pid, a.suffix)),
                len(cells) or 1, 560 if pid == "close" else 460)


# ── stage: facepass ──────────────────────────────────────────────────────────
#
# The previous attempt at this (arm D of terra_face_quality.jpg) produced a good re-rendered
# crop and a paste-back that washed it out. Two things fix that and both are here:
#   1. the re-render is colour-matched back to the original crop, per channel, on mean and
#      standard deviation, so the seam cannot show a level shift
#   2. the feather is a NARROW ring at the very edge, not a soft blend across the whole
#      crop, so the interior is the new pixels at full strength
# and then the seam is cut out at 1:1 and looked at, which is the step that was skipped.


def _match_levels(new, ref):
    """Linear per-channel match of `new` to `ref` on mean and stddev. PIL only - the system
    python3 on this box has PIL and NO numpy, and every card tells the reader to run these
    tools with python3."""
    out = []
    sn, sr = ImageStat.Stat(new), ImageStat.Stat(ref)
    for ch in range(3):
        m1, d1 = sn.mean[ch], max(sn.stddev[ch], 1e-3)
        m2, d2 = sr.mean[ch], sr.stddev[ch]
        g = d2 / d1
        b = m2 - g * m1
        lut = [max(0, min(255, int(round(g * v + b)))) for v in range(256)]
        out.append(lut)
    return new.point(out[0] + out[1] + out[2])


def _feather(size, ring):
    """A mask that is 255 everywhere except a linear ramp `ring` px wide at the border."""
    w, h = size
    m = Image.new("L", size, 255)
    px = m.load()
    for y in range(h):
        for x in range(w):
            d = min(x, y, w - 1 - x, h - 1 - y)
            if d < ring:
                px[x, y] = int(255 * d / ring)
    return m


def cmd_facepass(a):
    """Crop the face, re-render it big at low denoise, colour-match, paste back, LOOK.

    --box is x,y,w,h in fractions of the source. There is no face detector in the system
    python here; SDPoseFaceBBoxes exists in ComfyUI but returns nothing this script could
    read, so the box is given explicitly and the result is checked by eye at 1:1, which is
    the only check that would have caught the previous failure anyway.
    """
    src = a.src if os.path.isabs(a.src) else os.path.join(WORK, a.src + ".png")
    im = Image.open(src).convert("RGB")
    fx, fy, fw, fh = [float(v) for v in a.box.split(",")]
    box = (int(im.width * fx), int(im.height * fy),
           int(im.width * (fx + fw)), int(im.height * (fy + fh)))
    crop = im.crop(box)
    # ASPECT MUST SURVIVE THE ROUND TRIP. Forcing the crop to a square would re-render a
    # squashed face and then unsquash it, which puts the model's idea of a face onto the
    # wrong proportions - a subtler version of the failure this stage exists to avoid.
    # Scale the long side to 1024 and round both sides to a multiple of 32 for the VAE.
    scale = 1024.0 / max(crop.size)
    tw = max(256, int(round(crop.width * scale / 32)) * 32)
    th = max(256, int(round(crop.height * scale / 32)) * 32)
    up = crop.resize((tw, th), Image.LANCZOS)
    tmp = "tr_facepass_in.png"
    up.save(os.path.join(COMFY_IN, tmp))
    print("  crop %s -> render %s -> back to %s" % (crop.size, (tw, th), crop.size))

    prompt = ("A close photographic portrait of this exact woman. Same face, same "
              "expression, same light, same colour. " + TAIL)
    jobs = []
    for d in [float(x) for x in a.denoise.split(",")]:
        jobs.append(("fp_%02d" % int(d * 100),
                     ref_wf("fp_%02d" % int(d * 100), prompt, [tmp], tw, th,
                            a.seed, neg=NEG_PHOTO, denoise=d)))
    got = batch(jobs, "facepass")

    cells, seams = [], []
    for tag, path in sorted(got.items()):
        new = Image.open(path).convert("RGB").resize(crop.size, Image.LANCZOS)
        new = _match_levels(new, crop)
        merged = im.copy()
        ring = max(6, min(crop.size) // 24)
        merged.paste(new, box[:2], _feather(crop.size, ring))
        dst = os.path.join(WORK, "merged_%s.png" % tag)
        merged.save(dst)
        cells.append((tag, dst))
        # the seam, at 1:1, which is the step that was skipped last time
        pad = ring * 4
        sb = (max(0, box[0] - pad), max(0, box[1] - pad),
              min(im.width, box[2] + pad), min(im.height, box[3] + pad))
        s = os.path.join(WORK, "seam_%s.png" % tag)
        merged.crop(sb).save(s)
        seams.append((tag + " seam 1:1", s))
    cells.insert(0, ("original", src))
    montage(cells, os.path.join(OUT, "07_facepass.jpg"), len(cells), 520)
    montage(seams, os.path.join(OUT, "07_facepass_seams.jpg"), len(seams) or 1, 620)


# ── stage: negtest ───────────────────────────────────────────────────────────
#
# WHY THIS IS A STAGE AND NOT A FOOTNOTE. Both qwen graphs ship at cfg 1.0, which is the
# value at which classifier-free guidance degenerates and the negative branch normally
# stops being consulted at all. If that is what happens here then the negative prompt is
# INERT on every qwen render this project makes, and both the workflow default's
# "photorealistic, 3d render" (harmless) and this tool's careful NEG_PHOTO (useless) are
# theatre. That is a big enough claim about somebody else's renderer that it gets measured
# rather than reasoned about: same seed, same positive, three negatives including one
# deliberately hostile to the brief, compared pixel-for-pixel.


def cmd_negtest(a):
    pos = face_prompt("saturated", "win85", "portra", "offleft")
    arms = {
        "photoneg": NEG_PHOTO,
        "wfneg": "blurry, low quality, watermark, text, deformed, extra limbs, "
                 "photorealistic, 3d render",
        "hostile": "photograph, real skin, skin pores, film grain, sharp focus, real hair",
        "empty": "",
    }
    jobs = []
    for k, v in arms.items():
        jobs.append(("neg_t2i_" + k, t2i_wf("neg_t2i_" + k, pos, 1024, 1280, a.seed, neg=v)))
    got = batch(jobs, "negtest")
    base = got.get("neg_t2i_empty")
    print("\n  pixel difference against the EMPTY negative, same seed:")
    for k in arms:
        p = got.get("neg_t2i_" + k)
        if not p or not base:
            continue
        r = sh("magick", "compare", "-metric", "RMSE", base, p, "null:")
        print("    %-9s %s" % (k, (r.stderr or r.stdout).strip()))
    montage([(k, got["neg_t2i_" + k]) for k in arms if "neg_t2i_" + k in got],
            os.path.join(OUT, "08_negtest.jpg"), 4, 520)
    print("  If 'hostile' is identical to 'empty', the negative prompt does nothing here.")


# ── stage: install ───────────────────────────────────────────────────────────


def cmd_install(a):
    """Write the winner in. PHOTO AND REALISM FIELDS ONLY - this tool does not touch tags,
    prose, costumes, the LoRA or anything the anime path reads."""
    p = os.path.join(ROOT, "studio", "characters", "TERRA.json")
    with open(p, encoding="utf-8") as f:
        c = json.load(f)
    allowed = {"photo_prose", "sheet_photo", "sheet_photo_body", "sheet_photo_verdict",
               "sheet_photo_note", "realism_verdict", "photo_face_verdict"}
    with open(a.fields, encoding="utf-8") as f:
        new = json.load(f)
    bad = set(new) - allowed
    if bad:
        raise SystemExit("refusing to write fields outside my remit: %s" % sorted(bad))
    for k, v in new.items():
        c[k] = v
    with open(p, "w", encoding="utf-8") as f:
        json.dump(c, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("  wrote %d field(s) into TERRA.json: %s" % (len(new), ", ".join(sorted(new))))


# ── cli ──────────────────────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("portraits", help="hair x light sweep on the t2i path")
    s.add_argument("--seed", type=int, default=SEED)
    s.set_defaults(fn=cmd_portraits)

    s = sub.add_parser("moods", help="grade x expression sweep")
    s.add_argument("--hair", default="roots")
    s.add_argument("--light", default="win85")
    s.add_argument("--seed", type=int, default=SEED)
    s.set_defaults(fn=cmd_moods)

    s = sub.add_parser("finals", help="chosen combinations across seeds")
    s.add_argument("--combos", required=True,
                   help="hair:light:grade:expr,hair:light:grade:expr,...")
    s.add_argument("--seeds", default="4242,777,31337")
    s.add_argument("--ribbon", action="store_true", help="add her oxblood crown ribbon")
    s.set_defaults(fn=cmd_finals)

    s = sub.add_parser("bodies", help="costume panels generated FROM the base portraits")
    s.add_argument("--bases", required=True, help="comma-separated finals tags")
    s.add_argument("--framing", default="threequarter",
                   choices=["full", "threequarter", "bust"])
    s.add_argument("--negarm", action="store_true", help="also run the workflow default negative")
    s.add_argument("--seed", type=int, default=SEED)
    s.set_defaults(fn=cmd_bodies)

    s = sub.add_parser("sheets", help="composite face+body into candidate sheets")
    s.add_argument("--pairs", required=True, help="face:body[:third],...")
    s.add_argument("--height", type=int, default=1216)
    s.add_argument("--suffix", default="", help="appended to the sheet filename")
    s.set_defaults(fn=cmd_sheets)

    s = sub.add_parser("probe", help="candidate sheets down the real downstream path")
    s.add_argument("--sheets", default="")
    s.add_argument("--seed", type=int, default=SEED)
    s.add_argument("--hair", default="roots")
    s.add_argument("--include-current", action="store_true")
    s.add_argument("--negarm", action="store_true",
                   help="also run the first candidate with the WORKFLOW DEFAULT negative")
    s.add_argument("--control", action="store_true", help="add a no-sheet t2i control")
    s.add_argument("--suffix", default="", help="appended to the contact-sheet filenames")
    s.set_defaults(fn=cmd_probe)

    s = sub.add_parser("facepass", help="face detail pass with a checked paste-back")
    s.add_argument("--src", required=True)
    s.add_argument("--box", default="0.28,0.06,0.44,0.36", help="x,y,w,h as fractions")
    s.add_argument("--denoise", default="0.30,0.45")
    s.add_argument("--seed", type=int, default=SEED)
    s.set_defaults(fn=cmd_facepass)

    s = sub.add_parser("negtest", help="does the negative prompt do anything at cfg 1.0?")
    s.add_argument("--seed", type=int, default=SEED)
    s.set_defaults(fn=cmd_negtest)

    s = sub.add_parser("install", help="write photo/realism fields into TERRA.json")
    s.add_argument("--fields", required=True, help="json file of field->value")
    s.set_defaults(fn=cmd_install)

    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    a.fn(a)


if __name__ == "__main__":
    main()
