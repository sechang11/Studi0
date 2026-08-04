#!/usr/bin/env python3
"""Does a character survive on the QWEN engine, and can you restyle them?

    python3 studio/_tools/qwen_character.py                        # VIRO, every stage
    python3 studio/_tools/qwen_character.py --subject HALE PLAIN   # the generalisation run
    python3 studio/_tools/qwen_character.py --subject all --stage B2 C
    python3 studio/_tools/qwen_character.py --sheets               # contact sheets only

THE QUESTION THIS ANSWERS

VIRO has a trained character LoRA. It is an ANIMAGINE LoRA, and this project has already
proved from pixels that a LoRA is a delta on specific weights - animagine's does nothing on
Qwen. So on the qwen engine there is no trained identity mechanism at all, and the honest
question is what is left: a written description, a reference sheet through Qwen-Image-Edit,
the multiple-angles LoRA, Relight, and a qwen-native style LoRA.

WHY THIS TOOL IS NOW MULTI-SUBJECT

The 2026-08-03 run measured all of the above on VIRO and only VIRO, and the resulting
craft/CHARACTER_ON_QWEN.md says so in its own limitations section: "A face with fewer
distinctive markers than long curly hair plus an ear stud may drift more." That is a
testable claim and it was left untested. So the subject is now a parameter and three are
defined:

    VIRO    the original. Young man, HIGH marker count (long curly hair, ponytail, gold
            ear stud, a numbered teal jersey). Kept byte-identical - its output still
            lands in samples/qwen_character/ and not a subdirectory - so the measurements
            already written up stay reproducible.
    HALE    46, female, HIGH marker count but a DIFFERENT KIND of marker: glasses, a white
            streak, a jade stud. Tests whether the reference-sheet lock is about VIRO's
            hair or about references in general, and whether AGE survives a style LoRA
            whose training distribution is young anime women.
    PLAIN   early forties, male, DELIBERATELY ZERO distinctive markers - short brown hair,
            brown eyes, clean-shaven, a plain grey sweatshirt. This is the direct test of
            the caveat above. If the reference sheet holds THIS face it holds anything; if
            it does not, the doc's ranking needs a marker-count caveat attached to it.

PLAIN is not a cast member and must never become one. It is a control, and the moment
somebody "improves" it by adding a scar or a stud the experiment is destroyed.

WHAT IS HELD CONSTANT AND WHY

Framing is written into every prompt ("waist-up photograph"). The turnaround tool learned
this the hard way: when framing is left to the model it drifts, and then two things vary at
once and you cannot attribute the difference. Same for the garment - it is stated in every
cell, so that when a face changes it is the FACE that changed and not the outfit doing the
recognising for you.

Seed is fixed per PLACE, so arm A and arm B1 and arm B2 for the same place all sample the
same noise. The only difference between those cells is the mechanism under test. Seeds are
identical ACROSS SUBJECTS too, so a HALE cell and a PLAIN cell of the same place differ
only in the person.

THE FOUR IDENTITY ARMS ARE A LADDER, ONE VARIABLE PER RUNG

    A     no reference at all, description only        the control
    B1    reference = the sheet the films actually use, literal "image 1" phrasing
    B2    reference = a style-matched photographic sheet, literal "image 1" phrasing
    B3    reference = the same photographic sheet, the phrasing short.py actually emits

    A  -> B2   is the value of having a reference at all
    B1 -> B2   is the cost of the sheet being a different STYLE from the target
    B2 -> B3   is the cost of the prompt phrasing, which workflow 23 warns about and
               scripts/short.py does not follow

CONTACT SHEETS COME IN PAIRS. A full-frame grid shows whether the scene worked; a
face-crop grid shows whether the PERSON held. Identity has to be judged on the face crop,
because at full-frame a matching jersey reads as a matching character and it is not.

SUBMISSION IS BATCHED AND JUMPS THE QUEUE, deliberately. Each checkpoint here is a ~20 GB
fp8 model on a 32 GB card. If these cells are submitted one at a time onto a box that is
also grinding a video batch, an unrelated job runs between every pair of ours and the card
reloads 20 GB each time - the render becomes model-loading with a little sampling attached.
So a stage submits ALL its cells at once with ComfyUI's `front` flag (server.py:1072), which
REORDERS the pending queue and cancels nothing. Everyone else's work still runs, after ours.
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

OUT_BASE = os.path.join(STUDIO, "samples", "qwen_character")

T2I = "13_qwen_t2i_styled.json"        # Qwen-Image 2512, no reference
REF = "14_qwen_edit_ref.json"          # Qwen-Image-Edit 2511, reference images
ANG = "32_qwen_turnaround.json"        # 2511 + multiple-angles LoRA
EDT = "03_qwen_image_edit.json"        # Qwen-Image-Edit 2509, base for Relight

L_ILLUS   = "illustration-1.0-qwen-image.safetensors"
L_STORY   = "qwen_image_2512_storybook_anime_lora.safetensors"
L_MODERN  = "qwen_image_modern_anime_lora.safetensors"
L_RELIGHT = "Qwen-Image-Edit-2509-Relight.safetensors"
L_LIGHT09 = "Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors"

FRAME = "waist-up photograph"

# ---------------------------------------------------------------- subjects
#
# `prose` is the field the qwen engine uses; danbooru tags mean nothing to a photographic
# model. `wear` is one garment clause, stated in every prompt of every arm.
#
# `sheet_film` is an EXISTING sheet in ComfyUI/input rendered in some other style, used by
# arm B1 to measure style contamination. Only VIRO has one; for the others B1 is skipped
# rather than faked, because an invented mismatched sheet would measure nothing real.

SUBJECTS = {
    "VIRO": {
        "prose": ("a young man with long dark brown curly hair tied in a ponytail, "
                  "brown eyes, a small gold ear stud"),
        "wear": "wearing a teal soccer jersey with orange trim and the number 7",
        "sheet_film": "sheet_viro.png",
        "markers": "high",
        "dir": "",          # VIRO keeps the original flat layout - do not change
    },
    "HALE": {
        "prose": ("a woman in her mid-forties with steel-grey hair in a short crop, "
                  "one white streak above her left temple, round tortoiseshell glasses, "
                  "a jade stud in her right ear"),
        "wear": ("wearing a navy field jacket with a brass zip pull and a laminated "
                 "ID card on a red lanyard"),
        "sheet_film": None,
        "markers": "high (eyewear + streak)",
        "dir": "hale",
    },
    "PLAIN": {
        # THE CONTROL. Every noun here is deliberately generic.
        "prose": ("a man in his early forties with short brown hair, brown eyes, "
                  "an oval clean-shaven face"),
        "wear": "wearing a plain grey crew-neck sweatshirt",
        "sheet_film": None,
        "markers": "deliberately none",
        "dir": "plain",
    },
}


def load_subject(sid):
    """Subject definition, preferring a real character card if one exists.

    Cards are owned by another agent in this wave. This READS them and never writes them:
    if studio/characters/<ID>.json turns up later with a `prose` field it wins over the
    built-in copy automatically and the experiment re-runs against the real card.
    """
    sid = sid.upper()
    if sid not in SUBJECTS:
        raise SystemExit("unknown subject %s. known: %s" % (sid, ", ".join(sorted(SUBJECTS))))
    s = dict(SUBJECTS[sid])
    s["id"] = sid
    card_p = os.path.join(STUDIO, "characters", sid + ".json")
    s["card"] = None
    if os.path.isfile(card_p):
        try:
            card = json.load(open(card_p))
            s["card"] = card_p
            if card.get("prose"):
                s["prose"] = card["prose"]
            wt = card.get("wear_tags") or []
            if wt:
                # wear_tags[0] is the undamaged rung; every arm here is an undamaged shot.
                s["wear"] = wt[0] if wt[0].lower().startswith("wearing") else "wearing " + wt[0]
            if card.get("sheet"):
                s["sheet_film"] = card["sheet"]
        except Exception as e:
            print("  (card %s unreadable: %s - using built-in)" % (card_p, e))
    s["sheet_photo"] = "qc_%s_photo_sheet.png" % sid.lower()
    s["out"] = os.path.join(OUT_BASE, s["dir"]) if s["dir"] else OUT_BASE
    return s


# Four places the sheet has never seen. Concrete nouns, not adjectives - this project has
# measured that a place card with ~11 concrete nouns survives a style that would otherwise
# replace it, while three loose tags do not.
PLACES = [
    ("night_street", "on a rain-soaked city street at night, wet asphalt reflecting red "
                     "and green neon signs, parked cars, a bus shelter, puddles"),
    ("kitchen",      "in a bright domestic kitchen, white tiled wall, wooden worktop, a "
                     "steel kettle, a bowl of lemons, morning light from a window"),
    ("beach",        "on a windswept pebble beach under a grey overcast sky, breaking "
                     "waves, a wooden groyne, gulls, driftwood"),
    ("library",      "in a wood-panelled library, tall shelves of old books, a brass "
                     "reading lamp, a rolling ladder, warm lamplight"),
]

SEED = 4400
W, H = 1152, 1440          # 4:5. A waist-up figure at 16:9 puts the face on ~90px of
                           # height, which is too small to judge identity from.

# Six views for the angles stage. Framing is stated in every one, for the reason in the
# module docstring.
VIEWS = [
    ("front",         "front view of the same person, facing the camera directly, neutral expression, head and shoulders"),
    ("three_quarter", "three-quarter view of the same person, head turned slightly to their left, head and shoulders"),
    ("side_left",     "the same person's head turned to face left, profile of the face, head and shoulders"),
    ("back",          "the same person seen from behind, back of the head, head and shoulders"),
    ("looking_up",    "the same person looking upward, chin raised, neutral expression, head and shoulders"),
    ("low_angle",     "the same person seen from a low camera angle looking up at them, head and shoulders"),
]

LIGHTS = [
    ("golden_hour", "Relight the photograph: warm low golden-hour sunlight raking in from "
                    "the left, long soft shadows, amber highlights on the face. Keep the "
                    "person, pose and background exactly the same."),
    ("hard_top",    "Relight the photograph: harsh hard overhead light from directly above, "
                    "deep shadows in the eye sockets and under the chin, high contrast. "
                    "Keep the person, pose and background exactly the same."),
    ("blue_rim",    "Relight the photograph: cool blue backlight rimming the head and "
                    "shoulders from behind, dim cold ambient fill on the face. Keep the "
                    "person, pose and background exactly the same."),
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


def stage_img(path, name):
    """LoadImage only reads from ComfyUI/input, so anything referenced must live there."""
    dst = os.path.join(COMFY, "input", name)
    if os.path.abspath(path) != os.path.abspath(dst):
        sh("cp", path, dst)
    return name


# --------------------------------------------------------------- batched submission

def submit(wf, front=True):
    """POST one workflow. `front` REORDERS the pending queue; it cancels nothing.

    ComfyUI negates the queue number when front is set (server.py:1072-1073), so a batch
    submitted in order comes back in REVERSE order. Harmless here - every cell writes its
    own file and nothing in a stage depends on a sibling."""
    resp = api(HOST, "/prompt", {"prompt": wf, "client_id": str(uuid.uuid4()),
                                 "front": bool(front)})
    if "error" in resp:
        raise RuntimeError(json.dumps(resp)[:300])
    return resp["prompt_id"]


def batch(jobs, front=True, timeout=2400):
    """jobs is [(dst_path, workflow, label)]. Submit them all, then wait for all.

    Submitting the whole stage before waiting is the entire point: it keeps our cells
    adjacent in the queue so the checkpoint is loaded once for the stage instead of once
    per cell. See the module docstring."""
    todo = []
    for dst, wf, label in jobs:
        if os.path.exists(dst):
            print("  %-34s = exists" % label)
            continue
        todo.append((dst, wf, label))
    if not todo:
        return 0

    live = []
    for dst, wf, label in todo:
        try:
            live.append((submit(wf, front), dst, label))
        except Exception as e:
            print("  %-34s FAILED to submit: %s" % (label, str(e)[:100]))
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
            entry = hist[pid]
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                print("  %-34s FAILED (execution error)" % label)
                for m in status.get("messages", [])[:3]:
                    print("      %s" % str(m)[:200])
                continue
            if not status.get("completed"):
                still.append((pid, dst, label))
                continue
            outs = []
            for _n, out in entry.get("outputs", {}).items():
                for f in out.get("images", []):
                    outs.append(("%s/%s" % (f.get("subfolder", ""), f["filename"])).lstrip("/"))
            if outs and ensure_local(outs[0], dst, required=False):
                print("  %-34s %6.0f KB  [%3.0fs]" % (label, os.path.getsize(dst) / 1024,
                                                      time.time() - t0), flush=True)
                done += 1
            else:
                print("  %-34s NO OUTPUT" % label)
        pending = still
    for _pid, _dst, label in pending:
        print("  %-34s TIMED OUT" % label)
    return done


# --------------------------------------------------------------- workflow builders

def wf_t2i(prompt, seed, style_lora=None, strength=0.0, w=W, h=H):
    """Qwen-Image 2512 text-to-image. Node 7 is the style slot and ships OFF."""
    wf = load_wf(T2I)
    set_path(wf, "10.inputs.text", prompt)
    set_path(wf, "12.inputs.width", w)
    set_path(wf, "12.inputs.height", h)
    set_path(wf, "13.inputs.seed", seed)
    if style_lora:
        set_path(wf, "7.inputs.lora_name", style_lora)
    set_path(wf, "7.inputs.strength_model", float(strength))
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/qc/t2i")
    return wf


def wf_ref(prompt, seed, sheet, style_lora=None, strength=0.0, w=W, h=H):
    """Qwen-Image-Edit 2511 in REFERENCE mode: the sheet conditions, an empty latent is
    the canvas (node 13 samples node 20, not node 12). The sheet is NOT the thing being
    painted over - a whole new scene is generated with the sheet as side-conditioning."""
    wf = load_wf(REF)
    wf.pop("9", None)      # second LoadImage, unwired here; drop it so it cannot fail
    wf.pop("12", None)     # VAEEncode of the ref - dead in reference mode
    set_path(wf, "8.inputs.image", sheet)
    # Both encoders get the references. That is the Qwen edit convention and node 11 is
    # the negative; feeding it the same images is deliberate, not a copy-paste bug.
    set_path(wf, "10.inputs.prompt", prompt)
    set_path(wf, "20.inputs.width", w)
    set_path(wf, "20.inputs.height", h)
    set_path(wf, "13.inputs.seed", seed)
    if style_lora:
        set_path(wf, "7.inputs.lora_name", style_lora)
    set_path(wf, "7.inputs.strength_model", float(strength))
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/qc/ref")
    return wf


def wf_angles(src, prompt, seed, strength=0.85):
    wf = load_wf(ANG)
    set_path(wf, "7.inputs.image", src)
    set_path(wf, "10.inputs.prompt", prompt)
    set_path(wf, "15.inputs.seed", seed)
    set_path(wf, "40.inputs.strength_model", float(strength))
    set_path(wf, "17.inputs.filename_prefix", "claude-generated/qc/ang")
    return wf


def wf_relight(src, prompt, seed, strength=1.0):
    """Qwen-Image-Edit 2509 + Relight. Built by patching workflow 03 rather than adding a
    workflow file, because this is an experiment and not yet a sanctioned graph.

    Chain order follows the project convention set in workflow 32: the accelerator sits
    CLOSEST TO THE BASE WEIGHTS and the task LoRA stacks after it. The accelerator is
    sampler configuration, not style, and must stay at 1.0.

    Relight is a 2509 LoRA, so it runs on the 2509 checkpoint. 2511 is a different base
    and this project has already proved LoRAs are base-locked."""
    wf = load_wf(EDT)
    wf["40"] = {"class_type": "LoraLoaderModelOnly",
                "inputs": {"model": ["1", 0], "lora_name": L_LIGHT09, "strength_model": 1.0}}
    wf["41"] = {"class_type": "LoraLoaderModelOnly",
                "inputs": {"model": ["40", 0], "lora_name": L_RELIGHT,
                           "strength_model": float(strength)}}
    set_path(wf, "5.inputs.model", ["41", 0])
    set_path(wf, "7.inputs.image", src)
    set_path(wf, "10.inputs.prompt", prompt)
    set_path(wf, "13.inputs.seed", seed)
    set_path(wf, "13.inputs.steps", 4)      # the 2509 Lightning LoRA is installed, so the
    set_path(wf, "13.inputs.cfg", 1.0)      # 20-step / cfg 4.0 default in 03 is obsolete
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/qc/relight")
    return wf


# --------------------------------------------------------------- stages
#
# Every stage takes (subject, force) and RETURNS a job list for batch() rather than
# rendering inline, so main() can group whole checkpoints together across subjects.

def dirfor(s, name):
    d = os.path.join(s["out"], name)
    os.makedirs(d, exist_ok=True)
    return d


def _clear(dst, force):
    if force and os.path.exists(dst):
        os.remove(dst)
    return dst


def sheet_path(s):
    return os.path.join(dirfor(s, "sheet"), "%s_photo_sheet.png" % s["id"].lower())


def stage_sheet(s, force):
    """A photographic reference sheet, rendered the way make_sheets.py does it but with
    the style LoRA slot explicitly OFF.

    This exists because the sheet the films actually use (sheet_viro.png) is an
    ILLUSTRATION. It was rendered through workflow 13 back when node 7 carried the
    storybook LoRA at 0.8, so the style is baked into the reference itself. Comparing an
    illustrated reference against a photographic target confounds identity with style,
    so arm B2 needs a style-matched sheet to be a fair test."""
    dst = _clear(sheet_path(s), force)
    p = (f"A character reference sheet photograph of {s['prose']}, {s['wear']}, neutral "
         f"expression, facing the camera directly, even soft lighting, plain flat grey "
         f"background, head and shoulders.")
    return [(dst, wf_t2i(p, 990, w=1328, h=1328), "%s photo sheet" % s["id"])]


def publish_sheet(s):
    """Copy the rendered sheet into ComfyUI/input so LoadImage can see it."""
    p = sheet_path(s)
    if os.path.exists(p):
        stage_img(p, s["sheet_photo"])
        return True
    return False


def stage_A(s, force):
    """CONTROL: description only, no reference of any kind. How far do words carry a face?"""
    d = dirfor(s, "A_control")
    jobs = []
    for i, (pid, place) in enumerate(PLACES):
        dst = _clear(os.path.join(d, "%d_%s.png" % (i, pid)), force)
        p = f"A {FRAME} of {s['prose']}, {s['wear']}, {place}."
        jobs.append((dst, wf_t2i(p, SEED + i), "%s A %s" % (s["id"], pid)))
    return jobs


def _literal(s, place):
    """The phrasing workflow 23 says the model was trained on: refer to the reference as
    "image 1", literally. Its _notes warn that vaguer wording degrades the association.

    "The person in image 1" rather than "the man" / "the woman", so the identical sentence
    works for every subject and GENDER IS NEVER RE-ASSERTED BY THE PROMPT. That matters:
    if this said "the woman" for HALE it would be propping up exactly the thing the
    style-LoRA arms are trying to measure."""
    return (f"The person in image 1 is now {place}. {FRAME.capitalize()}. "
            f"Keep their face, hair and features exactly as they are in image 1. "
            f"They are {s['wear']}.")


def _shortpy(s, place):
    """What scripts/short.py actually emits: the character's prose with "from the reference
    image" hand-written into the film's character string, and no mention of image 1."""
    return f"A {FRAME} of {s['prose']} from the reference image, {s['wear']}, {place}."


