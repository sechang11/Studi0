#!/usr/bin/env python3
"""PROVE A CHARACTER SURVIVES BEING PUT SOMEWHERE NEW.

    python3 studio/_tools/cast_proof.py                    # every character with weights
    python3 studio/_tools/cast_proof.py VIRO NIKA
    python3 studio/_tools/cast_proof.py --stage A B --force
    python3 studio/_tools/cast_proof.py --measure-only     # re-read what is on disk

    NOTE: --measure-only (and the measure pass at the end of a full run) needs numpy.
    System python3 on this box has PIL but NOT numpy, so run measurement with
    ~/ComfyUI/venv/bin/python. Rendering works under either interpreter.

WHY THIS TOOL EXISTS, AND WHY A TURNAROUND IS NOT THE PROOF

A turnaround re-poses ONE picture. It proves the re-poser works; it says nothing about
whether the person survives being dropped into a scene that was never in the training set,
which is the only thing anyone actually wants from a cast. This project already has
studio/_tools/lora_strength_sweep.py, which puts a character in two scenes at three
strengths - that measures STRENGTH. It does not measure whether the same face comes back
in five different rooms, because two cells cannot show you dispersion.

THE MATRIX. One character, five places the training set never contained, everything else
held still - same seed per place, same prompt text, same framing clause, same garment
rung, same sampler settings, same resolution.

    A_lora    character LoRA at the card's own recommended strength AND IPAdapter from the
              reference sheet at the workflow's shipping weight 0.6. This is the exact
              configuration studio/cast.html promises under "trained LoRA + sheet", so it
              is the configuration that has to be proved and not a laboratory variant.
    B_control LoRA off. IPAdapter still at 0.6. THE CONTROL THE BRIEF ASKS FOR: identical
              prompt, identical seed, one thing removed.
    B0_words  LoRA off AND IPAdapter at 0.0. Nothing but the danbooru tags. This is the
              floor, and it is what answers "is it the same person, or merely the same
              description" - because B0 IS the description, rendered five times.
    C_style   the same character in ONE of those places under three styles, on FOUR rungs:
              lora+sheet, sheet only, neither, and LORA ONLY. The fourth rung was added
              after the first three came back with no style on them at all - see the
              result below, it is the most actionable thing this tool found.
    D_qwen    the photographic engine, via the reference sheet through Qwen-Image-Edit.
              The animagine character LoRA is base-locked and does nothing here (proved
              from pixels on 2026-08-03), so the sheet is the only mechanism there is.
    F_*       the five places again with the FRAMING PINNED, because the wide arms are not
              comparable to each other. See the FRAMING IS NOT A CONSTANT block below.

WHAT THIS RUN MEASURED (2026-08-04, 3 characters, 126 cells, all looked at)

  1. IDENTITY HOLDS, AND THE SIZE OF THE WIN DEPENDS ENTIRELY ON HOW SPECIFIC THE TAGS
     ALREADY ARE. VIRO's tags are generic ("long dark brown curly hair, ponytail, brown
     eyes, gold ear stud") and his tags-only arm returns five different people, so the
     LoRA is the difference between a character and a description. NIKA's and PIP's tags
     are extremely specific (heterochromia + a scar + a named pin; ginger + freckles + gap
     teeth + a yellow raincoat) and their tags-only arms are ALREADY nearly on model, so
     the LoRA adds much less. A character LoRA is worth most to the character whose
     description is worth least.
     THE ONE CLEAN COUNTABLE RESULT is NIKA's heterochromia. Her card names two eye
     colours and no side, so nothing in the prompt can decide which eye is which. Amber on
     the viewer's left came back 5 of 5 with the LoRA, 3 of 5 with the reference sheet
     alone, and 2 of 5 on tags alone - chance. Counted by eye off nika_pinned_faces.jpg at
     full crop resolution, twice, because a first count at thumbnail size was not legible.
  2. THE REFERENCE SHEET THROUGH IPAdapter SUPPRESSES THE STYLE, AND THE LoRA DOES NOT.
     Three styles x three characters x four rungs. With the sheet at its shipping weight
     0.6, eight of the nine styled cells are visually indistinguishable from the no-style
     cell beside them - a prompt carrying "monochrome, greyscale, brush stroke" returned a
     full-colour digital anime picture. The one partial exception is NIKA under ink_wash,
     which greys the ROOM but leaves the character in full colour and produces no
     brushwork. Set the IPAdapter to 0.0 and leave the LoRA ON and all three styles land
     on all three characters while the character still holds.
     The hue_vs_unstyled figures in _metrics.json say the same thing without the eye: with
     the sheet on, 16 of 18 cells moved less than 20; with it off, 14 of 18 moved more.
  3. THE LoRA IMPORTS FRAMING AND BACKGROUND, not just the face. All five places came back
     as tight busts, and every scene is bleached toward the training set's flat backdrop.
  4. ON THE QWEN PATH THE SHEET HOLDS IDENTITY BETTER AND COSTS THE SCENE NOTHING - but it
     imports its own STYLE, so an anime sheet makes qwen draw illustrations however loudly
     the prompt says "photograph".

THE TRIGGER WORD IS IN EVERY ARM ON PURPOSE. "viro" is a token the base model has no
opinion about; leaving it in the controls keeps the prompt strings byte-identical between
A, B and B0, so the only difference between the arms is a weight. Removing it from the
controls would have been a second variable.

THE LoRA LOADER IS IN THE GRAPH IN EVERY ARM TOO, at strength 0.0 for the controls.
ComfyUI's LoraLoaderModelOnly returns the model untouched at strength 0, so this is a true
no-op, and it means A and B submit structurally identical graphs.

THE NEGATIVE IS REPLACED WHOLESALE, NOT APPENDED TO. Node 6 of
22_anime_kf_ipadapter.json hard-codes "1girl, girl, female, feminine, breasts, ..." - a
negative written for two male footballers and baked into the workflow. NIKA cannot be
rendered through it as shipped. This is a known, reported renderer defect (scripts/short.py
plumbs no negative input on either keyframe workflow; compose.py:71-73 and 1836-1841 both
say so). It is NOT fixed here - this tool supplies its own negative for its own renders and
the film pipeline is still broken for a female character.

WHAT IS MEASURED, EXACTLY, SO THE NUMBER CAN BE CHALLENGED

Every number in _metrics.json comes from a HEAD CROP, not a whole frame. At full frame a
matching jersey reads as a matching character and it is not.

  1. LOCATING THE HEAD. Not by detection - THERE IS NO FACE DETECTOR ON THIS BOX and a
     skin-hue one was built, tested on seven images, failed differently on all three
     characters and was thrown away (the reasons are recorded above the HEAD constant, so
     nobody repeats it). The head box is three numbers - centre x, centre y and side, as
     fractions of the frame - fixed per image family, set by looking at the renders, and
     then CHECKED against every crop in <ID>_faces.jpg. Cells the box misses are given
     their own three numbers in OVERRIDES; cells with no head in frame at all go in
     EXCLUDE and are left out of every number, with the count printed. The box is square
     and generous enough to contain hair, because hair colour is one of this project's
     load-bearing identity markers and a tight face box would throw it away.
     The SAME box is used for arms A, B and B0 at a given place, which is what makes the
     arm comparison fair - those three cells share a seed and therefore a composition, so
     comparing them through different crop windows would have measured the windows.
     The cost of a fixed box is that some background is inside the crop. That matters,
     because this project has measured that a character LoRA drags its training
     background's value and hue into a scene - so part of any A-vs-B difference below is
     background, not face. It is called out again next to the results.

  2. struct - SHAPE AND VALUE. The head crop is greyscaled, resized to 96x96 and
     z-normalised (subtract its own mean, divide by its own standard deviation) so that
     overall brightness and contrast cannot contribute. The number is the mean absolute
     difference between two such crops, x100.
       0    = identical pixels
       ~113 = the value two statistically independent images would give
     A measured "different people" baseline is computed on this box's own data by
     comparing each character's arm-A cells against the OTHER characters' arm-A cells at
     the same place, and printed beside the within-character numbers. Read the within-arm
     figure against that ceiling, not against zero.

  3. hue - COLOUR IDENTITY. A 36-bin hue histogram of the head crop, each pixel weighted
     by saturation x value so that grey background and black shadow do not vote. The
     number is the chi-square distance between two normalised histograms, x100, so it runs
     0 (same colour distribution) to 100 (disjoint).

  4. WITHIN-ARM DISPERSION is the mean of all 10 pairwise distances between the five
     places of one arm. Low means the same head keeps coming back in different rooms.
  5. TO-SHEET is the mean distance from each of the five cells to the head crop of the
     character's own reference sheet. Low means it is the RIGHT head. A character can
     score well on 4 and badly on 5 - internally consistent and consistently not the
     person on the card - which is why both are reported.

WHAT THESE NUMBERS ARE NOT, AND HOW BADLY ONE OF THEM FAILED

They are not a face-identity metric. There is no face embedding, no landmark model and no
second judge on this box (no cv2, no insightface, no facexlib - checked in both pythons).

MEASURED, AND REPORTED BECAUSE IT IS A NEGATIVE RESULT SOMEBODY ELSE WOULD OTHERWISE
REPEAT: struct does not work. Every arm on every character landed between 95 and 110
against a different-people ceiling of 100.3, including arms that are visibly one man in
five rooms. A z-normalised grey difference over a 96x96 crop is swamped by head angle and
expression, and those vary from cell to cell no matter what is held constant. Read struct
as noise.

hue DOES track the eye, on two characters out of three. Pinned-framing within-arm hue on
this run: NIKA 7.8 / 26.8 / 37.8 and PIP 16.2 / 19.7 / 27.4 for lora / sheet / tags, both
monotone and both matching what the contact sheets show. VIRO breaks it - 11.1 / 6.9 /
32.1 - because his sheet-only arm produces a CONSISTENT man who is simply the WRONG man,
and a colour histogram cannot tell those apart. That is the honest limit of the number:
it measures whether the palette in the crop is stable, which correlates with identity
until a mechanism is stably wrong.

So the number is a check on the judgement, not a substitute for it. Every verdict in this
project's cards from this run was reached by looking at the contact sheets first.

READ THE OUTPUT IN THIS ORDER
    <ID>_places.jpg        3 rows x 5 places, wide. Did the SCENE survive, and is it one
                           person? This is the primary evidence.
    <ID>_pinned.jpg        the same five places with the framing pinned.
    <ID>_pinned_faces.jpg  head crops of the above. IDENTITY IS JUDGED HERE.
    <ID>_style.jpg         4 rungs x 3 styles. Row `loraonly` is the interesting one.
    <ID>_qwen.jpg          the photographic engine via the reference sheet.
    <ID>_faces.jpg         head crops of the WIDE arms - kept for completeness, but the
                           framing differs between arms so they are not comparable.
    _metrics.json          the numbers, the exact crop fractions, and every override.
"""
import argparse, json, os, subprocess, sys, time, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import api, set_path                       # noqa: E402
from epic import load_wf, ensure_local, COMFY, HOST   # noqa: E402

