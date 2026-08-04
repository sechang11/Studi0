#!/usr/bin/env python3
"""PUT A CAST MEMBER IN A NON-ANIME STYLE.

    python3 studio/_tools/cast_style.py --stage P          # photographic reference sheets
    python3 studio/_tools/cast_style.py --stage Q          # qwen edit path, 4 places
    python3 studio/_tools/cast_style.py --stage A          # painterly on animagine, IP sweep
    python3 studio/_tools/cast_style.py --stage S          # qwen style LoRA, ref vs no ref
    python3 studio/_tools/cast_style.py --sheets           # rebuild contact sheets only

    Run it with ~/ComfyUI/venv/bin/python - the contact-sheet and metric passes need numpy
    and system python3 on this box has PIL but not numpy.

WHY THIS TOOL EXISTS

Every character in this project renders as anime, and the one attempt at a photographic
cast proof (studio/samples/cast_proof/*_qwen.jpg, top row) came back as an illustration in
every cell even though the prompt said "waist-up photograph". The cause was already
measured and is not a prompt problem: A REFERENCE SHEET IMPORTS ITS STYLE AS FORCEFULLY AS
ITS IDENTITY. All six cards point at sheet_anime_*.png, so the reference handed to
Qwen-Image-Edit is a drawing, and the model draws.

So this tool does not try to argue with the model. It changes the reference, and then it
sweeps the two other routes off the anime path to find which settings actually work.

THE FOUR STAGES, ONE QUESTION EACH

    P  Render a PHOTOGRAPHIC reference sheet - a photograph of the person, not a drawing
       of them. Qwen-Image 2512 with the style LoRA slot pinned to 0.0 by hand, and the
       word "photograph" in the prompt where it is not fighting anything.

    Q  Take that sheet through the qwen edit path (14_qwen_edit_ref.json) into four places
       the sheet has never seen, against the ANIME sheet as the control. The prompt string
       is byte-identical between the two arms, the seed is fixed per place, and the only
       difference in the graph is which PNG node 8 loads. Two questions, both of which have
       to come back yes: is it PHOTOGRAPHIC, and is it still the same person.

       A third arm, photo_negfix, exists because node 11 of that workflow ships the
       negative "... photorealistic, 3d render". That clause is aimed at the model on a
       path whose whole purpose here is to produce a photograph. It is kept as shipped in
       the two comparison arms so they stay honest, and removed in a third so the cost of
       the defect can be stated separately from the cost of the sheet.

    A  PAINTERLY ON THE ILLUSTRATION ENGINE, and this is the stage with the known trap.
       cast_proof measured that a reference sheet through IPAdapter SUPPRESSES style: at
       the workflow shipping weight 0.6, eight of nine styled cells were indistinguishable
       from the unstyled cell beside them. It measured two points, 0.6 and 0.0, so the
       actionable number - where does style start to die - was not known. This sweeps
       0.0 / 0.2 / 0.4 / 0.6 with the character LoRA held at the card value, across two
       places, with a NO-STYLE control column at every weight so that "did the style land"
       is a comparison and not an impression.

       Five columns, not four. studio/styles/oil_painting.json says in its own note that
       oil_painting must NOT be run on the anime checkpoint and that the painterly clause
       "painterly shading, visible brushstrokes" is the anime-path substitute. Both are
       rendered, because a card that tells you not to use it is worth testing once.

    S  THE QWEN STYLE-LoRA ROUTE, on characters it has not been measured on.
       illustration-1.0-qwen-image at 1.5 is recorded as giving painted illustration, and
       as turning a man into a young woman in 6 of 6 renders when given no reference while
       returning the same man when given one. That was measured on VIRO alone. It is run
       here on NIKA (already a young woman - so the failure mode recorded for VIRO cannot
       show up as itself and has to be looked for as drift) and on PIP (nine years old -
       the drift, if it is real, has somewhere very obvious to go). 1.0 is included because
       the same note says 1.0 changes the SUBJECT and leaves the medium photographic.

WHAT IS HELD CONSTANT

Seed is fixed per PLACE, so every arm at a place samples the same noise. Framing is stated
in every prompt, because this project has measured that framing left to the model drifts
and then two things vary at once. The garment is stated in every prompt for the same
reason - when a face changes it should be the face that changed, not the outfit doing the
recognising.

The trigger token and the character LoRA loader are in every anime arm, the loader at
strength 0.0 where the arm is a control, because LoraLoaderModelOnly is a documented no-op
at strength 0 and that keeps every graph the same shape.

WHAT THIS TOOL DOES NOT DO

It does not rewrite identity tags on a character card. `--write-card` adds `sheet_photo`
and a verdict field and touches nothing else.

WHAT THIS RUN MEASURED (2026-08-04, NIKA and PIP, 82 cells, all looked at)

  1. THE SHEET IS THE WHOLE FIX, AND IT IS COMPLETE. 8 of 8 cells off the anime sheet came
     back as flat cel illustration with the word "photograph" in the prompt. 8 of 8 off the
     photographic sheet came back as photographs, and the scene survived intact in every
     one - washers, snowdrifts, green library lamps, market produce. Nothing else changed
     between those two arms. If you want a photographic cast member, render a photographic
     sheet; there is no prompt that substitutes for it.

  2. THE NEGATIVE PROMPT ON THE QWEN PATH DOES NOTHING AT ALL. Node 11 of workflow 14 ships
     "... photorealistic, 3d render", which reads like the obvious culprit for a
     photographic proof coming back as illustration. It is not: the photo_sheet and
     photo_negfix arms are PIXEL-IDENTICAL, maxdiff 0 over 8 pairs. The KSampler runs at
     cfg 1.0 because of the 4-step Lightning LoRA, and at cfg 1.0 there is no
     classifier-free guidance, so the negative conditioning is never subtracted. Every
     negative on every 4-step qwen workflow in this project is decoration. Do not spend
     time authoring one, and do not blame one.

  3. WHAT THE PHOTOGRAPHIC ROUTE COSTS: the eye colour, and only for a face whose markers
     are fine. NIKA's card names one green eye and one amber eye. Counted at full crop
     resolution off nika_eyes.jpg, the heterochromia is legible in 2 of 4 photographic
     cells and absent in the other 2, against 4 of 4 on the anime path where it is a
     graphic feature the size of a coin. Her facial scar carried 4 of 4, and PIP - ginger,
     freckles, gap teeth, yellow coat - held in 4 of 4 with nothing lost. A photograph
     renders a marker at its real-world size, so a marker that only worked because
     illustration exaggerates it will not survive the trip.
     The route also FIXES a defect: PIP's anime sheet has a stray white hair tuft that his
     LoRA learned as permanent, and it is absent from all four photographic cells.

  4. IPADAPTER IS THE STYLE KILL SWITCH AND THE THRESHOLD IS BELOW 0.2. cast_proof knew
     0.6 suppressed style and 0.0 did not; the middle was unmeasured. Sweeping it, the
     collapse is immediate rather than gradual. ink_wash is the readable case because its
     whole job is removing colour: its saturation runs 8 / 27 / 28 / 26 in the library and
     20 / 26 / 35 / 33 in the market at weights 0.0 / 0.2 / 0.4 / 0.6, against no-style
     controls of 37-43 and 42-65. Its hue distance from the unstyled cell beside it falls
     from 117.6 at 0.0 to 18.6 at 0.2 - a sixfold collapse for the first fifth of a turn.
     By 0.6 all five columns are the same washed-out picture and the ROOM has gone too.
     THE SETTING IS: IPAdapter 0.0, character LoRA on at the card's measured strength.
     Nothing in between is worth having.
     IDENTITY IS NOT THE THING YOU TRADE. Counted off nika_paint_faces_market_street.jpg,
     the heterochromia is present and on the correct sides in 20 of 20 cells - every style,
     every weight, including the four with the sheet switched off entirely. The character
     LoRA at 0.5 holds her by itself. WHAT YOU ACTUALLY TRADE IS FRAMING: at IPAdapter 0.0
     the library row came back as two wide shots and three busts, so no single crop window
     fits it, while at 0.4 and 0.6 every cell is the same tight bust. The sheet was holding
     the shot size, not the face. Pin the framing in the prompt if you drop the sheet.

  5. THE STYLE LoRA ON QWEN DOES NOT NEED A REFERENCE, AND ON ONE CHARACTER THE REFERENCE
     ACTIVELY DESTROYS THE IDENTITY. The recorded claim - that illustration-1.0-qwen-image
     at 1.5 turns a man into a young woman in 6 of 6 renders without a reference and
     returns the same man with one - does not generalise. On NIKA the NO-REFERENCE arm is
     the best of the four: painted illustration, heterochromia correct and the brow scar
     present in 2 of 2. The photographic-reference arm at the same strength restyled
     correctly and returned a DIFFERENT WOMAN in 2 of 2 - dark eyes, no scar. On PIP the
     no-reference arm is also on model in 2 of 2 and the photographic reference is fine
     too. The failure recorded for VIRO is better read as the LoRA falling back to its own
     training distribution when the description does not push hard away from it, and a
     young man with long curly hair in a ponytail is the description closest to it.
     1.0 behaves as recorded: it leaves the medium photographic about half the time (2 of
     4 cells here), so it is not a style setting.

READ THE OUTPUT IN THIS ORDER
    <id>_qwen_sheets.jpg   stage Q. 2 rows (anime sheet / photo sheet) x 4 places.
                           THE PRIMARY EVIDENCE for the photographic question.
    <id>_qwen_faces.jpg    head crops of the above. IDENTITY IS JUDGED HERE.
    <id>_paint_<place>.jpg stage A. 4 IPAdapter weights x 5 style columns.
    <id>_styleLoRA.jpg     stage S. 4 arms x 2 places.
    _sheets/               the reference sheets themselves - look at these first, because
                           everything downstream inherits from them.
    _metrics.json          numbers. They rank candidates; they do not decide.
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

OUT = os.path.join(STUDIO, "samples", "cast_style")
CAST = os.path.join(STUDIO, "characters")
PLACEDIR = os.path.join(STUDIO, "places")
STYLEDIR = os.path.join(STUDIO, "styles")
LORADIR = os.path.join(COMFY, "models", "loras")

WF_T2I = "13_qwen_t2i_styled.json"       # Qwen-Image 2512, style slot on node 7
WF_REF = "14_qwen_edit_ref.json"         # Qwen-Image-Edit 2511, reference on node 8
WF_ANIME = "22_anime_kf_ipadapter.json"  # animagine + IPAdapter, sheet on node 2

L_ILLUS = "illustration-1.0-qwen-image.safetensors"

SHEET_SIDE = 1328
QW, QH = 1152, 1440       # 4:5. A waist-up figure at 16:9 puts the face on too few pixels.
AW, AH = 896, 1152        # an SDXL portrait bucket, same reason.
SEED0 = 8100

FRAME_QWEN = "waist-up photograph"
FRAME_ANIME = "upper body, looking at the viewer, centered"
Q_TAGS = "masterpiece, best quality, very aesthetic, absurdres"

# The shipped node-6 negative of workflow 22 opens "1girl, girl, female, feminine, breasts"
# - written for two male footballers and baked into the workflow. It is rebuilt rather than
# extended, exactly as cast_proof.py does, so a female character is renderable at all.
NEG_BASE = ("motion blur, blurry, overexposed, washed out, lowres, worst quality, "
            "bad anatomy, bad hands, extra limbs, watermark, signature, text")
NEG_MALE = "1girl, female, feminine, breasts, multiple boys"
NEG_FEMALE = "1boy, male focus, masculine, beard, facial hair, multiple girls"
NEG_CHILD = "adult, mature male, muscular, tall"
# NOT in NEG_BASE and that is deliberate: "photorealistic, 3d" belongs in an anime negative
# and is added there, but stage A is the only stage that wants it.
NEG_ANIME_MEDIUM = "photorealistic, 3d, western comic, multiple views"

# The sheet is a photograph, so the things to push away from it are the drawing media.
NEG_PHOTO = ("illustration, drawing, painting, anime, cartoon, comic, sketch, cel shading, "
             "lineart, 3d render, cgi, blurry, low quality, watermark, text, "
             "jpeg artifacts, deformed, extra limbs")
# Workflow 14 node 11 as shipped. Reproduced here so the two arms can be shown to differ
# in exactly one clause set.
NEG_REF_SHIPPED = ("blurry, low quality, watermark, text, deformed, extra limbs, "
                   "photorealistic, 3d render")

# Four places the sheets have never seen, spread across value and hue on purpose: a flat
# fluorescent interior, a blown-out white exterior, a warm dim interior and a busy warm
# exterior. These are four of cast_proof's five, so the qwen rows here are directly
# comparable to studio/samples/cast_proof/viro_qwen.jpg.
PLACES = ["laundromat", "snowfield", "library_reading_room", "market_street"]
# compose.py:209 strips these from a place tag string when a character is in the shot.
PLACE_EMPTY_NOUNS = ("scenery", "no humans")

PAINT_PLACES = ["market_street", "library_reading_room"]
IP_WEIGHTS = [0.0, 0.2, 0.4, 0.6]
# ("column label", style card id or None, override tag string or None)
PAINT_COLS = [
    ("none", None, None),
    ("watercolour", "watercolour", None),
    ("ink_wash", "ink_wash", None),
    ("oil_painting", "oil_painting", None),
    # studio/styles/oil_painting.json says its own tags do not work on this checkpoint and
    # names this clause as the substitute. Rendered so the card can be answered.
    ("oil_painterly", "oil_painting",
     "painterly shading, visible brushstrokes, traditional media, impasto, canvas texture"),
]

STYLE_PLACES = ["market_street", "library_reading_room"]
# ("arm label", uses reference?, sheet kind, illustration LoRA strength)
STYLE_ARMS = [
    ("noref_1.5", False, None, 1.5),
    ("photoref_1.5", True, "photo", 1.5),
    ("photoref_1.0", True, "photo", 1.0),
    ("animeref_1.5", True, "anime", 1.5),
]


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def font(sz):
    for p in ("/usr/share/fonts/google-carlito-fonts/Carlito-Bold.ttf",
              "/usr/share/fonts/adwaita-sans-fonts/AdwaitaSans-Regular.ttf",
              "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def card_path(cid):
    p = os.path.join(CAST, cid.upper() + ".json")
    if os.path.isfile(p):
        return p
    for fn in sorted(os.listdir(CAST)):
        if fn.lower() == cid.lower() + ".json":
            return os.path.join(CAST, fn)
    raise SystemExit("no character card for %s" % cid)


def load_card(cid):
    p = card_path(cid)
    return p, load_json(p)


def strength_for(card):
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
    parts = [x.strip() for x in place_card(pid).get("tags", "").split(",")]
    return ", ".join(p for p in parts if p.lower() not in PLACE_EMPTY_NOUNS)


def style_card(sid):
    return load_json(os.path.join(STYLEDIR, sid + ".json"))


def wear_prose(card):
    """wear_tags[0] is the undamaged rung. Authored as danbooru fragments for the anime
    path, so a bare fragment spliced into a qwen sentence reads "wearing clean grey school
    blazer" with no article. Qwen is a prose model and the article is free."""
    wt = card.get("wear_tags") or []
    if not wt:
        return "in plain clothes"
    w = wt[0].strip()
    if w.lower().startswith("wearing"):
        return w
    if w[:2].lower() not in ("a ", "an") and not w.lower().startswith("the "):
        w = ("an " if w[0].lower() in "aeiou" else "a ") + w
    return "wearing " + w