def _ref_arm(s, name, sheet, phrasing, force):
    d = dirfor(s, name)
    jobs = []
    for i, (pid, place) in enumerate(PLACES):
        dst = _clear(os.path.join(d, "%d_%s.png" % (i, pid)), force)
        jobs.append((dst, wf_ref(phrasing(s, place), SEED + i, sheet),
                     "%s %s %s" % (s["id"], name.split("_")[0], pid)))
    return jobs


def stage_B1(s, force):
    if not s.get("sheet_film"):
        print("  %s has no pre-existing film sheet - B1 skipped (nothing real to measure)"
              % s["id"])
        return []
    return _ref_arm(s, "B1_film_sheet", s["sheet_film"], _literal, force)


def stage_B2(s, force):
    return _ref_arm(s, "B2_photo_sheet", s["sheet_photo"], _literal, force)


def stage_B3(s, force):
    return _ref_arm(s, "B3_shortpy_phrasing", s["sheet_photo"], _shortpy, force)


def stage_C(s, force):
    """MULTIPLE ANGLES on a photographic source. The existing VIRO turnaround was run from
    the ANIME sheet, so it has never been tried on the kind of image the qwen engine
    actually produces."""
    d = dirfor(s, "C_angles")
    jobs = []
    for i, (vid, prompt) in enumerate(VIEWS):
        dst = _clear(os.path.join(d, "%d_%s.png" % (i, vid)), force)
        jobs.append((dst, wf_angles(s["sheet_photo"], prompt, 1200 + i),
                     "%s C %s" % (s["id"], vid)))
    return jobs


