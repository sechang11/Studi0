#!/usr/bin/env python3
"""ONE CHARACTER ACROSS THE WHOLE STYLE LIBRARY. The widest axis of "all versions of her".

    ~/ComfyUI/venv/bin/python studio/_tools/terra_styles.py --stage 0   # prompt-recipe pilot
    ~/ComfyUI/venv/bin/python studio/_tools/terra_styles.py --stage A   # every anime-engine ready style
    ~/ComfyUI/venv/bin/python studio/_tools/terra_styles.py --stage Q   # every qwen-engine ready style
    ~/ComfyUI/venv/bin/python studio/_tools/terra_styles.py --sheets    # rebuild contact sheets only

    Use the ComfyUI venv python. The metric pass needs numpy and the system python3 on
    this box has PIL but not numpy.

WHAT IS BEING ASKED. Not "does the style work" - studio/_tools/style_examples.py already
answered that against a generic woman in a coat, and the answers are on the cards in
`verdict` and `compose`. The question here is the one a director asks about a CAST MEMBER:
put THIS person in that idiom and do you still get HER out. Two independent halves, and a
style passes only if both land. A gorgeous woodblock print of somebody else is a failure.

THE ONE RULE THIS TOOL EXISTS TO OBEY. One place, one seed, one costume, one framing, one
LoRA strength, one IPAdapter weight. The ONLY thing that varies between two cells in a
sweep is the style card. This project has broken that discipline repeatedly - 133 of 134
capability cards varied the subject alongside the variable and so demonstrated nothing -
and every held-constant value lives in the CONSTANTS block below where it can be read at a
glance. If you change one, you have started a new sweep and the old cells are not
comparable.

WHY THE SETTINGS ARE WHAT THEY ARE. Each of these is somebody's measurement, not a guess:

  IPAdapter 0.0 on the anime path. A reference sheet was measured to suppress style - four
  styles came back as one render repeated. Identity is carried by the trained LoRA alone.
  This is the single setting that makes a style sweep possible at all on a cast member.

  LoRA v3 at 0.5. 0.5 is the strength every existing film was built against. The v3 weights
  are the recaptioned two-costume retrain; the taupe-backdrop collapse that used to appear
  at 0.85 was the uncaptioned turnaround wall, not a property of strength.

  The danbooru name is a PILOT VARIABLE, not a constant, and stage 0 decides it. For a
  known character the tag and the LoRA each carry the canonical look; together they were
  measured to saturate and beat a costume. A franchise tag plausibly drags a franchise
  ART STYLE too, which would poison every cell of a style sweep. That is a testable claim
  and it gets tested before 90 renders are spent on the wrong recipe.

  The framing tag is the other pilot variable. ukiyo_e and gothic_illustration were both
  measured to hijack COMPOSITION rather than medium and shrink her to a distant figure. A
  dossier of tiny figures is useless, so the shot size is pinned in the prompt - and where
  in the prompt is exactly the kind of thing this project has found to be load-bearing.

  On the qwen path the character LoRA does nothing - it is base-model locked - so identity
  comes from her PHOTOGRAPHIC sheet through Qwen-Image-Edit. That sheet is a photograph,
  and a reference imports its medium as hard as its identity, so the non-photographic qwen
  styles (pixar_3d, claymation, noir_comic, eight_bit, blueprint) are expected to fight it.
  Stage 0 measures that too rather than assuming it, and carries a no-reference arm as the
  fallback.

  Do not try to fix a qwen render with a negative prompt. At cfg 1.0 with the Lightning
  LoRA the negative was measured to produce byte-identical output. The negatives are still
  written, because they cost nothing and the setting may change, but no qwen result here
  may be attributed to one.

THE NEGATIVE IS BUILT PER STYLE, which is new and matters. The standing anime negative
carries "photorealistic, 3d, western comic" as a medium guard. Applied blindly that guard
fights american_comic, low_poly_3d and voxel - three cards would have been condemned by
their own workflow. neg_for_style() drops any guard clause the style itself asks for.

================================ WHAT THIS SWEEP FOUND ================================
Per-style verdicts are in samples/cast/terra_styles/verdicts.json, every one of them set
by opening the cell and looking at it. The five results that generalise beyond Terra:

1  THE COMPOSITION HIJACK AND THE IDENTITY FAILURE ARE ONE FAILURE, NOT TWO. Eleven of
   sixty-six anime cells came back with her hair repainted red at seed 3311, and about
   forty did at seed 7788 - and at 7788 almost every red-haired cell is also a cell where
   the style pulled the camera back and made her small. Where she is rendered large she
   stays green; where a style wins the framing she loses her hair colour with it. A
   character LoRA holds identity in proportion to the pixels the character occupies, so
   "the style shrank her" and "the style repainted her" are the same event. Read
   sheet_heads_a_01.jpg against sheet_heads_a_s7788_01.jpg - the correlation is visible at
   a glance across 132 cells.

2  SO SHOT SIZE IS THE LOAD-BEARING CONTROL, AND PINNING IT IN THE PROMPT IS NOT ENOUGH.
   "cowboy shot" first in the tag string stopped both measured hijackers at seed 3311 and
   failed across most of the library at seed 7788. Anything that depends on her being big
   in frame - which is everything about a character - needs the framing enforced by
   something stronger than a tag.

3  IDENTITY LOCK AND STYLE STRENGTH ARE THE SAME DIAL PULLING OPPOSITE WAYS, measured
   three ways across 33 cells in stage H and consistent in all eleven styles:
     LoRA 0.50, no danbooru name  -> style at full strength, HAIR RED
     LoRA 0.50, name restored     -> hair green, but the tag drags its canon back: a
                                     feathered headdress that is on no card of hers, and
                                     her gold dress replaced by a bandeau and wrap
     LoRA 0.85, no name           -> hair green AND costume correct, but the style is
                                     visibly weaker - chiaroscuro flattens, glow dims,
                                     the ink wash thins
   There is no free option. Default to 0.50/no-name, escalate to 0.85 only for the styles
   verdicts.json marks as identity failures, and never restore the tag - it costs a whole
   costume plus an injected prop to buy back one colour.

4  ON THE QWEN EDIT-REF PATH THE REFERENCE GOVERNS PROPORTION AND THE PROMPT GOVERNS
   EVERYTHING ELSE. A style that changes how she is DRAWN lands completely - noir_comic
   inks her, eight_bit pixelates her, pointillism dots her. A style that needs to change
   what she IS cannot - pixar_3d's stylised proportion, stop_motion_felt's puppet and
   claymation's clay face all convert the SET and leave her a photographic human standing
   in it. blueprint is the extreme case and worth looking at: a real person inside a
   cyanotype line drawing.

5  THE QWEN PATH IS THE SEED-ROBUST ONE AND THE ANIME PATH IS THE EXPRESSIVE ONE.
   Identity held in 29/29 qwen cells at seed 3311 and 28/29 at 7788, with the single
   exception being security_camera putting her far away on purpose. The anime path held
   55/66 and then roughly 26/66. Pixel conditioning beats a weight-space prior when
   something else in the prompt is fighting for the frame.
"""
import argparse, json, os, subprocess, sys, time, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import api, run, set_path                  # noqa: E402
from epic import load_wf, ensure_local, HOST          # noqa: E402
from PIL import Image, ImageDraw, ImageFont           # noqa: E402
import numpy as np                                    # noqa: E402