def neg_anime(card, style=None):
    t = (card.get("tags", "") + " " + card.get("base_tags", "")).lower()
    parts = [NEG_FEMALE if "1girl" in t else NEG_MALE]
    if "child" in t:
        parts.append(NEG_CHILD)
    parts += [NEG_ANIME_MEDIUM, NEG_BASE]
    if style and style.get("negative_add"):
        parts.append(style["negative_add"])
    return ", ".join(parts)


# ------------------------------------------------------------------ prompts

def sheet_prompt(card):
    """The photographic sheet. Every noun that makes this a PHOTOGRAPH is here, and there
    is nothing in the prompt pulling the other way, because the style slot is 0.0."""
    prose = (card.get("prose") or "").strip()
    if not prose:
        raise SystemExit("%s has no `prose` - a danbooru tag string means nothing to a "
                         "photographic model" % card["id"])
    return (", ".join([
        "A colour reference photograph of " + prose,
        wear_prose(card),
        "facing the camera directly, neutral expression",
        "even soft studio lighting",
        "plain flat neutral grey background",
        "head and shoulders",
        "sharp focus, 85mm lens, natural skin texture, fine skin pores, real photograph",
    ]) + ".")


def qwen_place_prompt(card, pid):
    """The literal "image 1" phrasing workflow 23 says the edit model was trained on. The
    sentence never says "the man" or "the woman", so it is identical for every character
    and never re-asserts the thing under test. Byte-identical across the sheet arms."""
    return ("The person in image 1 is now in %s. %s. Keep their face, hair and features "
            "exactly as they are in image 1. They are %s."
            % (place_card(pid).get("prose", pid), FRAME_QWEN.capitalize(),
               wear_prose(card)))