def stage_E1(s, force):
    """Positive control for E2: the same style LoRA on its OWN base, the 2512 t2i model,
    where it is already proven to work."""
    d = dirfor(s, "E1_style_t2i")
    place = PLACES[3][1]
    jobs = []
    for st in (0.0, 1.0, 1.5):
        dst = _clear(os.path.join(d, "str_%.1f.png" % st), force)
        p = f"A {FRAME} of {s['prose']}, {s['wear']}, {place}."
        jobs.append((dst, wf_t2i(p, 5150, L_ILLUS, st), "%s E1 illus %.1f" % (s["id"], st)))
    return jobs


def stage_E2(s, force):
    """The combination the question is actually about: a style LoRA restyling a person
    while a reference sheet holds the face.

    NOTE THE BASE-REVISION TRAP. illustration-1.0-qwen-image was trained on Qwen-Image
    (text-to-image). This arm runs it on Qwen-Image-EDIT 2511, which shares the 60-block
    geometry so it will attach silently and cleanly whether or not it does anything.
    Stage E1 is the positive control that separates "the LoRA is inert" from "the LoRA
    does not cross to the edit model"."""
    d = dirfor(s, "E2_style_on_ref")
    place = PLACES[3][1]      # the library, which has the most to lose to a flat style
    jobs = []
    for st in (0.0, 1.0, 1.5):
        dst = _clear(os.path.join(d, "str_%.1f.png" % st), force)
        jobs.append((dst, wf_ref(_literal(s, place), 5150, s["sheet_photo"], L_ILLUS, st),
                     "%s E2 illus %.1f" % (s["id"], st)))
    return jobs