CAST = os.path.join(STUDIO, "characters")
STYLEDIR = os.path.join(STUDIO, "styles")
PLACEDIR = os.path.join(STUDIO, "places")
OUT = os.path.join(STUDIO, "samples", "cast", "terra_styles")
CELLS = os.path.join(OUT, "cells")
SCRATCH = "/tmp/terra_styles_work"
MEAS = os.path.join(OUT, "measurements.json")
CLIENT = str(uuid.uuid4())

WF_ANIME = "22_anime_kf_ipadapter.json"   # animagine + IPAdapter, sheet on node 2
WF_T2I = "13_qwen_t2i_styled.json"        # Qwen-Image 2512, style LoRA slot on node 7
WF_REF = "14_qwen_edit_ref.json"          # Qwen-Image-Edit 2511, reference on node 8

# ====================================================================== CONSTANTS
# Everything held still. Change one of these and you have started a new sweep.
CHAR = "TERRA"
SEED = 3311                  # the dossier seed. --seed runs a confirmation pass; see below.
SFX = ""                     # tag suffix, non-empty only on a confirmation seed
PLACE = "castle_courtyard"
COSTUME = "default"          # the traveller - her trained default, measured to land
WEAR = 0                     # undamaged rung
IP_WEIGHT = 0.0              # a sheet suppresses style; the LoRA carries identity alone
AW, AH = 896, 1152           # SDXL portrait bucket, 0.778
QW, QH = 1024, 1280          # qwen 4:5. A waist-up figure at 16:9 wastes the face.

# The shot size, pinned, because two styles were measured to shrink her to a distant
# figure. "cowboy shot" is a real danbooru tag meaning mid-thigh up, so it is a noun the
# checkpoint was trained on rather than an adjective it will ignore.
FRAME_ANIME = "cowboy shot, solo focus, looking at viewer"
FRAME_QWEN = ("Waist-up to mid-thigh, standing, facing the camera, the figure filling "
              "most of the frame")

Q_TAGS = "masterpiece, best quality, very aesthetic, absurdres"

# Workflow 22's shipped node-6 negative opens "1girl, girl, female, feminine, breasts" -
# written for two male footballers and baked in. Rebuilt rather than extended, exactly as
# cast_proof.py and cast_style.py do, or a female character is not renderable at all.
NEG_BASE = ("motion blur, blurry, overexposed, washed out, lowres, worst quality, "
            "bad anatomy, bad hands, extra limbs, watermark, signature, text")
NEG_FEMALE = "1boy, male focus, masculine, beard, facial hair, multiple girls"
# The medium guard. Each clause here is dropped again when the style asks for it.
NEG_MEDIUM = ["photorealistic", "3d", "western comic", "multiple views"]
NEG_PHOTO = ("illustration, drawing, painting, anime, cartoon, comic, sketch, cel shading, "
             "lineart, 3d render, cgi, blurry, low quality, watermark, text, "
             "jpeg artifacts, deformed, extra limbs")

# compose.py:209 strips these from a place tag string when a character is in the shot.
PLACE_EMPTY_NOUNS = ("scenery", "no humans")

# ====================================================================== STAGE 0
# Two prompt decisions, settled by rendering before 90 cells are spent on a recipe.
PILOT_STYLES = [
    ("ukiyo_e", "measured hijacker - put her in an ornamental arch"),
    ("gothic_illustration", "measured hijacker - shrank her to a kneeling figure"),
    ("watercolour", "measured clean - landed and she survived"),
    ("_control", "no style at all - the baseline"),
]
# (label, keep danbooru name?, frame first in the tag string?)
PILOT_ARMS = [
    ("name+frame_late", True, False),
    ("name+frame_early", True, True),
    ("noname+frame_late", False, False),
    ("noname+frame_early", False, True),
]
# (label, route, style clause first?)
PILOT_QARMS = [
    ("ref_style_last", "ref", False),
    ("ref_style_first", "ref", True),
    ("noref_style_first", "noref", True),
]
PILOT_QSTYLES = [
    ("film_35mm", "photographic - aligned with the photo sheet"),
    ("pixar_3d", "non-photographic - should fight the photo sheet"),
    ("noir_comic", "non-photographic, graphic - should fight it hardest"),
]