def qwen_noref_prompt(card, pid, painted):
    """Stage S arm noref. No reference exists, so the person has to come from words."""
    head = "A painted illustration of " if painted else "A photograph of "
    return ("%s%s, %s, in %s. %s."
            % (head, card.get("prose", ""), wear_prose(card),
               place_card(pid).get("prose", pid), FRAME_QWEN.capitalize()))


def anime_prompt(card, pid, style_tags=None):
    """compose.py:1476-1502's slot order kept exactly: identity, base/sex, garment in its
    clean state, shot, place, style, quality."""
    bits = [card["id"].lower(), card.get("tags", "").strip()]
    if card.get("base_tags"):
        bits.append(card["base_tags"].strip())
    wt = card.get("wear_tags") or []
    if wt:
        bits.append(wt[0].strip())
    bits += [FRAME_ANIME, place_tags(pid)]
    if style_tags:
        bits.append(style_tags.strip())
    bits.append(Q_TAGS)
    return ", ".join(b for b in bits if b)


# ------------------------------------------------------------------ graphs

def wf_sheet(prompt, seed):
    wf = load_wf(WF_T2I)
    set_path(wf, "10.inputs.text", prompt)
    set_path(wf, "11.inputs.text", NEG_PHOTO)
    set_path(wf, "12.inputs.width", SHEET_SIDE)
    set_path(wf, "12.inputs.height", SHEET_SIDE)
    set_path(wf, "13.inputs.seed", seed)
    # THE WHOLE POINT OF STAGE P. Node 7 is the style slot and it is written every time,
    # never trusted to be off - that is exactly how sheet_viro.png got made as a drawing.
    set_path(wf, "7.inputs.strength_model", 0.0)
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/cast_style/sheet")
    return wf