def stage_F(s, force):
    """SEED ROBUSTNESS for the style stages, because the single-seed result was strong
    enough that it had to be checked before being reported.

    At seed 5150 the illustration LoRA on the bare t2i path turned VIRO into a woman at
    both 1.0 and 1.5, while the same LoRA over a reference sheet kept him male. If that
    holds across seeds it is the whole answer to "how do I give them a look"; if it was
    one unlucky sample it is nothing. Three extra seeds per arm settles it."""
    d = dirfor(s, "F_style_seeds")
    place = PLACES[3][1]
    jobs = []
    for st in (1.0, 1.5):
        for seed in (6001, 6002, 6003):
            dst = _clear(os.path.join(d, "t2i_str%.1f_s%d.png" % (st, seed)), force)
            p = f"A {FRAME} of {s['prose']}, {s['wear']}, {place}."
            jobs.append((dst, wf_t2i(p, seed, L_ILLUS, st),
                         "%s F t2i %.1f s%d" % (s["id"], st, seed)))
    return jobs


def stage_G(s, force):
    """The same seed sweep on the REFERENCE path, so F and G are directly comparable.
    Split from F only because it needs the 2511 edit checkpoint and F needs 2512 t2i -
    interleaving them would pay a ~20 GB model load per image."""
    d = dirfor(s, "G_style_seeds_ref")
    place = PLACES[3][1]
    jobs = []
    for st in (1.0, 1.5):
        for seed in (6001, 6002, 6003):
            dst = _clear(os.path.join(d, "ref_str%.1f_s%d.png" % (st, seed)), force)
            jobs.append((dst, wf_ref(_literal(s, place), seed, s["sheet_photo"], L_ILLUS, st),
                         "%s G ref %.1f s%d" % (s["id"], st, seed)))
    return jobs