from PIL import Image, ImageDraw, ImageFont           # noqa: E402

OUT = os.path.join(STUDIO, "samples", "cast_proof")
CAST = os.path.join(STUDIO, "characters")
PLACEDIR = os.path.join(STUDIO, "places")
STYLEDIR = os.path.join(STUDIO, "styles")
LORADIR = os.path.join(COMFY, "models", "loras")

WF_ANIME = "22_anime_kf_ipadapter.json"
WF_QWEN = "14_qwen_edit_ref.json"

AW, AH = 896, 1152        # an SDXL bucket in portrait. The workflow ships 1344x768, which
                          # puts a waist-up face on too few pixels to judge identity from.
QW, QH = 1152, 1440       # 4:5, the ratio qwen_character.py settled on for the same reason
SEED0 = 7700
IP_WEIGHT = 0.6           # the shipping weight of node 4. Not tuned here.

Q = "masterpiece, best quality, very aesthetic, absurdres"
FRAME_ANIME = "upper body, looking at the viewer, centered"
FRAME_QWEN = "waist-up photograph"
# Stage F only. See the FRAMING IS NOT A CONSTANT block further down for why this exists.
FRAME_FACE = ("close-up portrait, head and shoulders, face centered, looking at the "
              "viewer, shallow depth of field")
FW = FH = 1024