def wf_t2i_styled(prompt, seed, lora, strength):
    wf = load_wf(WF_T2I)
    set_path(wf, "10.inputs.text", prompt)
    set_path(wf, "12.inputs.width", QW)
    set_path(wf, "12.inputs.height", QH)
    set_path(wf, "13.inputs.seed", seed)
    set_path(wf, "7.inputs.lora_name", lora)
    set_path(wf, "7.inputs.strength_model", float(strength))
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/cast_style/t2i")
    return wf


def wf_ref(prompt, seed, sheet, negative=None, lora=None, strength=0.0):
    """Qwen-Image-Edit 2511 in REFERENCE mode: node 13 samples node 20 (an empty latent),
    not node 12, so a whole new scene is generated with the sheet as side-conditioning
    rather than the sheet being painted over."""
    wf = load_wf(WF_REF)
    wf.pop("9", None)      # second LoadImage, unwired here
    wf.pop("12", None)     # VAEEncode of the ref - dead in reference mode
    set_path(wf, "8.inputs.image", sheet)
    set_path(wf, "10.inputs.prompt", prompt)
    if negative is not None:
        set_path(wf, "11.inputs.prompt", negative)
    set_path(wf, "20.inputs.width", QW)
    set_path(wf, "20.inputs.height", QH)
    set_path(wf, "13.inputs.seed", seed)
    if lora:
        set_path(wf, "7.inputs.lora_name", lora)
    set_path(wf, "7.inputs.strength_model", float(strength))
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/cast_style/ref")
    return wf


def wf_anime(card, pid, ip_weight, lora_strength, seed, style=None, style_tags=None):
    wf = load_wf(WF_ANIME)
    sheet = card.get("sheet") or "sheet_viro.png"
    set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
    set_path(wf, "2.inputs.image", sheet)
    set_path(wf, "4.inputs.weight", float(ip_weight))
    set_path(wf, "5.inputs.text", anime_prompt(card, pid, style_tags))
    set_path(wf, "6.inputs.text", neg_anime(card, style))
    set_path(wf, "7.inputs.width", AW)
    set_path(wf, "7.inputs.height", AH)
    set_path(wf, "8.inputs.seed", seed)
    set_path(wf, "10.inputs.width", AW)
    set_path(wf, "10.inputs.height", AH)
    wf["90"] = {"class_type": "LoraLoaderModelOnly",
                "inputs": {"model": ["1", 0], "lora_name": card["lora"],
                           "strength_model": float(lora_strength)}}
    for nid, node in list(wf.items()):
        if nid in ("1", "90") or not isinstance(node, dict):
            continue
        for k, v in (node.get("inputs") or {}).items():
            if isinstance(v, list) and len(v) == 2 and v[0] == "1" and v[1] == 0:
                node["inputs"][k] = ["90", 0]
    set_path(wf, "11.inputs.filename_prefix", "claude-generated/cast_style/anime")
    return wf


# ------------------------------------------------------------------ submission

def submit(wf, front=True):
    resp = api(HOST, "/prompt", {"prompt": wf, "client_id": str(uuid.uuid4()),
                                 "front": bool(front)})
    if "error" in resp:
        raise RuntimeError(json.dumps(resp)[:400])
    return resp["prompt_id"]