# The 2026-08-03 doc closes with "Only illustration-1.0-qwen-image was tested as a style
# LoRA. Whether the other two qwen style LoRAs also flip the subject is unknown." H closes
# exactly that, and it is cheap: two LoRAs, two seeds, with and without a reference.
OTHER_STYLES = [("story", L_STORY), ("modern", L_MODERN)]


def stage_H1(s, force):
    """The other two qwen style LoRAs with NO reference, on their own t2i base."""
    d = dirfor(s, "H1_other_styles_noref")
    place = PLACES[3][1]
    jobs = []
    for tag, lora in OTHER_STYLES:
        for seed in (6001, 6002):
            dst = _clear(os.path.join(d, "%s_s%d.png" % (tag, seed)), force)
            p = f"A {FRAME} of {s['prose']}, {s['wear']}, {place}."
            jobs.append((dst, wf_t2i(p, seed, lora, 1.0),
                         "%s H1 %s s%d" % (s["id"], tag, seed)))
    return jobs


def stage_H2(s, force):
    """The same two LoRAs WITH the reference sheet, on the 2511 edit model at 1.5 - the
    strength the illustration LoRA needed before it did anything on this base."""
    d = dirfor(s, "H2_other_styles_ref")
    place = PLACES[3][1]
    jobs = []
    for tag, lora in OTHER_STYLES:
        for seed in (6001, 6002):
            dst = _clear(os.path.join(d, "%s_s%d.png" % (tag, seed)), force)
            jobs.append((dst, wf_ref(_literal(s, place), seed, s["sheet_photo"], lora, 1.5),
                         "%s H2 %s s%d" % (s["id"], tag, seed)))
    return jobs