# The stock node-6 negative carries the sex terms, so it is rebuilt rather than extended.
NEG_BASE = ("motion blur, blurry, overexposed, washed out, photorealistic, 3d, "
            "western comic, multiple views, lowres, worst quality, bad anatomy, bad hands, "
            "extra limbs, watermark, signature, text")
NEG_MALE = "1girl, female, feminine, breasts, multiple boys"
NEG_FEMALE = "1boy, male focus, masculine, beard, facial hair, multiple girls"
NEG_CHILD = "adult, mature male, muscular, tall"

# Five places the training set never contained. The training set is sixteen
# head-and-shoulders turnaround views on one flat backdrop, so any real room is new - but
# these are chosen to SPREAD ACROSS VALUE AND HUE on purpose. This project has measured
# that a character LoRA drags its own training background's value and hue into the scene,
# and that the damage therefore depends on how far the target sits from it. A bright white
# snowfield and a dim underground platform are the two ends of that.
PLACES = ["laundromat", "snowfield", "library_reading_room", "subway_platform",
          "market_street"]

# Three styles that attack identity in three different ways, in increasing order of threat:
#   cel_anime_90s      repaints (line weight, palette, grain) - face geometry left alone
#   ink_wash           deletes COLOUR entirely. Hair colour is the project's most reliable
#                      identity marker, so this removes it and asks what is left.
#   retro_shoujo_70s   rewrites FACE GEOMETRY - huge eyes, elongated figure. Rated strong.
STYLES = ["cel_anime_90s", "ink_wash", "retro_shoujo_70s"]
STYLE_PLACE = "library_reading_room"

# compose.py:209 strips these from a place tag string when a character is in the shot,
# because "no humans" and "1boy, solo" cannot both be true of one frame. Same rule here.
PLACE_EMPTY_NOUNS = ("scenery", "no humans")

ARMS = [
    ("A_lora", True, True),        # LoRA on, IPAdapter on   - what the cast page promises
    ("B_control", False, True),    # LoRA off, IPAdapter on  - the brief's control
    ("B0_words", False, False),    # nothing but the tags    - the floor
]