def batch(jobs, force=False, timeout=3600):
    """jobs is [(dst_path, workflow, label)]. Submit them all, THEN wait for all.

    Each checkpoint here is a ~20 GB fp8 model on a 32 GB card. Submitting one at a time
    lets an unrelated job run between every pair of ours and the card reloads 20 GB each
    time. Submitting a whole stage keeps our cells adjacent in the queue."""
    todo = []
    for dst, wf, label in jobs:
        if os.path.exists(dst) and not force:
            print("  %-40s = exists" % label)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        todo.append((dst, wf, label))
    if not todo:
        return 0
    live = []
    for dst, wf, label in todo:
        try:
            live.append((submit(wf), dst, label))
        except Exception as e:
            print("  %-40s FAILED to submit: %s" % (label, str(e)[:160]))
    if not live:
        return 0
    print("  submitted %d cell(s), waiting..." % len(live), flush=True)
    t0, done, pending = time.time(), 0, list(live)
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
                    print("      %s" % str(m)[:220])
                continue
            if not st.get("completed"):
                still.append((pid, dst, label))
                continue
            outs = []
            for _n, out in hist[pid].get("outputs", {}).items():
                for f in out.get("images", []):
                    outs.append(("%s/%s" % (f.get("subfolder", ""), f["filename"])).lstrip("/"))
            if outs and ensure_local(outs[0], dst, required=False):
                print("  %-40s %6.0f KB  [%4.0fs]"
                      % (label, os.path.getsize(dst) / 1024, time.time() - t0), flush=True)
                done += 1
            else:
                print("  %-40s NO OUTPUT" % label)
        pending = still
    for _pid, _dst, label in pending:
        print("  %-40s TIMED OUT" % label)
    return done


def stage_input(path, name):
    """ComfyUI LoadImage reads ONLY from its own input dir."""
    dst = os.path.join(COMFY, "input", name)
    if os.path.abspath(path) != os.path.abspath(dst):
        sh("cp", path, dst)
    return name


# ------------------------------------------------------------------ stages

def sheet_path(cid):
    return os.path.join(OUT, "_sheets", "sheet_photo_%s.png" % cid.lower())


def staged_name(cid):
    """The name inside ComfyUI/input. Same convention as qwen_sheet.py, which already
    wrote sheet_photo_viro.png there - a sheet whose style you cannot read off its own
    filename is a trap, and that is exactly how sheet_viro.png got made as a drawing."""
    return "sheet_photo_%s.png" % cid.lower()


def stage_P(cids, force):
    print("\n=== STAGE P  photographic reference sheets =========================")
    jobs = []
    for i, cid in enumerate(cids):
        _p, card = load_card(cid)
        pr = sheet_prompt(card)
        print("  %-6s %s" % (cid, pr[:150]))
        jobs.append((sheet_path(cid), wf_sheet(pr, 4400 + i), "P %s" % cid))
    n = batch(jobs, force)
    for cid in cids:
        if os.path.exists(sheet_path(cid)):
            stage_input(sheet_path(cid), staged_name(cid))
            print("  staged -> %s/input/%s" % (COMFY, staged_name(cid)))
    return n