# Set from stage 0 by looking. Stage A and Q read these.
RECIPE = {
    "keep_danbooru_name": False,
    "frame_first": True,
    "qwen_route": "ref",
    "qwen_style_first": True,
}


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def font(sz, bold=True):
    for p in ("/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/google-carlito-fonts/Carlito-Bold.ttf",
              "/usr/share/fonts/adwaita-sans-fonts/AdwaitaSans-Regular.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def card():
    return jload(os.path.join(CAST, CHAR + ".json"))


def style_card(sid):
    return jload(os.path.join(STYLEDIR, sid + ".json"))


def place_card():
    return jload(os.path.join(PLACEDIR, PLACE + ".json"))


def place_tags():
    parts = [x.strip() for x in place_card().get("tags", "").split(",")]
    return ", ".join(p for p in parts if p.lower() not in PLACE_EMPTY_NOUNS)


def styles_for(engine):
    """Every status=ready card that routes to this engine. `either` counts for both."""
    out = []
    for fn in sorted(os.listdir(STYLEDIR)):
        if not fn.endswith(".json"):
            continue
        st = jload(os.path.join(STYLEDIR, fn))
        if st.get("status") != "ready":
            continue
        eng = str(st.get("engine", "")).lower()
        if eng == engine or eng == "either":
            out.append(st)
    return out


def wear_tags():
    c = card()
    cos = (c.get("costumes") or {}).get(COSTUME) or {}
    wt = cos.get("wear_tags") or c.get("wear_tags") or [""]
    return wt[min(WEAR, len(wt) - 1)].strip()


def wear_prose():
    """wear_tags are danbooru fragments. Qwen is a prose model and the article is free."""
    w = wear_tags()
    if not w:
        return "in plain clothes"
    if w.lower().startswith("wearing"):
        return w
    return "wearing " + (("an " if w[0].lower() in "aeiou" else "a ") + w
                         if w[:2].lower() not in ("a ", "an") else w)


def photo_bits():
    """Split photo_prose into the parts this sweep is allowed to use, and drop the rest.

    THE SAME COSTUME IS A DIFFERENT STRING ON EACH ENGINE, and this is the whole reason
    photo_prose exists. Her traveller outfit is "red cape, sleeveless gold dress, red sash,
    red boots" in danbooru and "raw-silk tabard in faded ochre, wool cape in dull carmine,
    worn brown leather belt" in photographic prose - the same clothes, re-materialised,
    because transcribing the tag string literally into a photo prompt is precisely what
    produced her first sheet as cosplay: a green wig, craft felt and vinyl boots. So the
    qwen path takes its wardrobe from here, not from wear_tags. The costume is still held
    constant; only the dialect changes.

    Two sentences are deliberately THROWN AWAY. The lighting sentence ("soft daylight from
    a tall window, warm grey seamless behind her") belongs to a studio backdrop and would
    fight both the place and the style, which is the layer under test. The pose sentence
    belongs to the framing, which is pinned. Keeping either would mean the sweep was not
    holding its constants still.

    Returns (identity, wardrobe).
    """
    import re
    c = card()
    pp = (c.get("photo_prose") or "").strip()
    if not pp:
        return (c.get("prose") or "").strip().rstrip("."), wear_prose()
    sents = [s.strip() for s in re.split(r"(?<=\.)\s+", pp) if s.strip()]
    ident = sents[0].rstrip(".") if sents else ""
    # Strip a leading lens/format clause - "an 85mm portrait at f/2 of". It names a camera,
    # and a camera is a photographic noun that fights eight_bit, blueprint and claymation.
    ident = re.sub(r"^an?\s+[^,]*?(portrait|photograph|shot)[^,]*?\bof\s+", "", ident,
                   flags=re.I)
    wardrobe = ""
    for s in sents[1:]:
        if re.match(r"^(she|he|they)\s+(wears|wear)\b", s, flags=re.I):
            wardrobe = re.sub(r"^(she|he|they)\s+(wears|wear)\s+", "", s.rstrip("."),
                              flags=re.I)
            break
    return ident, ("wearing " + wardrobe if wardrobe else wear_prose())


# ------------------------------------------------------------------ negatives

def neg_for_style(st):
    """Drop any medium-guard clause the style itself is asking for.

    The standing anime negative guards against photorealism, 3d and western comics. Left
    alone it silently fights american_comic, low_poly_3d and voxel - three cards that would
    then be written up as failures of the style rather than failures of the negative. The
    style's own text is the authority on what it wants.
    """
    st = st or {}
    blob = " ".join(str(st.get(k, "")) for k in
                    ("id", "name", "tags", "prose", "means", "family")).lower()
    fam = str(st.get("family", "")).lower()
    keep = []
    for clause in NEG_MEDIUM:
        if clause in blob:
            continue
        if clause == "3d" and fam == "3d":
            continue
        if clause == "photorealistic" and fam in ("photo", "photoreal"):
            continue
        if clause == "western comic" and "comic" in blob:
            continue
        keep.append(clause)
    parts = [NEG_FEMALE, ", ".join(keep), NEG_BASE]
    if st.get("negative_add"):
        parts.append(st["negative_add"])
    seen, clauses = set(), []
    for cl in (x.strip() for p in parts if p for x in p.split(",")):
        if cl and cl.lower() not in seen:
            seen.add(cl.lower())
            clauses.append(cl)
    return ", ".join(clauses)


# ------------------------------------------------------------------ prompts

def anime_prompt(st, keep_name=None, frame_first=None):
    """compose.py's slot order - identity, sex, garment, shot, place, style, quality - with
    two documented deviations, both of them the pilot's variables."""
    keep_name = RECIPE["keep_danbooru_name"] if keep_name is None else keep_name
    frame_first = RECIPE["frame_first"] if frame_first is None else frame_first
    c = card()
    tags = c.get("tags", "")
    if not keep_name:
        tags = ", ".join(x for x in tags.split(", ")
                         if "terra branford" not in x.lower()
                         and "final fantasy" not in x.lower())
    ident = [c["id"].lower(), tags.strip()]
    if c.get("base_tags"):
        ident.append(c["base_tags"].strip())
    ident.append(wear_tags())
    bits = ([FRAME_ANIME] + ident if frame_first else ident + [FRAME_ANIME])
    bits.append(place_tags())
    if st and st.get("tags"):
        bits.append(st["tags"].strip())
    bits.append(Q_TAGS)
    return ", ".join(b for b in bits if b)


def qwen_ref_prompt(st, style_first=None):
    """The literal "image 1" phrasing workflow 23 says the edit model was trained on. The
    sentence never says "the woman", so it never re-asserts the thing under test."""
    style_first = RECIPE["qwen_style_first"] if style_first is None else style_first
    med = ("The entire image is %s." % st["prose"].strip().rstrip(".")) \
        if (st and st.get("prose")) else ""
    body = ("The person in image 1 is now in %s. %s. Keep their face, hair and features "
            "exactly as they are in image 1. They are %s."
            % (place_card().get("prose", PLACE), FRAME_QWEN, photo_bits()[1]))
    return (med + " " + body).strip() if style_first else (body + " " + med).strip()


def qwen_noref_prompt(st):
    """No reference, so the person has to come from words - her photo_prose identity."""
    ident, wardrobe = photo_bits()
    med = ("The entire image is %s." % st["prose"].strip().rstrip(".")) \
        if (st and st.get("prose")) else ""
    return ("%s %s, %s, standing in %s. %s."
            % (med, ident, wardrobe, place_card().get("prose", PLACE),
               FRAME_QWEN)).strip()


# ------------------------------------------------------------------ graphs

def wf_anime(st, tag, keep_name=None, frame_first=None):
    c = card()
    wf = load_wf(WF_ANIME)
    set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
    set_path(wf, "2.inputs.image", c.get("sheet") or "sheet_anime_terra.png")
    set_path(wf, "4.inputs.weight", float(IP_WEIGHT))
    set_path(wf, "5.inputs.text", anime_prompt(st, keep_name, frame_first))
    set_path(wf, "6.inputs.text", neg_for_style(st))
    set_path(wf, "8.inputs.seed", SEED)
    for n in ("7", "10"):
        set_path(wf, "%s.inputs.width" % n, AW)
        set_path(wf, "%s.inputs.height" % n, AH)
    # The character LoRA, spliced in front of every consumer of the checkpoint model.
    wf["90"] = {"class_type": "LoraLoaderModelOnly",
                "inputs": {"model": ["1", 0], "lora_name": c["lora"],
                           "strength_model": float(c.get("lora_strength_measured") or 0.5)}}
    for nid, node in list(wf.items()):
        if nid in ("1", "90") or not isinstance(node, dict):
            continue
        for k, v in (node.get("inputs") or {}).items():
            if isinstance(v, list) and len(v) == 2 and v[0] == "1" and v[1] == 0:
                node["inputs"][k] = ["90", 0]
    set_path(wf, "11.inputs.filename_prefix", "claude-generated/terra_styles/%s" % tag)
    return wf


def wf_qwen_ref(st, tag, style_first=None):
    """Qwen-Image-Edit 2511 in REFERENCE mode: node 13 samples node 20, an empty latent,
    not node 12 - so a new scene is generated with the sheet as side-conditioning rather
    than the sheet being painted over."""
    c = card()
    wf = load_wf(WF_REF)
    wf.pop("9", None)      # second LoadImage, unwired here
    wf.pop("12", None)     # VAEEncode of the ref - dead in reference mode
    set_path(wf, "8.inputs.image", c.get("sheet_photo") or "sheet_photo_terra.png")
    set_path(wf, "10.inputs.prompt", qwen_ref_prompt(st, style_first))
    set_path(wf, "11.inputs.prompt", NEG_PHOTO)   # measured inert at cfg 1.0; written anyway
    set_path(wf, "20.inputs.width", QW)
    set_path(wf, "20.inputs.height", QH)
    set_path(wf, "13.inputs.seed", SEED)
    set_path(wf, "7.inputs.strength_model", 0.0)  # style LoRA slot off - never trusted
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/terra_styles/%s" % tag)
    return wf


def wf_qwen_noref(st, tag):
    wf = load_wf(WF_T2I)
    set_path(wf, "10.inputs.text", qwen_noref_prompt(st))
    set_path(wf, "11.inputs.text", NEG_PHOTO)
    set_path(wf, "12.inputs.width", QW)
    set_path(wf, "12.inputs.height", QH)
    set_path(wf, "13.inputs.seed", SEED)
    set_path(wf, "7.inputs.strength_model", 0.0)
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/terra_styles/%s" % tag)
    return wf


# ------------------------------------------------------------------ render

def fetch(tag, outs):
    """Pull one finished render off the server and keep it as a cell.

    THE MEASUREMENT TRAP THIS AVOIDS. epic.ensure_local() returns early when the
    destination already exists, so a probe that names its scratch file after the cell will
    silently re-tile the PREVIOUS run's image and come back byte-identical - which reads as
    'the change did nothing'. The scratch path is removed before every fetch.
    """
    if not outs:
        print("    %-34s no output" % tag, flush=True)
        return None
    os.makedirs(SCRATCH, exist_ok=True)
    raw = os.path.join(SCRATCH, tag + ".png")
    if os.path.exists(raw):
        os.remove(raw)
    loc = ensure_local(outs[0], raw, required=False)
    if not loc:
        print("    %-34s could not fetch" % tag, flush=True)
        return None
    os.makedirs(CELLS, exist_ok=True)
    dst = os.path.join(CELLS, tag + ".webp")
    sh("ffmpeg", "-y", "-v", "error", "-i", loc, "-vf", "scale=900:-1",
       "-quality", "90", dst)
    try:
        os.remove(loc)
    except OSError:
        pass
    return dst if os.path.exists(dst) else None


def render(wf, tag, force=False):
    """One cell, submitted and waited on. Kept for the pilot, which is small."""
    dst = os.path.join(CELLS, tag + ".webp")
    if os.path.exists(dst) and not force:
        return dst
    try:
        _, outs = run(HOST, wf, quiet=True)
    except SystemExit as e:            # comfy.api and comfy.run both sys.exit on error
        print("    %-34s SUBMIT/RENDER FAILED (%s)" % (tag, e), flush=True)
        return None
    except Exception as e:
        print("    %-34s FAILED %s" % (tag, str(e)[:70]), flush=True)
        return None
    return fetch(tag, outs)


def run_batch(jobs, force=False):
    """Queue every cell at once, then collect them in order.

    THIS BOX IS SHARED AND THAT CHANGES THE RIGHT WAY TO SUBMIT. Rendering one cell at a
    time and waiting for it means every single cell rejoins the BACK of a queue that other
    agents are also filling - measured here against a concurrently running LTX-2.3 22B
    video wave, where warm 3-second SDXL renders were taking 30 seconds of wall clock and
    then stalled entirely behind a video job. Submitting the whole sweep in one go puts
    the cells contiguously in the queue, so the sweep costs the box one wait instead of
    ninety-four, and finishes in its own render time rather than in everyone else's.

    ComfyUI is FIFO, so the jobs complete in submission order and the poll can stop at the
    first one that is not finished yet instead of asking about all of them every cycle.

    jobs: list of dicts with keys `tag` and `wf`. Sets `path` on each.
    """
    todo = []
    for j in jobs:
        dst = os.path.join(CELLS, j["tag"] + ".webp")
        if os.path.exists(dst) and not force:
            j["path"] = dst
            continue
        try:
            resp = api(HOST, "/prompt", {"prompt": j["wf"], "client_id": CLIENT})
        except SystemExit as e:
            print("    %-34s SUBMIT REFUSED (%s)" % (j["tag"], e), flush=True)
            continue
        if "error" in resp:
            print("    %-34s SUBMIT ERROR %s" % (j["tag"], str(resp)[:90]), flush=True)
            continue
        j["pid"] = resp["prompt_id"]
        todo.append(j)
    print("  queued %d cells, %d already on disk"
          % (len(todo), len(jobs) - len(todo)), flush=True)

    t0 = time.time()
    for n, j in enumerate(todo, 1):
        while True:
            try:
                hist = api(HOST, "/history/%s" % j["pid"])
            except SystemExit:
                hist = {}
            entry = hist.get(j["pid"])
            if entry:
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    print("    %-34s RENDER ERROR" % j["tag"], flush=True)
                    j["outs"] = []
                    break
                if status.get("completed"):
                    outs = []
                    for _, out in (entry.get("outputs") or {}).items():
                        for f in out.get("images", []):
                            outs.append(("%s/%s" % (f.get("subfolder", ""),
                                                    f["filename"])).lstrip("/"))
                    j["outs"] = outs
                    break
            time.sleep(3)
        j["path"] = fetch(j["tag"], j.get("outs"))
        print("  [%3d/%d] %-30s %s  (%.0fs elapsed)"
              % (n, len(todo), j["tag"], "ok" if j["path"] else "FAILED",
                 time.time() - t0), flush=True)
    return jobs


# ------------------------------------------------------------------ metrics

def metrics(path, ref=None):
    """Numbers that go BESIDE the looking, never instead of it.

    delta   mean absolute pixel difference from the same-engine no-style control, 0-100.
            A style that scores near zero did nothing. A high score is NOT a pass - a
            style that hijacked the composition also scores high.
    sat     mean saturation. Separates the monochrome idioms mechanically.
    edge    mean gradient magnitude - line-heavy against soft-wash.
    flat    fraction of the frame in its single most common quantised colour. High means
            flat unmodulated areas, which is what the print and vector idioms are made of.
    """
    im = Image.open(path).convert("RGB").resize((256, 320), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    mx, mn = a.max(2), a.min(2)
    sat = float(np.mean(np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)) * 100)
    g = a.mean(2)
    edge = float(np.mean(np.hypot(np.gradient(g)[0], np.gradient(g)[1])))
    q = (a // 32).astype(np.int32)
    codes = q[..., 0] * 64 + q[..., 1] * 8 + q[..., 2]
    flat = float(np.bincount(codes.ravel()).max() / codes.size * 100)
    out = {"sat": round(sat, 1), "edge": round(edge, 2), "flat": round(flat, 1)}
    if ref and os.path.exists(ref):
        b = np.asarray(Image.open(ref).convert("RGB")
                       .resize((256, 320), Image.LANCZOS)).astype(np.float32)
        out["delta"] = round(float(np.mean(np.abs(a - b))) / 255 * 100, 1)
    return out


def build_heads(stage="A", sfx="", per=48, cols=8):
    """Every cell cropped to the head, tiled small, so one image answers one question.

    THE QUESTION. Eleven of the sixty-six anime cells came back with Terra's hair repainted
    red, and the confirmation seed showed the failure is stochastic - gouache, grimdark and
    illuminated_manuscript all passed at 3311 and failed at 7788. So a per-style pass/fail
    from one seed is a lower bound, and settling it properly means judging 66 styles across
    2 seeds. At six cells to a contact sheet that is 34 sheets to read.

    A PIXEL METRIC WAS TRIED FIRST AND FAILED ITS VALIDATION, which is why this exists.
    Counting red-dominant against green-dominant pixels in the top of the frame looks
    obvious and does not work: solarpunk and trigger_kinetic both scored strongly GREEN
    while showing red hair, because their backgrounds are green, and golden_age_illustration
    scored RED with green hair because the warm ground and her cape sit high in the frame.
    Validated against fourteen cells already judged by eye, it got four of them wrong. A
    proxy that disagrees with looking, on the very cases it exists to classify, is not a
    measurement - so it was deleted rather than reported.

    What survives is cheaper anyway: crop to where the head actually is and let a person
    look at all of them at once.
    """
    m = load_meas()
    keys = sorted(k for k, v in m.items()
                  if v.get("stage") == stage and k.endswith(sfx)
                  and (sfx or not k.endswith("_s7788")))
    made = []
    for i in range(0, len(keys), per):
        chunk = keys[i:i + per]
        tw, th = 210, 215
        lab = 24
        rows = (len(chunk) + cols - 1) // cols
        im = Image.new("RGB", (cols * (tw + 4) + 4, 40 + rows * (th + lab + 4) + 4),
                       (14, 14, 16))
        d = ImageDraw.Draw(im)
        d.text((6, 8), "HEADS - %s%s : is her hair still green?"
               % (stage, sfx or " seed %d" % SEED), font=font(24), fill=(255, 232, 120))
        f = font(15)
        for n, k in enumerate(chunk):
            p = os.path.join(CELLS, k + ".webp")
            if not os.path.exists(p):
                continue
            src = Image.open(p).convert("RGB")
            W, H = src.size
            crop = src.crop((int(W * .22), int(H * .01), int(W * .78), int(H * .40)))
            crop = crop.resize((tw, th), Image.LANCZOS)
            r, c = divmod(n, cols)
            x = 4 + c * (tw + 4)
            y = 40 + r * (th + lab + 4)
            im.paste(crop, (x, y))
            name = m[k].get("style", k)
            d.rectangle([x, y + th, x + tw, y + th + lab], fill=(26, 26, 30))
            d.text((x + 4, y + th + 4), name[:27], font=f, fill=(220, 220, 226))
        dst = os.path.join(OUT, "sheet_heads_%s%s_%02d.jpg"
                           % (stage.lower(), sfx, i // per + 1))
        im.save(dst, quality=92)
        made.append(dst)
    print("%d head sheets, %d cells" % (len(made), len(keys)))
    return made


def load_meas():
    if os.path.exists(MEAS):
        try:
            return jload(MEAS)
        except Exception:
            pass
    return {}


def save_meas(m):
    os.makedirs(OUT, exist_ok=True)
    with open(MEAS, "w", encoding="utf-8") as f:
        json.dump(m, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def record(tag, **kw):
    """Merge PER CELL, never per stage. A whole-record replace per stage is exactly the
    bug that silently destroyed a column of measurements in cast_voice.py."""
    m = load_meas()
    rec = m.get(tag) or {}
    rec.update(kw)
    m[tag] = rec
    save_meas(m)


# ------------------------------------------------------------------ contact sheets

def sheet(cells, dst, cols=3, cw=600, title=""):
    """cells: list of (image_path, line1, line2). Labels sit UNDER the image so nothing is
    covering the render - a caption box over the top-left corner hides exactly the part of
    a hijacked frame you need to see."""
    cells = [c for c in cells if c[0] and os.path.exists(c[0])]
    if not cells:
        return None
    ch = int(cw * 1.28)
    lab = 62
    pad = 8
    rows = (len(cells) + cols - 1) // cols
    top = 46 if title else 0
    W = cols * (cw + pad) + pad
    H = top + rows * (ch + lab + pad) + pad
    im = Image.new("RGB", (W, H), (14, 14, 16))
    d = ImageDraw.Draw(im)
    f1, f2, ft = font(27), font(21), font(30)
    if title:
        d.text((pad + 4, 10), title, font=ft, fill=(255, 232, 120))
    for i, (p, l1, l2) in enumerate(cells):
        r, c = divmod(i, cols)
        x = pad + c * (cw + pad)
        y = top + pad + r * (ch + lab + pad)
        src = Image.open(p).convert("RGB")
        src.thumbnail((cw, ch), Image.LANCZOS)
        box = Image.new("RGB", (cw, ch), (26, 26, 30))
        box.paste(src, ((cw - src.width) // 2, (ch - src.height) // 2))
        im.paste(box, (x, y))
        d.rectangle([x, y + ch, x + cw, y + ch + lab], fill=(26, 26, 30))
        d.text((x + 8, y + ch + 5), l1[:44], font=f1, fill=(255, 224, 90))
        d.text((x + 8, y + ch + 34), l2[:70], font=f2, fill=(178, 178, 186))
    im.save(dst, quality=92)
    return dst


def build_seedcheck(sfx="_s7788", only=None, per=8):
    """Put the dossier seed beside the confirmation seed, one style per ROW.

    WHY THIS EXISTS. Every per-style verdict this project has ever written rests on a
    single seed, and that limitation is named in the caveats of the video sweep, the
    costume sweep and the voice sweep alike. A verdict that flips when the seed changes is
    not a property of the style, it is a property of that one render. This sheet is the
    cheapest possible way to tell those apart: same style, same everything, two seeds, side
    by side, so a flip is visible rather than assumed absent.
    """
    m = load_meas()
    pairs = []
    for k in sorted(m):
        if k.endswith(sfx) or m[k].get("stage") not in ("A", "Q"):
            continue
        other = k + sfx
        if other not in m:
            continue
        sid = m[k].get("style", k)
        if only and sid not in only:
            continue
        pairs.append((sid, k, other))
    made = []
    for i in range(0, len(pairs), per):
        cs = []
        for sid, a, b in pairs[i:i + per]:
            for tag, lab in ((a, "seed %d" % SEED), (b, "seed %s" % sfx.lstrip("_s"))):
                mt = m[tag].get("metrics") or {}
                cs.append((os.path.join(CELLS, tag + ".webp"), "%s | %s" % (sid, lab),
                           "%s | d%s sat%s edge%s flat%s"
                           % (m[tag].get("family", "?"), mt.get("delta", "-"),
                              mt.get("sat", "-"), mt.get("edge", "-"),
                              mt.get("flat", "-"))))
        dst = os.path.join(OUT, "sheet_seedcheck_%02d.jpg" % (i // per + 1))
        if sheet(cs, dst, cols=2, cw=560,
                 title="SEED CHECK - does the verdict survive a second seed?  (%d/%d)"
                       % (i // per + 1, (len(pairs) + per - 1) // per)):
            made.append(dst)
    print("\n%d seed-check sheets, %d styles compared" % (len(made), len(pairs)))
    return made


def build_sheets(per=6, cols=3, seed=None):
    """Group by family so a director reads them thematically, and put each style's
    EXISTING library verdict on the label - the prior this sweep is arguing with.

    Sheets are built for ONE seed at a time. Mixing two seeds onto a page would put two
    different renders of the same style side by side under one heading, which is a
    seed comparison wearing a style sweep's clothes."""
    seed = SEED if seed is None else seed
    m = {k: v for k, v in load_meas().items()
         if v.get("seed", SEED) == seed or v.get("stage", "").startswith("0")}
    os.makedirs(OUT, exist_ok=True)
    made = []

    def emit(name, keys, title, n_per=None, n_cols=None, cw=600):
        n_per = n_per or per
        n_cols = n_cols or cols
        for i in range(0, len(keys), n_per):
            chunk = keys[i:i + n_per]
            n = "%s_%02d" % (name, i // n_per + 1)
            cs = []
            for k in chunk:
                rec = m[k]
                p = os.path.join(CELLS, k + ".webp")
                mt = rec.get("metrics") or {}
                l2 = "%s | d%s sat%s edge%s flat%s | lib:%s" % (
                    rec.get("family", "?"), mt.get("delta", "-"), mt.get("sat", "-"),
                    mt.get("edge", "-"), mt.get("flat", "-"), rec.get("lib_compose", "?"))
                cs.append((p, rec.get("label", k), l2))
            dst = os.path.join(OUT, "sheet_%s.jpg" % n)
            if sheet(cs, dst, cols=n_cols, cw=cw, title="%s  (%d/%d)" % (
                    title, i // n_per + 1, (len(keys) + n_per - 1) // n_per)):
                made.append(dst)

    # The pilot is a GRID, not a gallery: one row per style, one column per arm, so the
    # arms are read against each other on one line. Chunking it 6-to-a-sheet would split
    # a style's four arms across two images and make the comparison impossible.
    for stage, title, arms in (("0A", "PILOT - anime prompt recipe", PILOT_ARMS),
                               ("0Q", "PILOT - qwen route", PILOT_QARMS),
                               ("H", "WHY THE HAIR WENT RED", HAIR_ARMS)):
        keys = [k for k, v in m.items() if v.get("stage") == stage]
        if not keys:
            continue
        order = {lab.replace("+", "_"): i for i, (lab, *_) in enumerate(arms)}
        keys.sort(key=lambda k: (m[k].get("style", ""),
                                 order.get(k.split("__")[-1], 99)))
        n = len(arms)
        name = ("hair" if stage == "H" else "pilot_%s" % stage.lower())
        emit(name, keys, title, n_per=n * 4, n_cols=n, cw=470)

    for stage, title in (("A", "TERRA x STYLE - illustration engine"),
                         ("Q", "TERRA x STYLE - qwen engine")):
        keys = [k for k, v in m.items() if v.get("stage") == stage]
        if not keys:
            continue
        keys.sort(key=lambda k: (m[k].get("family", "zz"), k))
        byfam = {}
        for k in keys:
            byfam.setdefault(m[k].get("family", "zz"), []).append(k)
        for fam, ks in sorted(byfam.items()):
            emit("%s_%s%s" % (stage.lower(), fam, SFX), ks,
                 "%s - %s  [seed %d]" % (title, fam, seed))
    print("\n%d contact sheets in %s" % (len(made), OUT))
    for p in made:
        print("  " + os.path.basename(p))
    return made


# ------------------------------------------------------------------ stages

def stage_pilot(force=False):
    """Settle the prompt recipe before spending the sweep. Two grids, two questions.

    ANIME: does the danbooru name poison the style layer, and does putting the framing tag
    first stop the two measured composition hijackers?

    QWEN: does the photographic sheet suppress a non-photographic style, and if it does,
    is the no-reference route (her photo_prose, no sheet) a usable fallback?
    """
    print("STAGE 0  prompt-recipe pilot", flush=True)
    for sid, why in PILOT_STYLES:
        st = None if sid == "_control" else style_card(sid)
        for label, keep, first in PILOT_ARMS:
            tag = "p0a_%s__%s" % (sid, label.replace("+", "_"))
            print("  %-22s %-20s" % (sid, label), flush=True)
            p = render(wf_anime(st, tag, keep, first), tag, force)
            if p:
                record(tag, stage="0A", style=sid, label="%s | %s" % (sid, label),
                       family=(st or {}).get("family", "control"),
                       lib_compose=(st or {}).get("compose", "-"), why=why,
                       prompt=anime_prompt(st, keep, first),
                       negative=neg_for_style(st), metrics=metrics(p))
    for sid, why in PILOT_QSTYLES:
        st = style_card(sid)
        for label, route, sfirst in PILOT_QARMS:
            tag = "p0q_%s__%s" % (sid, label)
            print("  %-22s %-20s" % (sid, label), flush=True)
            wf = (wf_qwen_noref(st, tag) if route == "noref"
                  else wf_qwen_ref(st, tag, sfirst))
            p = render(wf, tag, force)
            if p:
                record(tag, stage="0Q", style=sid, label="%s | %s" % (sid, label),
                       family=st.get("family", "?"), lib_compose=st.get("compose", "-"),
                       why=why,
                       prompt=(qwen_noref_prompt(st) if route == "noref"
                               else qwen_ref_prompt(st, sfirst)),
                       metrics=metrics(p))
    print("\nNOW LOOK AT THE PILOT SHEETS before running stage A or Q.", flush=True)


def sweep(engine, only=None, force=False):
    """One engine's whole sweep. The control is submitted FIRST so it is the first thing
    the queue returns and every delta below is measured against this run's own baseline -
    not against a baseline from a previous run at a different seed."""
    stage = "A" if engine == "anime" else "Q"
    pre = "a_" if engine == "anime" else "q_"
    print("STAGE %s  every %s-engine ready style, seed %d, recipe %s"
          % (stage, engine, SEED, RECIPE), flush=True)

    def build(st, tag):
        if engine == "anime":
            return wf_anime(st, tag)
        if RECIPE["qwen_route"] == "noref":
            return wf_qwen_noref(st, tag)
        return wf_qwen_ref(st, tag)

    def prompt_of(st):
        if engine == "anime":
            return anime_prompt(st)
        if RECIPE["qwen_route"] == "noref":
            return qwen_noref_prompt(st)
        return qwen_ref_prompt(st)

    sts = [s for s in styles_for(engine) if s["id"] != "_control"]
    if only:
        sts = [s for s in sts if s["id"] in only]
    print("  %d styles + 1 control" % len(sts), flush=True)

    ctrl_tag = pre + "_control" + SFX
    jobs = [{"tag": ctrl_tag, "wf": build(None, ctrl_tag), "st": None}]
    for st in sts:
        tag = pre + st["id"] + SFX
        jobs.append({"tag": tag, "wf": build(st, tag), "st": st})
    run_batch(jobs, force)

    ctrl = jobs[0].get("path")
    for j in jobs:
        if not j.get("path"):
            continue
        st = j["st"] or {}
        rec = dict(stage=stage, seed=SEED, style=st.get("id", "_control"),
                   label=st.get("id") or "_control (no style)",
                   family=st.get("family", "00control"),
                   lib_compose=st.get("compose", "baseline"),
                   prompt=prompt_of(j["st"]),
                   metrics=metrics(j["path"], ctrl if j["st"] else None))
        if st.get("verdict"):
            rec["lib_verdict"] = st["verdict"][:220]
        if engine == "anime":
            rec["negative"] = neg_for_style(j["st"])
        record(j["tag"], **rec)


# ====================================================================== STAGE H
# THE FAILURE STAGE A FOUND, AND THE THREE THINGS IT COULD BE.
#
# Eleven of the sixty-six anime cells came back with TERRA'S HAIR REPAINTED RED - not
# tinted, not shadowed, but red at the crown fading to green at the ends. Her hair is the
# first identity noun on her card and the thing a viewer recognises her by across a cut, so
# this is a hard identity failure and not a stylistic one. The eleven are listed below and
# they do not share a family: they are painterly, world, movement, anime and 3d.
#
# Three candidate causes, and this stage separates them by rendering the same cell three
# ways:
#   1  THE MISSING TAG. The pilot stripped "terra branford (final fantasy vi)" because it
#      was overriding her own card's costume. That tag is also the strongest green-hair
#      anchor the base checkpoint has. Removing it may have left "long wavy green hair" as
#      a lone adjective competing with a whole style clause for attention - and this
#      project's governing rule is that adjectives lose.
#   2  NOT ENOUGH LoRA. 0.5 is the strength every film was built against, chosen when the
#      uncaptioned v1 weights destroyed the setting above it. v3 raised that ceiling. If
#      identity lock is simply too weak against a strong style, more weight fixes it.
#   3  NEITHER - the style genuinely owns the palette and no prompt-side change helps.
#
# Arms 2 and 3 are one-variable changes off arm 1, so whichever restores the green names
# the cause. If both do, the cheaper one wins.
HAIR_FAILURES = [
    "baroque_painting", "concept_art", "dark_academia", "expressionism", "ink_wash",
    "low_poly_3d", "solarpunk", "steampunk", "trigger_kinetic", "ufotable_glow",
    "wasteland",
]
# (label, keep danbooru name, lora strength)
HAIR_ARMS = [
    ("1_asswept_noname_0.50", False, 0.50),
    ("2_withname_0.50", True, 0.50),
    ("3_noname_0.85", False, 0.85),
]


def stage_hair(only=None, force=False):
    print("STAGE H  why did the hair go red - %d styles x %d arms"
          % (len(HAIR_FAILURES), len(HAIR_ARMS)), flush=True)
    ids = [s for s in HAIR_FAILURES if not only or s in only]
    jobs = []
    for sid in ids:
        st = style_card(sid)
        for label, keep, strength in HAIR_ARMS:
            tag = "h_%s__%s" % (sid, label)
            wf = wf_anime(st, tag, keep_name=keep)
            set_path(wf, "90.inputs.strength_model", float(strength))
            jobs.append({"tag": tag, "wf": wf, "st": st, "label": label,
                         "keep": keep, "strength": strength})
    run_batch(jobs, force)
    for j in jobs:
        if not j.get("path"):
            continue
        record(j["tag"], stage="H", seed=SEED, style=j["st"]["id"],
               label="%s | %s" % (j["st"]["id"], j["label"]),
               family=j["st"].get("family", "?"),
               lib_compose=j["st"].get("compose", "-"),
               keep_danbooru_name=j["keep"], lora_strength=j["strength"],
               prompt=anime_prompt(j["st"], keep_name=j["keep"]),
               metrics=metrics(j["path"]))


def stage_anime(only=None, force=False):
    sweep("anime", only, force)


def stage_qwen(only=None, force=False):
    sweep("qwen", only, force)


def shortlist():
    """What a director actually wants out of a dossier: which styles suit her.

    The bar is BOTH halves at BOTH seeds - the idiom arrived strongly, and she was still
    herself in the 3311 cell and in the 7788 cell. Anything that passed on one seed only
    is listed separately as conditional, because that is exactly the class of claim this
    project keeps having to retract."""
    p = os.path.join(OUT, "verdicts.json")
    if not os.path.exists(p):
        raise SystemExit("no verdicts.json - the verdicts are written by looking, not by "
                         "a stage. See the header of that file.")
    v = jload(p)
    for eng in ("anime", "qwen"):
        rows = v[eng]
        keep = [k for k, r in sorted(rows.items())
                if r["style"] == "strong" and r["id_3311"] == "yes"
                and r["id_7788"] == "yes"]
        cond = [k for k, r in sorted(rows.items())
                if r["style"] == "strong" and r["id_3311"] == "yes"
                and r["id_7788"] != "yes"]
        bad = [k for k, r in sorted(rows.items()) if r["id_3311"] == "no"]
        thin = [k for k, r in sorted(rows.items()) if r["style"] in ("none", "partial")]
        print("\n=== %s ===" % eng.upper())
        print("CAST HER IN THESE - style strong, identity held at both seeds (%d)" % len(keep))
        for k in keep:
            print("   %-26s %s" % (k, rows[k]["saw"][:96]))
        print("\nCONDITIONAL - strong and she held at 3311 only; re-render before "
              "committing, or raise the LoRA to 0.85 (%d)" % len(cond))
        print("   " + ", ".join(cond))
        print("\nIDENTITY FAILS AT BOTH SEEDS - do not use without the 0.85 escalation (%d)"
              % len(bad))
        print("   " + (", ".join(bad) or "(none)"))
        print("\nTHIN - the idiom did not really arrive on this subject (%d)" % len(thin))
        print("   " + ", ".join(thin))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["0", "A", "Q", "H"])
    ap.add_argument("--sheets", action="store_true")
    ap.add_argument("--seedcheck", action="store_true",
                    help="build the two-seed comparison sheets")
    ap.add_argument("--heads", action="store_true",
                    help="crop every cell to the head and tile them - one image that "
                         "answers the identity question for a whole seed at once")
    ap.add_argument("--shortlist", action="store_true",
                    help="print the ranked shortlist from verdicts.json")
    ap.add_argument("--only", help="comma separated style ids")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--keep-name", action="store_true",
                    help="override the pilot: leave the danbooru name in the prompt")
    ap.add_argument("--frame-late", action="store_true")
    ap.add_argument("--qroute", choices=["ref", "noref"])
    ap.add_argument("--per", type=int, default=6)
    ap.add_argument("--seed", type=int,
                    help="run a CONFIRMATION pass at a second seed. Every per-style "
                         "verdict in this project has historically rested on one seed; "
                         "this is what lets a verdict be checked for a seed artefact. "
                         "Cells are suffixed so the dossier seed is never overwritten.")
    a = ap.parse_args()

    global SEED, SFX
    if a.seed and a.seed != SEED:
        SEED = a.seed
        SFX = "_s%d" % a.seed
    if a.keep_name:
        RECIPE["keep_danbooru_name"] = True
    if a.frame_late:
        RECIPE["frame_first"] = False
    if a.qroute:
        RECIPE["qwen_route"] = a.qroute

    os.makedirs(CELLS, exist_ok=True)
    only = [x.strip() for x in a.only.split(",")] if a.only else None
    t0 = time.time()
    if a.stage == "0":
        stage_pilot(a.force)
    elif a.stage == "A":
        stage_anime(only, a.force)
    elif a.stage == "Q":
        stage_qwen(only, a.force)
    elif a.stage == "H":
        stage_hair(only, a.force)
    if a.shortlist:
        shortlist()
        return
    if a.heads:
        for st in ("A", "Q"):
            for s in ("", "_s7788"):
                build_heads(st, s)
    if a.seedcheck:
        build_seedcheck(only=only)
    if a.sheets or a.stage:
        build_sheets(per=a.per)
    print("\n%.1f min" % ((time.time() - t0) / 60))
    print("A RENDER IS NOT A VERIFICATION. Both halves have to be looked at per cell: did "
          "the STYLE land, and is it still TERRA. A beautiful picture of someone else is a "
          "failure for this purpose.")


if __name__ == "__main__":
    main()