# FRAMING IS NOT A CONSTANT, AND THAT BREAKS A FACE METRIC. Measured, not assumed: with
# "upper body, looking at the viewer, centered" in every arm, arm A came back as a tight
# bust in all five places while arm B0 came back as wide shots with the figure at a fifth
# of the height. The character LoRA is trained on sixteen head-and-shoulders turnaround
# views, so it imports FRAMING along with the face, and the tags alone do not hold framing
# at all. A crop window that fits arm A therefore lands on background in arm B0, and any
# number computed across them measures the framing rather than the face.
#
# Stage F re-renders the same five places at the same seeds with the framing PINNED hard -
# a square 1024 canvas and an explicit close-up clause - in all three arms. That is where
# the face numbers come from. The wide arms above stay exactly as they are, because the
# question "did the scene survive" needs the scene in shot.
#
# THE BIAS THIS INTRODUCES IS STATED RATHER THAN HIDDEN: a close-up is IN DISTRIBUTION for
# a LoRA trained on head-and-shoulders views, so stage F is a friendlier test for arm A
# than a wide shot would be. It is the right trade - a fair crop with a stated bias beats
# an unfair crop with a hidden one - but the numbers are not a substitute for looking at
# <ID>_places.jpg.
FARMS = [("F_lora", True, True), ("F_control", False, True), ("F_words", False, False)]


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def font(sz):
    for p in ("/usr/share/fonts/google-carlito-fonts/Carlito-Bold.ttf",
              "/usr/share/fonts/adwaita-sans-fonts/AdwaitaSans-Regular.ttf",
              "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


# --------------------------------------------------------------------- library

def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def characters_with_weights():
    out = []
    for f in sorted(os.listdir(CAST)):
        if not f.endswith(".json"):
            continue
        c = load_json(os.path.join(CAST, f))
        lora = c.get("lora")
        if lora and os.path.exists(os.path.join(LORADIR, lora)):
            out.append(c["id"])
    return out


def strength_for(card):
    """The character's OWN recommended strength, not one global number.

    NIKA and PIP carry lora_strength_measured: 0.5, measured from a rendered sweep. VIRO's
    card carries none and studio/loras/character-viro.json says 0.85. Running each at what
    its own card recommends means this matrix tests the product as advertised rather than a
    setting nobody would ship."""
    if card.get("lora_strength_measured"):
        return float(card["lora_strength_measured"])
    p = os.path.join(STUDIO, "loras", "character-%s.json" % card["id"].lower())
    if os.path.exists(p):
        try:
            return float(load_json(p).get("strength"))
        except (TypeError, ValueError):
            pass
    return 0.5


def place_card(pid):
    return load_json(os.path.join(PLACEDIR, pid + ".json"))


def place_tags(pid):
    t = place_card(pid).get("tags", "")
    parts = [x.strip() for x in t.split(",")]
    return ", ".join(p for p in parts if p.lower() not in PLACE_EMPTY_NOUNS)


def style_card(sid):
    return load_json(os.path.join(STYLEDIR, sid + ".json"))


# --------------------------------------------------------------------- prompts

def negative_for(card, style=None):
    t = (card.get("tags", "") + " " + card.get("base_tags", "")).lower()
    parts = [NEG_FEMALE if "1girl" in t else NEG_MALE]
    if "child" in t:
        parts.append(NEG_CHILD)
    parts.append(NEG_BASE)
    if style and style.get("negative_add"):
        parts.append(style["negative_add"])
    return ", ".join(parts)


def positive_for(card, pid, style=None, frame=None):
    """compose.py:1476-1502's slot order, kept exactly: identity, then the base/sex slot,
    then the garment in its clean state, then the shot, then the place, then the style,
    then quality. Earlier and more specific wins on this engine, which is why the trigger
    and the tags come before the room."""
    bits = [card["id"].lower()]                       # the trigger turnaround.py captioned with
    bits.append(card.get("tags", "").strip())
    if card.get("base_tags"):
        bits.append(card["base_tags"].strip())
    wear = card.get("wear_tags") or []
    if wear:
        bits.append(wear[0].strip())
    bits.append(frame or FRAME_ANIME)
    bits.append(place_tags(pid))
    if style and style.get("tags"):
        bits.append(style["tags"].strip())
    bits.append(Q)
    return ", ".join(b for b in bits if b)


def qwen_prompt(card, pid):
    """The literal "image 1" phrasing workflow 23 says the edit model was trained on.

    "The person in image 1" and never "the man" / "the woman", so the sentence is identical
    for every character and the prompt never re-asserts the thing under test."""
    wear = (card.get("wear_tags") or ["plain clothes"])[0]
    if not wear.lower().startswith("wearing"):
        wear = "wearing " + wear
    return ("The person in image 1 is now in %s. %s. Keep their face, hair and features "
            "exactly as they are in image 1. They are %s."
            % (place_card(pid).get("prose", pid), FRAME_QWEN.capitalize(), wear))


# --------------------------------------------------------------------- graphs

def wf_anime(card, pid, lora_on, ip_on, strength, seed, style=None, frame=None,
             size=None):
    wf = load_wf(WF_ANIME)
    w, h = size or (AW, AH)
    set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
    set_path(wf, "2.inputs.image", card.get("sheet") or "sheet_viro.png")
    set_path(wf, "4.inputs.weight", IP_WEIGHT if ip_on else 0.0)
    set_path(wf, "5.inputs.text", positive_for(card, pid, style, frame))
    set_path(wf, "6.inputs.text", negative_for(card, style))
    set_path(wf, "7.inputs.width", w)
    set_path(wf, "7.inputs.height", h)
    set_path(wf, "8.inputs.seed", seed)
    set_path(wf, "10.inputs.width", w)
    set_path(wf, "10.inputs.height", h)
    # Always present, 0.0 for the controls: LoraLoaderModelOnly is a documented no-op at
    # strength 0, so every arm submits the same graph shape.
    wf["90"] = {"class_type": "LoraLoaderModelOnly",
                "inputs": {"model": ["1", 0], "lora_name": card["lora"],
                           "strength_model": float(strength) if lora_on else 0.0}}
    for nid, node in list(wf.items()):
        if nid in ("1", "90") or not isinstance(node, dict):
            continue
        for k, v in (node.get("inputs") or {}).items():
            if isinstance(v, list) and len(v) == 2 and v[0] == "1" and v[1] == 0:
                node["inputs"][k] = ["90", 0]
    set_path(wf, "11.inputs.filename_prefix", "claude-generated/cast_proof/a")
    return wf


def wf_qwen(card, pid, sheet, seed):
    """Qwen-Image-Edit 2511 in REFERENCE mode - the sheet conditions, an empty latent is
    the canvas (node 13 samples node 20, not node 12), so a whole new scene is generated
    with the sheet as side-conditioning rather than painted over.

    NODE 11, THE NEGATIVE, IS LEFT AS SHIPPED. It reads "... photorealistic, 3d render",
    which fights the word "photograph" in the positive. That is the shipped graph and this
    arm is meant to measure the product, so it is reported rather than quietly patched."""
    wf = load_wf(WF_QWEN)
    wf.pop("9", None)      # second LoadImage, unwired here
    wf.pop("12", None)     # VAEEncode of the ref - dead in reference mode
    set_path(wf, "8.inputs.image", sheet)
    set_path(wf, "10.inputs.prompt", qwen_prompt(card, pid))
    set_path(wf, "20.inputs.width", QW)
    set_path(wf, "20.inputs.height", QH)
    set_path(wf, "13.inputs.seed", seed)
    set_path(wf, "7.inputs.strength_model", 0.0)      # style LoRA slot explicitly off
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/cast_proof/q")
    return wf


# --------------------------------------------------------------------- submission

def submit(wf, front=False):
    resp = api(HOST, "/prompt", {"prompt": wf, "client_id": str(uuid.uuid4()),
                                 "front": bool(front)})
    if "error" in resp:
        raise RuntimeError(json.dumps(resp)[:300])
    return resp["prompt_id"]


def batch(jobs, front=False, timeout=3600):
    """jobs is [(dst, workflow, label)]. Submit them all, then wait for all.

    Submitting a whole checkpoint group before waiting keeps our cells adjacent in the
    queue, so the 7 GB animagine checkpoint (or the 20 GB qwen one) is loaded once for the
    group instead of once per cell when another agent's job lands between ours.

    The output filename is read back out of /history rather than guessed as _00001_.
    make_anime_sheet.py guesses, and on 2026-08-04 an orphaned queue entry made the guess
    fetch the WRONG render. Do not reintroduce that."""
    todo = [(d, w, l) for d, w, l in jobs if not os.path.exists(d)]
    skipped = len(jobs) - len(todo)
    if skipped:
        print("  (%d cell(s) already on disk)" % skipped)
    if not todo:
        return 0
    live = []
    for dst, wf, label in todo:
        try:
            live.append((submit(wf, front), dst, label))
        except Exception as e:
            print("  %-40s FAILED to submit: %s" % (label, str(e)[:100]))
    if not live:
        return 0
    print("  submitted %d cell(s), waiting..." % len(live), flush=True)
    t0, done = time.time(), 0
    pending = list(live)
    while pending and time.time() - t0 < timeout:
        time.sleep(3.0)
        still = []
        for pid, dst, label in pending:
            try:
                hist = api(HOST, "/history/%s" % pid)
            except SystemExit:
                still.append((pid, dst, label))
                continue
            if pid not in hist:
                still.append((pid, dst, label))
                continue
            st = hist[pid].get("status", {})
            if st.get("status_str") == "error":
                print("  %-40s FAILED (execution error)" % label)
                for m in st.get("messages", [])[:3]:
                    print("      %s" % str(m)[:200])
                continue
            if not st.get("completed"):
                still.append((pid, dst, label))
                continue
            outs = []
            for _n, out in hist[pid].get("outputs", {}).items():
                for f in out.get("images", []):
                    outs.append(("%s/%s" % (f.get("subfolder", ""), f["filename"])).lstrip("/"))
            if outs and ensure_local(outs[0], dst, required=False):
                print("  %-40s %6.0f KB  [%3.0fs]" % (label, os.path.getsize(dst) / 1024.0,
                                                      time.time() - t0), flush=True)
                done += 1
            else:
                print("  %-40s NO OUTPUT" % label)
        pending = still
    for _p, _d, label in pending:
        print("  %-40s TIMED OUT" % label)
    return done


# --------------------------------------------------------------------- stages

def cell_path(cid, arm, name, make=False):
    """make=False on purpose: measure() asks for paths of arms that may not have been
    rendered (D_qwen_photo exists for VIRO alone), and creating the directory as a side
    effect of looking left empty folders behind."""
    d = os.path.join(OUT, cid, arm)
    if make:
        os.makedirs(d, exist_ok=True)
    return os.path.join(d, name + ".png")


def jobs_places(card, force):
    cid = card["id"]
    st = strength_for(card)
    jobs = []
    for arm, lora_on, ip_on in ARMS:
        for i, pid in enumerate(PLACES):
            dst = cell_path(cid, arm, "%d_%s" % (i, pid), make=True)
            if force and os.path.exists(dst):
                os.remove(dst)
            wf = wf_anime(card, pid, lora_on, ip_on, st, SEED0 + i * 101)
            jobs.append((dst, wf, "%s %s %s" % (cid, arm, pid)))
    return jobs


def jobs_faces(card, force):
    """Stage F: the same five places and seeds with the framing pinned, so the head lands
    in the same window in every arm and the crop is a fair one. See FARMS above."""
    cid = card["id"]
    st = strength_for(card)
    jobs = []
    for arm, lora_on, ip_on in FARMS:
        for i, pid in enumerate(PLACES):
            dst = cell_path(cid, arm, "%d_%s" % (i, pid), make=True)
            if force and os.path.exists(dst):
                os.remove(dst)
            wf = wf_anime(card, pid, lora_on, ip_on, st, SEED0 + i * 101,
                          frame=FRAME_FACE, size=(FW, FH))
            jobs.append((dst, wf, "%s %s %s" % (cid, arm, pid)))
    return jobs


def jobs_styles(card, force):
    cid = card["id"]
    st = strength_for(card)
    jobs = []
    seed = SEED0 + PLACES.index(STYLE_PLACE) * 101
    for sid in STYLES:
        sc = style_card(sid)
        # The third rung exists because the first two came back with NO STYLE ON THEM AT
        # ALL and "the style did not land" needs a cause. C_style_words drops both the LoRA
        # and the IPAdapter, leaving the identical prompt - so if the style appears here it
        # is the identity mechanism suppressing it, and if it does not, it is the prompt.
        for arm, lora_on, ip_on in (("C_style_lora", True, True),
                                    ("C_style_nolora", False, True),
                                    ("C_style_words", False, False),
                                    ("C_style_loraonly", True, False)):
            dst = cell_path(cid, arm, sid, make=True)
            if force and os.path.exists(dst):
                os.remove(dst)
            wf = wf_anime(card, STYLE_PLACE, lora_on, ip_on, st, seed, style=sc)
            jobs.append((dst, wf, "%s %s %s" % (cid, arm, sid)))
    return jobs


def jobs_qwen(card, force):
    cid = card["id"]
    jobs = []
    sheets = [("D_qwen_sheet", card.get("sheet"))]
    photo = "sheet_photo_%s.png" % cid.lower()
    if os.path.exists(os.path.join(COMFY, "input", photo)):
        # Only VIRO has one. It is the single case where anime-sheet and photo-sheet can be
        # compared on the same engine at the same seeds.
        sheets.append(("D_qwen_photo", photo))
    for arm, sheet in sheets:
        if not sheet or not os.path.exists(os.path.join(COMFY, "input", sheet)):
            print("  %s %s: sheet %r not in ComfyUI/input - skipped" % (cid, arm, sheet))
            continue
        for i, pid in enumerate(PLACES):
            dst = cell_path(cid, arm, "%d_%s" % (i, pid), make=True)
            if force and os.path.exists(dst):
                os.remove(dst)
            jobs.append((dst, wf_qwen(card, pid, sheet, SEED0 + i * 101),
                         "%s %s %s" % (cid, arm, pid)))
    return jobs


# --------------------------------------------------------------------- head crops

def _np():
    try:
        import numpy as np
        return np
    except ImportError:
        raise SystemExit("numpy is needed to measure. System python3 here has none - "
                         "re-run with ~/ComfyUI/venv/bin/python")


# THERE IS NO FACE DETECTOR ON THIS BOX, and faking one was worse than doing without.
# cv2, insightface, facexlib and dlib are all absent (checked, in both the system python
# and ComfyUI's venv), and the only custom nodes installed are IPAdapter_plus, Chatterbox
# and TTS-Audio-Suite - none of which ships a bbox model.
#
# A SKIN-HUE BLOB DETECTOR WAS BUILT AND THROWN AWAY. Recording why, so the next agent
# does not spend the same hour: across seven test images the three characters produced
# three DIFFERENT failure modes.
#   - PIP's ginger hair sits at the same hue as skin, so hair and face merge into one blob.
#     That one is actually harmless: the merged blob is the head.
#   - NIKA's skin is pale enough (saturation around 30 of 255) that any threshold which
#     excludes a background also excludes her face. Her reference sheet produced an
#     essentially empty mask and the box landed on one eye.
#   - VIRO's sheet and turnaround views have a CREAM background, which is squarely inside
#     every skin hue window there is, and his jaw is connected to it. Morphological opening
#     plus rejecting border-touching blobs did not separate them; the box landed on the
#     backdrop.
# Two more rounds of threshold tuning moved the failures around rather than removing them.
#
# SO THE CROP IS DETERMINISTIC AND HAND-VERIFIED INSTEAD. A head box is three numbers -
# centre x, centre y and side, as fractions of the frame - fixed per image family, chosen
# by looking at the renders and then checked against every single crop in <ID>_faces.jpg.
# Cells where it misses are listed in OVERRIDES with their own three numbers, or in
# EXCLUDE if there is no head in the frame to crop at all, and both lists are printed with
# the results. This is dumber than a detector and it is honest: every number in
# _metrics.json can be reproduced from the constants below plus the PNGs.

# (centre x, centre y, side) as fractions - x of the width, y and side of the HEIGHT.
HEAD = {
    "anime": (0.50, 0.235, 0.32),      # 896x1152 "upper body, looking at the viewer"
    "qwen": (0.50, 0.235, 0.30),       # 1152x1440 "waist-up photograph"
    "face": (0.50, 0.45, 0.56),        # 1024x1024 stage F, framing pinned
}
# The reference sheets are square and were composed by a different tool, so they get their
# own boxes, one per file, read off the image by eye.
SHEET_HEAD = {
    "sheet_anime_viro.png": (0.44, 0.36, 0.58),
    "sheet_anime_nika.png": (0.50, 0.30, 0.46),
    "sheet_anime_pip.png": (0.53, 0.31, 0.46),
    "sheet_photo_viro.png": (0.55, 0.30, 0.48),
}
# key -> (cx, cy, side). Populated by LOOKING at <ID>_faces.jpg and fixing what missed.
OVERRIDES = {}
# Cells with no croppable head at all (subject turned away, or too small in frame).
EXCLUDE = set()


def frac_box(frac, W, H):
    cx, cy, side = frac
    s = side * H
    x0 = min(max(cx * W - s / 2.0, 0), W - s)
    y0 = min(max(cy * H - s / 2.0, 0), H - s)
    return (int(round(x0)), int(round(y0)), int(round(x0 + s)), int(round(y0 + s)))


def head_box(path, key=None, family="anime"):
    """Returns ((x0,y0,x1,y1), method). See the block comment above for the whole rule."""
    im = Image.open(path)
    W, H = im.size
    if key and key in OVERRIDES:
        return frac_box(OVERRIDES[key], W, H), "override"
    base = os.path.basename(path)
    if base in SHEET_HEAD:
        return frac_box(SHEET_HEAD[base], W, H), "sheet"
    return frac_box(HEAD.get(family, HEAD["anime"]), W, H), family


def crop_feats(path, box, size=96):
    np = _np()
    im = Image.open(path).convert("RGB").crop(box).resize((size, size), Image.LANCZOS)
    g = np.asarray(im.convert("L"), dtype=np.float64)
    g = (g - g.mean()) / (g.std() + 1e-6)
    hsv = np.asarray(im.convert("HSV"), dtype=np.float64)
    w = (hsv[:, :, 1] / 255.0) * (hsv[:, :, 2] / 255.0)
    hist, _ = np.histogram(hsv[:, :, 0], bins=36, range=(0, 256), weights=w)
    hist = hist / (hist.sum() + 1e-9)
    return {"g": g, "h": hist, "crop": im}


def d_struct(a, b):
    np = _np()
    return float(np.abs(a["g"] - b["g"]).mean() * 100.0)


def d_hue(a, b):
    np = _np()
    x, y = a["h"], b["h"]
    return float(0.5 * np.sum((x - y) ** 2 / (x + y + 1e-9)) * 100.0)


def pairwise(feats):
    n = len(feats)
    if n < 2:
        return None, None
    s, h, k = 0.0, 0.0, 0
    for i in range(n):
        for j in range(i + 1, n):
            s += d_struct(feats[i], feats[j])
            h += d_hue(feats[i], feats[j])
            k += 1
    return s / k, h / k


# --------------------------------------------------------------------- contact sheets

def cell_image(path, w, h, label, missing="not rendered"):
    if path and os.path.exists(path):
        im = Image.open(path).convert("RGB").resize((w, h), Image.LANCZOS)
    else:
        im = Image.new("RGB", (w, h), (40, 40, 44))
        d = ImageDraw.Draw(im)
        d.text((10, h // 2), missing, fill=(180, 90, 90), font=font(20))
    d = ImageDraw.Draw(im)
    f = font(max(14, w // 24))
    bb = d.textbbox((0, 0), label, font=f)
    d.rectangle([0, 0, w, bb[3] + 10], fill=(0, 0, 0))
    d.text((6, 4), label, fill=(255, 215, 60), font=f)
    return im


def grid(rows, dst, cell_w=360, aspect=None, title=None):
    """rows: [(row_label, [(cell_label, path), ...]), ...]"""
    if aspect is None:
        aspect = AH / float(AW)
    cell_h = int(round(cell_w * aspect))
    ncol = max(len(cells) for _l, cells in rows)
    th = 40 if title else 0
    sheet = Image.new("RGB", (ncol * cell_w, th + len(rows) * cell_h), (18, 18, 20))
    if title:
        ImageDraw.Draw(sheet).text((10, 8), title, fill=(255, 255, 255), font=font(24))
    for r, (rlabel, cells) in enumerate(rows):
        for c, (clabel, path) in enumerate(cells):
            im = cell_image(path, cell_w, cell_h, "%s | %s" % (rlabel, clabel))
            sheet.paste(im, (c * cell_w, th + r * cell_h))
    sheet.save(dst, quality=90)
    return dst


def face_grid(rows, dst, cell=220, title=None):
    """rows: [(row_label, [(cell_label, PIL crop or None), ...])]"""
    ncol = max(len(cells) for _l, cells in rows)
    th = 40 if title else 0
    sheet = Image.new("RGB", (ncol * cell, th + len(rows) * cell), (18, 18, 20))
    if title:
        ImageDraw.Draw(sheet).text((10, 8), title, fill=(255, 255, 255), font=font(24))
    for r, (rlabel, cells) in enumerate(rows):
        for c, (clabel, crop) in enumerate(cells):
            if crop is None:
                im = Image.new("RGB", (cell, cell), (40, 40, 44))
            else:
                im = crop.resize((cell, cell), Image.LANCZOS)
            d = ImageDraw.Draw(im)
            f = font(15)
            t = "%s|%s" % (rlabel, clabel)
            bb = d.textbbox((0, 0), t, font=f)
            d.rectangle([0, 0, cell, bb[3] + 8], fill=(0, 0, 0))
            d.text((4, 3), t, fill=(255, 215, 60), font=f)
            sheet.paste(im, (c * cell, th + r * cell))
    sheet.save(dst, quality=92)
    return dst


# --------------------------------------------------------------------- measure

def measure(cids):
    np = _np()
    os.makedirs(OUT, exist_ok=True)
    report = {"method": "see cast_proof.py module docstring", "places": PLACES,
              "styles": STYLES, "style_place": STYLE_PLACE, "seed0": SEED0,
              "ip_weight": IP_WEIGHT, "characters": {}}
    armA_feats = {}          # cid -> {place_key: feats}, for the different-people baseline
    excluded = []
    overridden = []

    def feats_for(cid, arm, name, family="anime"):
        """None if the cell is missing or is on the EXCLUDE list."""
        key = "%s/%s/%s" % (cid, arm, name)
        if key in EXCLUDE:
            excluded.append(key)
            return None
        p = cell_path(cid, arm, name)
        if not os.path.exists(p):
            return None
        box, meth = head_box(p, key, family)
        if meth == "override":
            overridden.append(key)
        return crop_feats(p, box)

    for cid in cids:
        card = load_json(os.path.join(CAST, cid + ".json"))
        st = strength_for(card)
        entry = {"lora": card.get("lora"), "strength": st, "sheet": card.get("sheet"),
                 "head_box": HEAD["anime"], "arms": {}}

        rows_full, rows_face = [], []
        for arm, _l, _ip in ARMS:
            feats, cells_full, cells_face = {}, [], []
            for i, pid in enumerate(PLACES):
                key = "%d_%s" % (i, pid)
                cells_full.append((pid, cell_path(cid, arm, key)))
                f = feats_for(cid, arm, key)
                if f:
                    feats[key] = f
                cells_face.append((pid[:11], f["crop"] if f else None))
            s, h = pairwise(list(feats.values()))
            entry["arms"][arm] = {"n": len(feats),
                                  "within_struct": None if s is None else round(s, 1),
                                  "within_hue": None if h is None else round(h, 1)}
            if arm == "A_lora":
                armA_feats[cid] = feats
            rows_full.append((arm, cells_full))
            rows_face.append((arm, cells_face))

        grid(rows_full, os.path.join(OUT, "%s_places.jpg" % cid.lower()),
             title="%s  -  five places the training set never contained  "
                   "(A: lora %.2f + sheet | B: sheet only | B0: tags only)" % (cid, st))
        face_grid(rows_face, os.path.join(OUT, "%s_faces.jpg" % cid.lower()),
                  title="%s  -  head crops of the WIDE arms. Framing varies between arms, "
                        "so these are not comparable - see _pinned" % cid)

        # STAGE F - framing pinned, square canvas. The numbers come from here.
        frows_full, frows_face = [], []
        for arm, _l, _ip in FARMS:
            feats, cells_full, cells_face = {}, [], []
            for i, pid in enumerate(PLACES):
                key = "%d_%s" % (i, pid)
                cells_full.append((pid, cell_path(cid, arm, key)))
                f = feats_for(cid, arm, key, family="face")
                if f:
                    feats[key] = f
                cells_face.append((pid[:11], f["crop"] if f else None))
            s, h = pairwise(list(feats.values()))
            entry["arms"][arm] = {"n": len(feats),
                                  "within_struct": None if s is None else round(s, 1),
                                  "within_hue": None if h is None else round(h, 1)}
            if arm == "F_lora":
                armA_feats[cid] = feats
            frows_full.append((arm, cells_full))
            frows_face.append((arm, cells_face))
        if any(any(p for _l, p in cs if os.path.exists(p)) for _a, cs in frows_full):
            grid(frows_full, os.path.join(OUT, "%s_pinned.jpg" % cid.lower()),
                 aspect=1.0,
                 title="%s  -  same five places, framing PINNED, so the faces are "
                       "comparable (lora %.2f)" % (cid, st))
            face_grid(frows_face, os.path.join(OUT, "%s_pinned_faces.jpg" % cid.lower()),
                      title="%s  -  head crops, framing pinned. IDENTITY IS JUDGED HERE." % cid)

        # to-sheet: distance from each cell to the character's own reference sheet
        sheet_p = os.path.join(COMFY, "input", card.get("sheet") or "")
        if os.path.exists(sheet_p):
            sb, _m = head_box(sheet_p)
            sf = crop_feats(sheet_p, sb)
            entry["sheet_box"] = SHEET_HEAD.get(os.path.basename(sheet_p))
            for arm, _l, _ip in ARMS + FARMS:
                fam = "face" if arm.startswith("F_") else "anime"
                ss, hh, k = 0.0, 0.0, 0
                for i, pid in enumerate(PLACES):
                    f = feats_for(cid, arm, "%d_%s" % (i, pid), family=fam)
                    if f:
                        ss += d_struct(f, sf)
                        hh += d_hue(f, sf)
                        k += 1
                if k and arm in entry["arms"]:
                    entry["arms"][arm]["to_sheet_struct"] = round(ss / k, 1)
                    entry["arms"][arm]["to_sheet_hue"] = round(hh / k, 1)

        # style rows
        srows_full, srows_face = [], []
        for arm, base_arm in (("C_style_lora", "A_lora"), ("C_style_nolora", "B_control"),
                              ("C_style_words", "B0_words"),
                              ("C_style_loraonly", "A_lora")):
            cells_full, cells_face, feats = [], [], []
            # the SAME place, seed and LoRA setting with no style at all - so the styled
            # cell is compared against its own unstyled twin and not across arms
            base = cell_path(cid, base_arm,
                             "%d_%s" % (PLACES.index(STYLE_PLACE), STYLE_PLACE))
            cells_full.append(("no style", base))
            bf = feats_for(cid, base_arm,
                           "%d_%s" % (PLACES.index(STYLE_PLACE), STYLE_PLACE))
            cells_face.append(("no style", bf["crop"] if bf else None))
            for sid in STYLES:
                cells_full.append((sid, cell_path(cid, arm, sid)))
                f = feats_for(cid, arm, sid)
                feats.append((sid, f))
                cells_face.append((sid[:11], f["crop"] if f else None))
            # distance from each styled cell back to the SAME cell unstyled
            if bf:
                d = {}
                for sid, f in feats:
                    if f:
                        d[sid] = {"struct_vs_unstyled": round(d_struct(f, bf), 1),
                                  "hue_vs_unstyled": round(d_hue(f, bf), 1)}
                entry.setdefault("styles", {})[arm] = d
            srows_full.append((arm.replace("C_style_", ""), cells_full))
            srows_face.append((arm.replace("C_style_", ""), cells_face))
        grid(srows_full, os.path.join(OUT, "%s_style.jpg" % cid.lower()),
             title="%s  -  %s under three styles, with and without the LoRA"
                   % (cid, STYLE_PLACE))
        face_grid(srows_face, os.path.join(OUT, "%s_style_faces.jpg" % cid.lower()),
                  title="%s  -  style head crops" % cid)

        # qwen rows
        qrows = []
        for arm in ("D_qwen_sheet", "D_qwen_photo"):
            cells = []
            any_ = False
            for i, pid in enumerate(PLACES):
                p = cell_path(cid, arm, "%d_%s" % (i, pid))
                any_ = any_ or os.path.exists(p)
                cells.append((pid, p))
            if any_:
                qrows.append((arm.replace("D_qwen_", ""), cells))
                feats, qface = [], []
                for i, pid in enumerate(PLACES):
                    f = feats_for(cid, arm, "%d_%s" % (i, pid), family="qwen")
                    if f:
                        feats.append(f)
                    qface.append((pid[:11], f["crop"] if f else None))
                face_grid([(arm.replace("D_qwen_", ""), qface)],
                          os.path.join(OUT, "%s_qwen_faces_%s.jpg"
                                       % (cid.lower(), arm.split("_")[-1])),
                          title="%s  -  qwen head crops (%s)" % (cid, arm))
                s, h = pairwise(feats)
                entry["arms"][arm] = {"n": len(feats),
                                      "within_struct": None if s is None else round(s, 1),
                                      "within_hue": None if h is None else round(h, 1)}
        if qrows:
            grid(qrows, os.path.join(OUT, "%s_qwen.jpg" % cid.lower()),
                 aspect=QH / float(QW),
                 title="%s  -  photographic engine, identity via the reference sheet" % cid)

        report["characters"][cid] = entry

    # the different-people ceiling, computed on this run's own pixels
    ids = [c for c in cids if armA_feats.get(c)]
    if len(ids) > 1:
        ss, hh, k = 0.0, 0.0, 0
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                fa, fb = armA_feats[ids[a]], armA_feats[ids[b]]
                for key in fa:
                    if key in fb:
                        ss += d_struct(fa[key], fb[key])
                        hh += d_hue(fa[key], fb[key])
                        k += 1
        if k:
            report["different_people_baseline"] = {
                "struct": round(ss / k, 1), "hue": round(hh / k, 1),
                "n_pairs": k,
                "means": "arm A cells of DIFFERENT characters at the SAME place and seed. "
                         "This is the ceiling: what the numbers look like when it is "
                         "definitely not the same person."}
    report["head_box_fractions"] = {"anime": HEAD["anime"], "qwen": HEAD["qwen"],
                                    "sheets": SHEET_HEAD}
    report["overridden_cells"] = sorted(set(overridden))
    report["excluded_cells"] = sorted(set(excluded))

    dst = os.path.join(OUT, "_metrics.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)

    # printed table
    print("\n" + "=" * 96)
    base = report.get("different_people_baseline")
    if base:
        print("DIFFERENT-PEOPLE CEILING (measured here): struct %.1f   hue %.1f   "
              "over %d cross-character pairs" % (base["struct"], base["hue"], base["n_pairs"]))
    print("lower struct/hue = the same head keeps coming back.  to_sheet = is it the RIGHT head.")
    print("%-7s %-16s %3s %8s %8s %10s %10s" %
          ("CHAR", "ARM", "N", "w-struct", "w-hue", "sheet-str", "sheet-hue"))
    for cid, e in report["characters"].items():
        for arm, v in e["arms"].items():
            print("%-7s %-16s %3d %8s %8s %10s %10s" %
                  (cid, arm, v["n"], v.get("within_struct"), v.get("within_hue"),
                   v.get("to_sheet_struct", "-"), v.get("to_sheet_hue", "-")))
    print("head box (cx,cy,side as fractions): anime %s  qwen %s" %
          (HEAD["anime"], HEAD["qwen"]))
    print("%d cell(s) hand-overridden, %d excluded" %
          (len(report["overridden_cells"]), len(report["excluded_cells"])))
    print("=" * 96)
    print("\n%s\nNOW LOOK AT THE SHEETS. The numbers do not decide this." % dst)
    return report


# --------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("characters", nargs="*")
    ap.add_argument("--stage", nargs="+", default=["A", "B", "B0", "C", "D", "F"],
                    choices=["A", "B", "B0", "C", "D", "F"])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--front", action="store_true",
                    help="reorder the pending queue (cancels nothing). Off by default so "
                         "this does not push in front of another agent's batch.")
    ap.add_argument("--measure-only", action="store_true")
    ap.add_argument("--no-measure", action="store_true")
    a = ap.parse_args()

    cids = [c.upper() for c in a.characters] or characters_with_weights()
    if not cids:
        raise SystemExit("no character card carries a `lora` whose .safetensors is on disk")
    cards = []
    for cid in cids:
        p = os.path.join(CAST, cid + ".json")
        if not os.path.exists(p):
            raise SystemExit("unknown character %r" % cid)
        cards.append(load_json(p))

    os.makedirs(OUT, exist_ok=True)
    print("characters : %s" % ", ".join(cids))
    for c in cards:
        print("  %-7s lora=%s  strength=%.2f  sheet=%s" %
              (c["id"], c.get("lora"), strength_for(c), c.get("sheet")))
    print("places     : %s" % ", ".join(PLACES))
    print("styles     : %s  (in %s)" % (", ".join(STYLES), STYLE_PLACE))

    if not a.measure_only:
        # ANIMAGINE GROUP. All anime cells for all characters in one submission, so the
        # SDXL checkpoint loads once for the whole group.
        anime = []
        for c in cards:
            if any(s in a.stage for s in ("A", "B", "B0")):
                for dst, wf, label in jobs_places(c, a.force):
                    arm = label.split()[1]
                    want = ("A" in a.stage and arm == "A_lora") or \
                           ("B" in a.stage and arm == "B_control") or \
                           ("B0" in a.stage and arm == "B0_words")
                    if want:
                        anime.append((dst, wf, label))
            if "C" in a.stage:
                anime += jobs_styles(c, a.force)
            if "F" in a.stage:
                anime += jobs_faces(c, a.force)
        if anime:
            print("\n--- animagine group: %d cell(s) ---" % len(anime))
            t0 = time.time()
            n = batch(anime, front=a.front)
            print("  %d rendered in %.0fs" % (n, time.time() - t0))

        # QWEN GROUP.
        if "D" in a.stage:
            qw = []
            for c in cards:
                qw += jobs_qwen(c, a.force)
            if qw:
                print("\n--- qwen-image-edit group: %d cell(s) ---" % len(qw))
                t0 = time.time()
                n = batch(qw, front=a.front)
                print("  %d rendered in %.0fs" % (n, time.time() - t0))

    if not a.no_measure:
        measure(cids)


if __name__ == "__main__":
    main()