def write_cards(cids):
    """Adds `sheet_photo` and `sheet_photo_rendered` and NOTHING ELSE. Identity tags,
    wear ladders and existing verdicts on these cards are owned elsewhere."""
    for cid in cids:
        p = sheet_path(cid)
        if not os.path.exists(p):
            print("  %s has no photographic sheet - skipped" % cid)
            continue
        cp, card = load_card(cid)
        card["sheet_photo"] = staged_name(cid)
        card["sheet_photo_rendered"] = time.strftime("%Y-%m-%dT%H:%M:%S",
                                                     time.localtime(os.path.getmtime(p)))
        with open(cp, "w", encoding="utf-8") as f:
            json.dump(card, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("  %s -> sheet_photo = %s" % (cp, card["sheet_photo"]))


def stage_Q(cids, force):
    print("\n=== STAGE Q  qwen edit path, anime sheet vs photographic sheet =====")
    jobs = []
    for cid in cids:
        _p, card = load_card(cid)
        anime = card.get("sheet")
        photo = staged_name(cid)
        if not os.path.exists(os.path.join(COMFY, "input", photo)):
            print("  %s has no photographic sheet yet - run --stage P" % cid)
            continue
        for pi, pid in enumerate(PLACES):
            seed = SEED0 + pi
            pr = qwen_place_prompt(card, pid)
            for arm, sheet, neg in (("anime_sheet", anime, None),
                                    ("photo_sheet", photo, None),
                                    ("photo_negfix", photo, NEG_PHOTO)):
                dst = os.path.join(OUT, cid, "Q_%s_%d_%s.png" % (arm, pi, pid))
                jobs.append((dst, wf_ref(pr, seed, sheet, negative=neg),
                             "Q %s %-13s %s" % (cid, arm, pid)))
    return batch(jobs, force)


def stage_A(cids, force):
    print("\n=== STAGE A  painterly on animagine, IPAdapter sweep ===============")
    jobs = []
    for cid in cids:
        _p, card = load_card(cid)
        if not card.get("lora"):
            print("  %s has no trained LoRA - skipped" % cid)
            continue
        ls = strength_for(card)
        print("  %s character LoRA %s @ %.2f" % (cid, card["lora"], ls))
        for pid in PAINT_PLACES:
            seed = SEED0 + 40 + PLACES.index(pid) if pid in PLACES else SEED0 + 40
            for w in IP_WEIGHTS:
                for label, sid, override in PAINT_COLS:
                    st = style_card(sid) if sid else None
                    tags = override if override else (st.get("tags") if st else None)
                    dst = os.path.join(OUT, cid,
                                       "A_%s_ip%.1f_%s.png" % (pid, w, label))
                    jobs.append((dst, wf_anime(card, pid, w, ls, seed, st, tags),
                                 "A %s %-22s ip%.1f %s" % (cid, pid, w, label)))
    return batch(jobs, force)


def stage_S(cids, force):
    print("\n=== STAGE S  illustration LoRA on qwen, reference vs none ==========")
    jobs = []
    for cid in cids:
        _p, card = load_card(cid)
        photo = staged_name(cid)
        anime = card.get("sheet")
        for pi, pid in enumerate(STYLE_PLACES):
            seed = SEED0 + 80 + pi
            for arm, use_ref, kind, strength in STYLE_ARMS:
                dst = os.path.join(OUT, cid, "S_%s_%d_%s.png" % (arm, pi, pid))
                if use_ref:
                    sheet = photo if kind == "photo" else anime
                    if kind == "photo" and not os.path.exists(
                            os.path.join(COMFY, "input", photo)):
                        continue
                    wf = wf_ref(qwen_place_prompt(card, pid), seed, sheet,
                                lora=L_ILLUS, strength=strength)
                else:
                    wf = wf_t2i_styled(qwen_noref_prompt(card, pid, True), seed,
                                       L_ILLUS, strength)
                jobs.append((dst, wf, "S %s %-13s %s" % (cid, arm, pid)))
    return batch(jobs, force)


# ------------------------------------------------------------------ contact sheets

def grid(cells, cols, out, title, cw=520, pad=4, bar=26):
    """cells is [(path, label)] in row-major order."""
    rows = (len(cells) + cols - 1) // cols
    ims = []
    ch = cw
    for p, _l in cells:
        if p and os.path.exists(p):
            im = Image.open(p).convert("RGB")
            ch = int(cw * im.height / im.width)
            break
    for p, l in cells:
        if p and os.path.exists(p):
            im = Image.open(p).convert("RGB").resize((cw, ch), Image.LANCZOS)
        else:
            im = Image.new("RGB", (cw, ch), (24, 24, 24))
        ims.append((im, l))
    W = cols * cw + (cols + 1) * pad
    H = rows * (ch + bar) + (rows + 1) * pad + 34
    sheet = Image.new("RGB", (W, H), (16, 16, 16))
    d = ImageDraw.Draw(sheet)
    d.text((8, 8), title, font=font(21), fill=(255, 255, 255))
    for i, (im, l) in enumerate(ims):
        r, c = divmod(i, cols)
        x = pad + c * (cw + pad)
        y = 34 + pad + r * (ch + bar + pad)
        d.rectangle([x, y, x + cw, y + bar - 2], fill=(0, 0, 0))
        d.text((x + 5, y + 4), l, font=font(15), fill=(255, 200, 90))
        sheet.paste(im, (x, y + bar))
    sheet.save(out, quality=92)
    print("  %s  (%dx%d)" % (out, sheet.width, sheet.height))


def facecrop(p, box, side=300):
    """A fixed head box, three fractions of the frame, set by looking at the renders.
    THERE IS NO FACE DETECTOR ON THIS BOX. The box is square and generous enough to hold
    hair, because hair colour is one of this project's load-bearing identity markers."""
    if not p or not os.path.exists(p):
        return Image.new("RGB", (side, side), (24, 24, 24))
    im = Image.open(p).convert("RGB")
    cx, cy, s = box
    half = s * min(im.width, im.height) / 2.0
    x, y = cx * im.width, cy * im.height
    l = max(0, int(x - half)); t = max(0, int(y - half))
    r = min(im.width, int(x + half)); b = min(im.height, int(y + half))
    return im.crop((l, t, r, b)).resize((side, side), Image.LANCZOS)


def facegrid(cells, cols, out, title, side=440, pad=4, bar=24):
    """cells is [(path, label, box)] - the box is per cell, see BOX_QWEN."""
    rows = (len(cells) + cols - 1) // cols
    W = cols * side + (cols + 1) * pad
    H = rows * (side + bar) + (rows + 1) * pad + 34
    sheet = Image.new("RGB", (W, H), (16, 16, 16))
    d = ImageDraw.Draw(sheet)
    d.text((8, 8), title, font=font(21), fill=(255, 255, 255))
    for i, (p, l, box) in enumerate(cells):
        r, c = divmod(i, cols)
        x = pad + c * (side + pad)
        y = 34 + pad + r * (side + bar + pad)
        d.rectangle([x, y, x + side, y + bar - 2], fill=(0, 0, 0))
        d.text((x + 5, y + 3), l, font=font(14), fill=(255, 200, 90))
        sheet.paste(facecrop(p, box, side), (x, y + bar))
    sheet.save(out, quality=92)
    print("  %s" % out)


# ------------------------------------------------------------------ metrics

def _np():
    try:
        import numpy as np
        return np
    except ImportError:
        raise SystemExit("numpy needed for the metric pass - run this with "
                         "~/ComfyUI/venv/bin/python")


def arr(p, n=256):
    np = _np()
    im = Image.open(p).convert("RGB").resize((n, n), Image.LANCZOS)
    return np.asarray(im).astype("float32")


def rgb_delta(a, b):
    """Mean absolute RGB difference, 0-255. Blunt on purpose: at a fixed seed two cells
    that differ only in a style LoRA share a composition, so a large number here IS the
    style. It says nothing about WHICH style."""
    np = _np()
    return float(np.abs(a - b).mean())


def sat_mean(p):
    np = _np()
    im = Image.open(p).convert("HSV").resize((128, 128), Image.LANCZOS)
    return float(np.asarray(im)[:, :, 1].mean())


def hue_chi2(pa, pb, bins=36):
    """Saturation x value weighted hue histogram, chi-square, x100. Grey background and
    black shadow do not vote."""
    np = _np()
    hs = []
    for p in (pa, pb):
        a = np.asarray(Image.open(p).convert("HSV").resize((128, 128),
                                                           Image.LANCZOS)).astype("float32")
        w = (a[:, :, 1] / 255.0) * (a[:, :, 2] / 255.0)
        h = (a[:, :, 0] / 256.0 * bins).astype("int32").clip(0, bins - 1)
        hist = np.bincount(h.ravel(), weights=w.ravel(), minlength=bins)
        s = hist.sum()
        hs.append(hist / s if s > 0 else hist)
    a, b = hs
    d = a + b
    return float((((a - b) ** 2) / np.where(d == 0, 1, d)).sum() * 100)


# ------------------------------------------------------------------ report

# Head boxes: cx / cy / side as fractions of the frame, side measured against the SHORT
# edge. THERE IS NO FACE DETECTOR ON THIS BOX, so these are set by looking at the renders
# and then checked against every crop in the face grid.
#
# THE BOX HAS TO BE PER ARM, and that is itself a result rather than a nuisance. The anime
# sheet puts the head high and small; the photographic sheet puts it lower and larger, and
# for PIP it changes the FRAMING outright - his wear clause names a boot on each foot, the
# photographic sheet drew the boots, and every downstream cell then came back full-body in
# spite of "waist-up photograph" in the prompt. One crop window across both arms would have
# measured that framing difference and called it identity drift.
BOX_QWEN = {
    "NIKA": {"anime": (0.50, 0.36, 0.42), "photo": (0.50, 0.32, 0.46)},
    "PIP":  {"anime": (0.50, 0.27, 0.30), "photo": (0.50, 0.30, 0.32)},
}
# (character, arm-kind, place) -> box, for the cells the family box misses.
BOX_OVERRIDES = {
    ("NIKA", "photo", "laundromat"): (0.31, 0.34, 0.40),
}

# Stage A. (character, place, weight) -> box. Checked against every crop.
BOX_PAINT = {
    ("NIKA", "market_street", "0.0"): (0.50, 0.275, 0.30),
    ("NIKA", "market_street", "0.2"): (0.50, 0.345, 0.30),
    ("NIKA", "market_street", "0.4"): (0.50, 0.355, 0.30),
    ("NIKA", "market_street", "0.6"): (0.50, 0.375, 0.30),
    # THIS ONE CANNOT BE MADE TO WORK AND THAT IS THE RESULT. At IPAdapter 0.0 in the
    # library the framing is not held at all: the no-style and ink_wash cells are wide
    # shots with the figure at a tenth of the frame height while the watercolour and oil
    # cells are busts. No single box fits the row. The sheet was doing framing work, and
    # turning it off to get the style back costs you that. Judge identity for this place
    # off market_street, where all five cells at every weight are comparable.
    ("NIKA", "library_reading_room", "0.0"): (0.50, 0.230, 0.28),
    ("NIKA", "library_reading_room", "0.2"): (0.50, 0.320, 0.30),
    ("NIKA", "library_reading_room", "0.4"): (0.50, 0.345, 0.30),
    ("NIKA", "library_reading_room", "0.6"): (0.50, 0.360, 0.30),
}


def box_for(cid, arm, pid):
    kind = "anime" if arm == "anime_sheet" else "photo"
    fam = BOX_QWEN.get(cid, {"anime": (0.5, 0.30, 0.36), "photo": (0.5, 0.32, 0.44)})
    return BOX_OVERRIDES.get((cid, kind, pid), fam[kind])


# The eye strip. Only characters whose identity turns on an EYE need one; NIKA's card
# names one green eye and one amber eye and nothing at head-crop scale can settle whether
# a photograph delivered that. Boxes are per place, tuned by looking, and the strip is
# letterboxed to the eye line so the count can be made at full resolution.
BOX_EYES = {
    "NIKA": {"_sheet": (0.500, 0.355, 0.30), "laundromat": (0.315, 0.365, 0.26),
             "snowfield": (0.500, 0.285, 0.26),
             "library_reading_room": (0.505, 0.345, 0.22),
             "market_street": (0.505, 0.295, 0.24)},
}


def eyestrip(cid, celldir, out, side=560):
    boxes = BOX_EYES[cid]
    cells = [(sheet_path(cid), "SHEET", boxes["_sheet"])]
    for pi, pid in enumerate(PLACES):
        p = os.path.join(celldir, "Q_photo_sheet_%d_%s.png" % (pi, pid))
        if os.path.exists(p) and pid in boxes:
            cells.append((p, pid, boxes[pid]))
    h = int(side * 0.62)
    im = Image.new("RGB", (len(cells) * side + (len(cells) + 1) * 4, h + 66), (16, 16, 16))
    d = ImageDraw.Draw(im)
    d.text((8, 8), "%s photographic route - EYE ZOOM, full resolution. Count the marker "
                   "here, not on the head crop." % cid, font=font(20), fill=(255, 255, 255))
    for i, (p, l, b) in enumerate(cells):
        src = Image.open(p).convert("RGB")
        cx, cy, s = b
        half = s * min(src.size) / 2
        x, y = cx * src.width, cy * src.height
        c = src.crop((int(x - half), int(y - half * 0.62),
                      int(x + half), int(y + half * 0.62))).resize((side, h), Image.LANCZOS)
        X = 4 + i * (side + 4)
        d.text((X + 4, 38), l, font=font(20), fill=(255, 200, 90))
        im.paste(c, (X, 62))
    im.save(out, quality=95)
    print("  %s" % out)


def sheets(cids):
    print("\n=== CONTACT SHEETS ================================================")
    os.makedirs(OUT, exist_ok=True)
    metrics = {}
    for cid in cids:
        d = os.path.join(OUT, cid)
        if not os.path.isdir(d):
            continue
        low = cid.lower()
        arms = ["anime_sheet", "photo_sheet", "photo_negfix"]

        # ---- stage Q
        cells, fcells = [], []
        for arm in arms:
            for pi, pid in enumerate(PLACES):
                p = os.path.join(d, "Q_%s_%d_%s.png" % (arm, pi, pid))
                cells.append((p, "%s | %s" % (arm, pid)))
                fcells.append((p, "%s | %s" % (arm, pid), box_for(cid, arm, pid)))
        if any(os.path.exists(p) for p, _ in cells):
            grid(cells, len(PLACES), os.path.join(OUT, "%s_qwen_sheets.jpg" % low),
                 "%s  -  qwen edit path.  Row 1 ANIME sheet (control), row 2 PHOTOGRAPHIC "
                 "sheet, row 3 photographic sheet + repaired negative" % cid)
            facegrid(fcells, len(PLACES),
                     os.path.join(OUT, "%s_qwen_faces.jpg" % low),
                     "%s  -  qwen edit path, head crops.  IDENTITY IS JUDGED HERE" % cid)
            if cid in BOX_EYES:
                eyestrip(cid, d, os.path.join(OUT, "%s_eyes.jpg" % low))

        # ---- stage A
        for pid in PAINT_PLACES:
            cells = []
            for w in IP_WEIGHTS:
                for label, _sid, _ov in PAINT_COLS:
                    p = os.path.join(d, "A_%s_ip%.1f_%s.png" % (pid, w, label))
                    cells.append((p, "ip %.1f | %s" % (w, label)))
            if any(os.path.exists(p) for p, _ in cells):
                grid(cells, len(PAINT_COLS),
                     os.path.join(OUT, "%s_paint_%s.jpg" % (low, pid)),
                     "%s  -  painterly on animagine, %s.  Rows = IPAdapter weight "
                     "(sheet strength), columns = style.  Column 1 is the no-style control"
                     % (cid, pid), cw=430)
                # The head box moves DOWN as the IPAdapter weight rises, because the sheet
                # tightens the framing from a wide shot to a bust. One box across the sweep
                # would have measured that and called it drift.
                fcells = []
                for w in IP_WEIGHTS:
                    for label, _sid, _ov in PAINT_COLS:
                        fcells.append((os.path.join(d, "A_%s_ip%.1f_%s.png"
                                                    % (pid, w, label)),
                                       "ip %.1f | %s" % (w, label),
                                       BOX_PAINT.get((cid, pid, "%.1f" % w),
                                                     (0.50, 0.30 + 0.03 * w / 0.2, 0.30))))
                facegrid(fcells, len(PAINT_COLS),
                         os.path.join(OUT, "%s_paint_faces_%s.jpg" % (low, pid)),
                         "%s  -  painterly sweep head crops, %s.  DID THE PERSON SURVIVE?"
                         % (cid, pid), side=340)

        # ---- stage S
        cells, fcells = [], []
        for arm, _u, kind, _s in STYLE_ARMS:
            for pi, pid in enumerate(STYLE_PLACES):
                p = os.path.join(d, "S_%s_%d_%s.png" % (arm, pi, pid))
                cells.append((p, "%s | %s" % (arm, pid)))
                fcells.append((p, "%s | %s" % (arm, pid),
                               box_for(cid, "anime_sheet" if kind == "anime"
                                       else "photo_sheet", pid)))
        if any(os.path.exists(p) for p, _ in cells):
            grid(cells, len(STYLE_PLACES),
                 os.path.join(OUT, "%s_styleLoRA.jpg" % low),
                 "%s  -  illustration-1.0-qwen-image on qwen.  noref / photo ref 1.5 / "
                 "photo ref 1.0 / anime ref 1.5" % cid, cw=520)
            facegrid(fcells, len(STYLE_PLACES),
                     os.path.join(OUT, "%s_styleLoRA_faces.jpg" % low),
                     "%s  -  style LoRA on qwen, head crops" % cid)

        # ---- numbers
        m = {"paint": {}, "qwen": {}}
        for pid in PAINT_PLACES:
            for w in IP_WEIGHTS:
                ctrl = os.path.join(d, "A_%s_ip%.1f_none.png" % (pid, w))
                if not os.path.exists(ctrl):
                    continue
                ca = arr(ctrl)
                for label, _sid, _ov in PAINT_COLS:
                    if label == "none":
                        continue
                    p = os.path.join(d, "A_%s_ip%.1f_%s.png" % (pid, w, label))
                    if not os.path.exists(p):
                        continue
                    m["paint"]["%s|%.1f|%s" % (pid, w, label)] = {
                        "rgb_delta_vs_control": round(rgb_delta(ca, arr(p)), 2),
                        "hue_vs_control": round(hue_chi2(ctrl, p), 2),
                        "sat_mean": round(sat_mean(p), 2),
                        "sat_mean_control": round(sat_mean(ctrl), 2),
                    }
        for pi, pid in enumerate(PLACES):
            base = os.path.join(d, "Q_anime_sheet_%d_%s.png" % (pi, pid))
            for arm in arms[1:]:
                p = os.path.join(d, "Q_%s_%d_%s.png" % (arm, pi, pid))
                if os.path.exists(base) and os.path.exists(p):
                    m["qwen"]["%s|%s" % (pid, arm)] = {
                        "rgb_delta_vs_anime_sheet": round(rgb_delta(arr(base), arr(p)), 2),
                        "sat_mean": round(sat_mean(p), 2),
                        "sat_mean_anime_sheet": round(sat_mean(base), 2),
                    }
        metrics[cid] = m
    with open(os.path.join(OUT, "_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print("  %s/_metrics.json" % OUT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("characters", nargs="*", default=None)
    ap.add_argument("--stage", nargs="*", default=["P", "Q", "A", "S"])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--sheets", action="store_true", help="contact sheets only")
    ap.add_argument("--write-card", action="store_true",
                    help="set `sheet_photo` on the character card and nothing else")
    a = ap.parse_args()

    cids = [c.upper() for c in (a.characters or ["NIKA", "PIP"])]
    os.makedirs(OUT, exist_ok=True)
    if a.write_card:
        write_cards(cids)
        return
    if a.sheets:
        sheets(cids)
        return
    stages = [s.upper() for s in a.stage]
    if "P" in stages:
        stage_P(cids, a.force)
    if "Q" in stages:
        stage_Q(cids, a.force)
    if "A" in stages:
        stage_A(cids, a.force)
    if "S" in stages:
        stage_S(cids, a.force)
    sheets(cids)


if __name__ == "__main__":
    main()