def stage_D(s, force):
    """RELIGHT: the "give them a certain look" half of the question. Lighting is the one
    part of "look" that is a physical fact about the image rather than an adjective, so it
    is exactly the kind of thing that belongs in a deterministic post-stage."""
    d = dirfor(s, "D_relight")
    src_png = os.path.join(s["out"], "B2_photo_sheet", "3_library.png")
    if not os.path.exists(src_png):
        src_png = sheet_path(s)
    if not os.path.exists(src_png):
        print("  %s: no source image for relight - run stage B2 or sheet first" % s["id"])
        return []
    sh("cp", src_png, os.path.join(d, "0_source.png"))
    src = stage_img(src_png, "qc_%s_relight_src.png" % s["id"].lower())
    jobs = []
    for i, (lid, prompt) in enumerate(LIGHTS):
        dst = _clear(os.path.join(d, "%d_%s.png" % (i + 1, lid)), force)
        jobs.append((dst, wf_relight(src, prompt, 3300 + i), "%s D %s" % (s["id"], lid)))
    return jobs


# --------------------------------------------------------------- contact sheets

def grid(cells, dst, cols, cell_w, title, crop=None):
    """cells is [(label, path)]. crop is (y_frac, side_frac) to cut a square around the
    head, or None for the whole frame."""
    ims, labels = [], []
    for label, p in cells:
        if not os.path.isfile(p):
            continue
        im = Image.open(p).convert("RGB")
        if crop:
            yf, sf = crop
            side = int(im.height * sf)
            x0 = max(0, (im.width - side) // 2)
            y0 = max(0, int(im.height * yf))
            im = im.crop((x0, y0, min(im.width, x0 + side), min(im.height, y0 + side)))
        w = cell_w
        h = max(1, int(im.height * w / im.width))
        ims.append(im.resize((w, h), Image.LANCZOS))
        labels.append(label)
    if not ims:
        return None

    bar, pad, top = 26, 6, 34
    cw = cell_w
    ch = max(i.height for i in ims) + bar
    rows = (len(ims) + cols - 1) // cols
    Wg = cols * cw + pad * (cols + 1)
    Hg = rows * ch + pad * (rows + 1) + top
    out = Image.new("RGB", (Wg, Hg), (17, 17, 17))
    dr = ImageDraw.Draw(out)
    dr.text((pad + 2, 8), title, font=font(19), fill=(255, 220, 90))
    for i, im in enumerate(ims):
        r, c = divmod(i, cols)
        x = pad + c * (cw + pad)
        y = top + pad + r * (ch + pad)
        dr.rectangle([x, y, x + cw, y + bar], fill=(0, 0, 0))
        dr.text((x + 5, y + 5), labels[i][:34], font=font(16), fill=(120, 235, 255))
        out.paste(im, (x, y + bar))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    out.save(dst, quality=93)
    print("  %s  %.0f KB" % (dst, os.path.getsize(dst) / 1024))
    return dst


def sheets(s):
    """Build every contact sheet for one subject from whatever has been rendered."""
    OUT = s["out"]

    def cells(sub):
        d = os.path.join(OUT, sub)
        if not os.path.isdir(d):
            return []
        fs = sorted(f for f in os.listdir(d) if f.endswith(".png"))
        return [(os.path.splitext(f)[0], os.path.join(d, f)) for f in fs]

    S = os.path.join(OUT, "_sheets")
    tag = s["id"]

    arms = ["A_control", "B1_film_sheet", "B2_photo_sheet", "B3_shortpy_phrasing"]
    ladder = []
    for sub in arms:
        for label, p in cells(sub):
            ladder.append(("%s  %s" % (sub.split("_")[0], label), p))
    if ladder:
        grid(ladder, os.path.join(S, "identity_ladder.jpg"), 4, 330,
             "%s - IDENTITY ON QWEN - rows: A control / B1 film sheet / B2 photo sheet / B3 short.py" % tag)
        grid(ladder, os.path.join(S, "identity_ladder_faces.jpg"), 4, 330,
             "%s - SAME CELLS, FACE CROP - judge identity here, not on the clothes" % tag,
             crop=(0.04, 0.42))

    for sub, title, cols, crop in [
        ("sheet", "THE REFERENCE SHEET", 2, None),
        ("C_angles", "C  MULTIPLE-ANGLES LoRA on a photographic source", 3, None),
        ("D_relight", "D  RELIGHT (2509 + Relight LoRA) - source then three lightings", 4, None),
        ("E1_style_t2i", "E1  illustration LoRA on its OWN base (2512 t2i) - positive control", 3, None),
        ("E2_style_on_ref", "E2  illustration LoRA on 2511 EDIT with a reference sheet", 3, None),
        ("F_style_seeds", "F  style LoRA, NO reference - 3 seeds at 1.0 (top) and 1.5 (bottom)", 3, None),
        ("G_style_seeds_ref", "G  style LoRA + REFERENCE SHEET - same 3 seeds, 1.0 then 1.5", 3, None),
        ("H1_other_styles_noref", "H1  the OTHER two qwen style LoRAs, NO reference", 4, None),
        ("H2_other_styles_ref", "H2  the same two style LoRAs WITH a reference sheet", 4, None),
    ]:
        c = cells(sub)
        if c:
            grid(c, os.path.join(S, sub + ".jpg"), cols, 360, "%s - %s" % (tag, title), crop=crop)
    if cells("C_angles"):
        grid(cells("C_angles"), os.path.join(S, "C_angles_faces.jpg"), 3, 360,
             "%s - C  MULTIPLE-ANGLES - face crop" % tag, crop=(0.02, 0.5))
    if cells("D_relight"):
        grid(cells("D_relight"), os.path.join(S, "D_relight_faces.jpg"), 4, 360,
             "%s - D  RELIGHT - face crop, does identity survive the lighting change?" % tag,
             crop=(0.04, 0.42))
    if cells("H1_other_styles_noref") or cells("H2_other_styles_ref"):
        grid(cells("H1_other_styles_noref") + cells("H2_other_styles_ref"),
             os.path.join(S, "H_other_styles.jpg"), 4, 340,
             "%s - H  OTHER STYLE LoRAs - top row NO reference, bottom row WITH reference" % tag,
             crop=(0.04, 0.44))

    def one(sub, fn):
        p = os.path.join(OUT, sub, fn)
        return p if os.path.isfile(p) else None
    picks = [
        ("SOURCE sheet", sheet_path(s)),
        ("A  prose only", one("A_control", "1_kitchen.png")),
        ("A  prose only", one("A_control", "2_beach.png")),
        ("B2 + ref sheet", one("B2_photo_sheet", "1_kitchen.png")),
        ("B2 + ref sheet", one("B2_photo_sheet", "2_beach.png")),
        ("C  angles LoRA", one("C_angles", "1_three_quarter.png")),
        ("D  relight", one("D_relight", "1_golden_hour.png")),
        ("F  style, NO ref", one("F_style_seeds", "t2i_str1.5_s6001.png")),
        ("G  style + ref", one("G_style_seeds_ref", "ref_str1.5_s6001.png")),
    ]
    picks = [(l, p) for l, p in picks if p and os.path.isfile(p)]
    if picks:
        grid(picks, os.path.join(S, "ANSWER.jpg"), 3, 340,
             "%s - THE ANSWER - every mechanism vs the source, face crop" % tag,
             crop=(0.04, 0.44))


def cross_subject_sheet(subs):
    """The sheet this whole run exists to produce: the SAME mechanism on every subject,
    one row each, so "does it generalise" is a question you answer by looking."""
    S = os.path.join(OUT_BASE, "_sheets")
    for sub, fns, title, crop in [
        ("sheet", None, "REFERENCE SHEETS - one per subject", None),
        ("A_control", ["1_kitchen.png", "2_beach.png", "3_library.png"],
         "A  PROSE ONLY - one row per subject. Same person three times, or three strangers?", (0.04, 0.44)),
        ("B2_photo_sheet", ["1_kitchen.png", "2_beach.png", "3_library.png"],
         "B2  REFERENCE SHEET - one row per subject. Does the lock generalise?", (0.04, 0.44)),
        ("F_style_seeds", ["t2i_str1.5_s6001.png", "t2i_str1.5_s6002.png", "t2i_str1.5_s6003.png"],
         "F  STYLE LoRA, NO REFERENCE - does it replace every subject, or only VIRO?", (0.04, 0.44)),
        ("G_style_seeds_ref", ["ref_str1.5_s6001.png", "ref_str1.5_s6002.png", "ref_str1.5_s6003.png"],
         "G  STYLE LoRA + REFERENCE - does the rescue generalise?", (0.04, 0.44)),
        ("C_angles", ["0_front.png", "1_three_quarter.png", "2_side_left.png", "4_looking_up.png"],
         "C  MULTIPLE-ANGLES LoRA - one row per subject", (0.02, 0.5)),
        ("D_relight", ["0_source.png", "1_golden_hour.png", "2_hard_top.png", "3_blue_rim.png"],
         "D  RELIGHT - one row per subject, source then three lightings", (0.04, 0.44)),
    ]:
        cells, cols = [], 0
        for s in subs:
            d = os.path.join(s["out"], sub)
            if not os.path.isdir(d):
                continue
            use = fns
            if use is None:
                use = sorted(f for f in os.listdir(d) if f.endswith(".png"))
            row = [(("%s %s" % (s["id"], os.path.splitext(f)[0]))[:34], os.path.join(d, f))
                   for f in use if os.path.isfile(os.path.join(d, f))]
            if row:
                cells += row
                cols = max(cols, len(row))
        if cells:
            grid(cells, os.path.join(S, "X_" + sub + ".jpg"), max(cols, 1), 330,
                 "ACROSS SUBJECTS - " + title, crop=crop)


# stage name -> (fn, checkpoint). The checkpoint tag is what lets main() order the run so
# each ~20 GB model is loaded once for ALL subjects rather than once per subject.
STAGES = [
    ("sheet", stage_sheet, "t2i"),
    ("A",     stage_A,     "t2i"),
    ("E1",    stage_E1,    "t2i"),
    ("F",     stage_F,     "t2i"),
    ("H1",    stage_H1,    "t2i"),
    ("B1",    stage_B1,    "edit2511"),
    ("B2",    stage_B2,    "edit2511"),
    ("B3",    stage_B3,    "edit2511"),
    ("C",     stage_C,     "edit2511"),
    ("E2",    stage_E2,    "edit2511"),
    ("G",     stage_G,     "edit2511"),
    ("H2",    stage_H2,    "edit2511"),
    ("D",     stage_D,     "edit2509"),
]
CKPT_ORDER = ["t2i", "edit2511", "edit2509"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", nargs="*", default=["VIRO"],
                    help="subject ids, or 'all'. known: " + ", ".join(sorted(SUBJECTS)))
    ap.add_argument("--stage", nargs="*", help="subset of: " + " ".join(s for s, _, _ in STAGES))
    ap.add_argument("--sheets", action="store_true", help="rebuild contact sheets only")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-front", action="store_true",
                    help="queue normally instead of jumping ahead of other work")
    a = ap.parse_args()

    ids = sorted(SUBJECTS) if "all" in [x.lower() for x in a.subject] else a.subject
    subs = [load_subject(x) for x in ids]

    if a.sheets:
        for s in subs:
            print("\n-- contact sheets: %s --" % s["id"])
            sheets(s)
        if len(subs) > 1:
            print("\n-- cross-subject sheets --")
            cross_subject_sheet(subs)
        return

    if a.stage:
        unknown = set(a.stage) - {s for s, _, _ in STAGES}
        if unknown:
            raise SystemExit("unknown stage(s): %s" % ", ".join(sorted(unknown)))
    want = [t for t in STAGES if not a.stage or t[0] in a.stage]

    for s in subs:
        os.makedirs(s["out"], exist_ok=True)
        print("SUBJECT %-6s markers=%-24s card=%s" %
              (s["id"], s["markers"], s["card"] or "(built-in)"))

    # ORDER IS BY CHECKPOINT FIRST, SUBJECT SECOND, and the whole checkpoint group is
    # submitted as ONE batch.
    #
    # Batching per STAGE is not enough on a shared box. Between two of our stages the
    # queue empties of our work, an unrelated video job starts, and the card swaps ~20 GB
    # out and back - so a 5-stage group pays five model loads. Collecting every cell that
    # needs the same checkpoint into a single submission makes that one load per group.
    #
    # Cross-group dependencies are respected because the groups are ordered: the sheet
    # (t2i) is published before the reference arms (edit2511) build their prompts, and D
    # (edit2509) reads a B2 output rendered in the edit2511 group. Within a group nothing
    # depends on a sibling.
    t_start = time.time()
    for ck in CKPT_ORDER:
        group = [t for t in want if t[2] == ck]
        if not group:
            continue
        print("\n########## checkpoint %s ##########" % ck, flush=True)
        jobs = []
        for name, fn, _ck in group:
            for s in subs:
                # The sheet must exist in ComfyUI/input before any arm can reference it.
                if name != "sheet":
                    publish_sheet(s)
                built = fn(s, a.force)
                if built:
                    print("  %-6s %-6s -> %d cell(s)" % (name, s["id"], len(built)))
                jobs += built
        if jobs:
            print("  -- %d cell(s) in one submission --" % len(jobs), flush=True)
            batch(jobs, front=not a.no_front)
        for s in subs:
            publish_sheet(s)

    print("\n-- contact sheets --")
    for s in subs:
        sheets(s)
    if len(subs) > 1:
        cross_subject_sheet(subs)
    print("\ntotal %.1f min" % ((time.time() - t_start) / 60.0))
    for s in subs:
        print("look at %s/_sheets/" % s["out"])


if __name__ == "__main__":
    main()
