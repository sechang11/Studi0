#!/usr/bin/env python3
"""cast_motion.py - DOES A CAST MEMBER SURVIVE MOVING?

    ~/ComfyUI/venv/bin/python3 studio/_tools/cast_motion.py strength
    ~/ComfyUI/venv/bin/python3 studio/_tools/cast_motion.py keyframes
    ~/ComfyUI/venv/bin/python3 studio/_tools/cast_motion.py clips
    ~/ComfyUI/venv/bin/python3 studio/_tools/cast_motion.py measure strips faces
    ~/ComfyUI/venv/bin/python3 studio/_tools/cast_motion.py all

    Run it under the ComfyUI venv. Rendering works under system python3, but every
    number below needs numpy and system python3 on this box has none.

WHY THIS TOOL EXISTS

Every identity result in this project comes from STILLS. cast_proof.py puts a character
in five rooms and proves the same face comes back; the LoRA cards prove a face against a
control at matched seeds; the turnaround proves a re-poser works. Not one of them has run
a clip. A film is not stills, and the question nobody has asked is whether the person in
frame 0 is still the person in frame 96.

THE STRUCTURAL FACT THAT DECIDES WHAT THIS CAN MEASURE, stated first because it changes
how the results read: THE CHARACTER LoRA IS NOT IN THE VIDEO GRAPH. scripts/short.py:394
splices node 90 into the ANIME KEYFRAME workflow only; workflows/12_ltx23_i2v_audio.json
loads an image and a string and has no LoRA slot for a character at all. So

    BETWEEN clips, identity is the LoRA's job - it draws each keyframe.
    WITHIN a clip, identity is entirely LTX's job, and nothing on the character card can
    help it. There is no knob.

That is why the two judgements are kept apart below, and why the control clip is worth
rendering: if within-clip drift is the same with the LoRA and without it, then the LoRA
is not what is holding a moving shot together and nobody should reach for it when a shot
smears.

THE MATRIX

VIRO, chosen over NIKA and PIP for three reasons, only the third of which is convenience:
  1. HIS CONTROL IS KNOWN TO FAIL. cast_proof measured that his tags are generic ("long
     dark brown curly hair, ponytail, brown eyes, gold ear stud") and his tags-only arm
     returns five different people, while NIKA's and PIP's tags are so specific that they
     are nearly on model with no LoRA at all. A control that already works proves nothing.
  2. HE CARRIES A COUNTABLE MARKER A METRIC CANNOT FAKE. wear_tags[0] is "clean teal
     soccer jersey, orange trim, number 7". A NUMERAL is the most brutal drift detector
     available - it is either a 7 or it is not, and no amount of "it still looks like
     him" survives the 7 turning into a smudge.
  3. He has the most existing still evidence to contradict.

Six clips, six places the training set never contained, six DIFFERENT motion cards, all
of family `subject` - the person moves, not the world, because that is where identity is
most likely to break. One video seed across every cell so the LTX noise is held.

STRENGTH. The brief says use the card's measured strength and not 0.85. VIRO'S CARD HAS
NO MEASURED STRENGTH - lora_strength_measured is on NIKA and PIP only, and
studio/loras/character-viro.json says in as many words that its 0.85 "is a judgement, not
a sweep" and that "the useful experiment is DOWNWARD". So stage `strength` renders the
sweep that was never run, two places x three strengths, and the number this run uses is
the one that came out of looking at it. It is written back onto the card so the next tool
inherits a measurement instead of a default.

LENGTH. Six cells at 97 frames (4.04s), which is the length the whole motion library was
measured at, so the motion figures here can be read against the cards' own bands. Then
four cells re-rendered at 193 frames (8.04s) - the SAME keyframe, the SAME seed, the same
string, twice the clip - because "he holds" and "he holds for four seconds" are different
claims and only the second one tells an editor anything.

WHAT IS MEASURED
  motion / churn / frozen   scripts/analyze_shots.py, the shipped module. Headline.
  creep                     video_engines.zoom_est, as motion_probe uses it.
  drift_struct / drift_hue  NEW HERE, and the number the brief actually asks for: a HEAD
                            CROP from every sampled frame, compared against the head crop
                            from FRAME 0 of the same clip. Same statistic cast_proof.py
                            uses between cells, pointed along time instead of across a
                            matrix. struct is shape-and-value on a z-normalised 96x96
                            grey crop; hue is a chi-square over a saturation-weighted
                            36-bin hue histogram, which is where hair and jersey colour
                            live.
                            IT IS A CROP WINDOW, NOT A FACE DETECTOR. There is no face
                            detector on this box (cast_proof.py records why one was built
                            and thrown away). The window is three fractions, set by
                            looking at the keyframe, and CHECKED against the face strip -
                            any cell whose head leaves the window is in EXCLUDE_FACE and
                            its drift numbers are dropped rather than reported wrong.
                            On walk_in the subject grows and the window cannot track it,
                            so that cell's drift number measures scale as well as face.
                            Said out loud rather than buried: on a travelling shot READ
                            THE STRIP, not the number.

THE NUMBERS RANK. THEY DO NOT DECIDE. This project has already had the stability metric
call a clip best-in-sweep while the subject's hair had covered her face. Every verdict
this tool writes came from reading a strip. This run produced its own example: c4_cup_lift
has the WORST drift figure in the set, 108, because he raises a cup in front of his own
face exactly as asked. Ranked by the number it is the failure; watched, it is the best
cell here.

WHAT THIS RUN MEASURED (2026-08-04, VIRO, 12 clips, all 24 strips read)

  1. WITHIN A CLIP HE HOLDS, AND HE HOLDS FOR EIGHT SECONDS. At f192 of c1_walk_in_long
     the number 7, both gold ear studs, the two-tone hair and the amber eyes are all
     unchanged from the keyframe. Its drift curve is non-monotonic - 0/43/52/14/43/54/23/
     55/20 - so the movement in that number is hair strands, not a face. Nothing here
     degraded with the clock.
  2. WHAT ENDS A FACE IS THE ACTION COMPLETING, AT A FRACTION OF THE CLIP RATHER THAN AT
     A SECOND. turn_away gives the face up ~60% through, head_turn ~70% at 4s and ~75% at
     8s, step_back (which renders as turn-and-walk-away) ~50%. Doubling the clip roughly
     doubles the face time. That is the number an editor needs and it is not a constant
     in seconds.
  3. THE CONTROL SEPARATES THE TWO CLAIMS THE LoRA IS USUALLY CREDITED WITH. Dropping it
     gives a different man - the cleanest single marker is the gold ear stud, on both ears
     in every LoRA cell and absent from every control frame - and a jersey whose number is
     small, high and duplicated into a crest instead of one large clean 7. Not a wildly
     different man, though: the sheet at 0.6 carries a lot on its own. So the LoRA is what
     makes him a specific person. But the control's own drift curve is just as flat, at 4s
     and at 8s - so the LoRA is NOT what makes him stable while moving. Nothing is. That is
     LTX's image conditioning and there is no knob for it on a character card.
     THIS POINT WAS WRONG IN A FIRST DRAFT, which said the control's jersey had no number,
     read off a 330px strip cell. At full resolution it has one. Judge garment detail from
     the frame, not from the strip; the strip is for staging and the face crop is for
     faces.
  4. THE MOTION LIBRARY'S MEASURED BANDS DID NOT TRANSFER. walk_in, measured at a mean of
     3.191 and called the best card in the library, came back at 0.380 on c1 - below its
     own do-nothing band - because that keyframe already has him close and there is
     nowhere to walk. hand_to_face, measured as a small articulated gesture, walked him
     the length of a subway platform. THE KEYFRAME'S STAGING, NOT THE MOTION STRING,
     DECIDED HOW MUCH MOVED. The library was measured on one keyframe and its bands should
     not be quoted at a user until it has been measured on several.

READ THE OUTPUT IN THIS ORDER
    strips/<cell>.png    keyframe + 9 frames across the clip, labelled. The evidence.
    faces/<cell>.png     the same frames as head crops, upscaled. IDENTITY IS JUDGED HERE.
    between.png          frame 0 and the last frame of every cell, side by side, as head
                         crops. This is the BETWEEN-clip judgement in one picture.
    results.json         every number, the crop fractions, and the exclusions.
    _strength.png        the LoRA strength ladder that set lora_strength_measured.
    _frames/             a regenerable CACHE of the sampled frames, ~70 MB. `measure`
                         rewrites it; `faces` and `between` read it. Safe to delete, and
                         if you do, run `measure` again before `faces`.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

# analyze_shots.py does os.environ.setdefault("COMFY_ROOT", "Z:/ComfyUI") - a Windows SMB
# path - and epic.py reads COMFY_ROOT at import. Set it FIRST, exactly as motion_probe.py
# does, or every path resolves to a share that is not mounted here.
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
REPO = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, HERE)

from analyze_shots import motion as ydif_motion, frozen_seconds     # noqa: E402
from comfy import api, set_path                                     # noqa: E402
from epic import load_wf, COMFY, HOST                               # noqa: E402
from PIL import Image                                               # noqa: E402

REL = "claude-generated/cast-motion"
LAB = f"{COMFY}/output/{REL}"
OUT = f"{STUDIO}/samples/cast_motion"
CAST = f"{STUDIO}/characters"
PLACEDIR = f"{STUDIO}/places"
MOTIONDIR = f"{STUDIO}/motions"
LORACARD = f"{STUDIO}/loras"
FONT = "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf"

WF_ANIME = "22_anime_kf_ipadapter.json"
WF_LTX = "12_ltx23_i2v_audio.json"

# short.py's shipping config, verbatim. anime_keyframe() renders 1344x768 (short.py:417)
# and clips() sets the latent to VID = 1280x704 (short.py:66). The keyframe is handed to
# LoadImage at its own size and LTXVImgToVideoInplace does the fitting - which is what a
# user gets, so it is what is measured. Do not "fix" the mismatch here.
KFW, KFH = 1344, 768
VW, VH = 1280, 704
FPS = 24
SHORT_FRAMES = 97       # 4.04s - the length the whole motion library was measured at
LONG_FRAMES = 193       # 8.04s - 8n+1, inside LTX-2.3's ~10s drift ceiling
IP_WEIGHT = 0.6         # node 4's shipping weight. Not tuned here.
KF_SEED0 = 7700
VID_SEED = 7701         # one seed for every clip; also a seed the motion library used

Q = "masterpiece, best quality, very aesthetic, absurdres"
# ONE framing clause for all six cells. The cells differ in place and motion on purpose;
# letting the framing differ too would have made the BETWEEN-clip comparison meaningless.
# `cowboy shot` (danbooru: mid-thigh up) is the compromise - wide enough that walk_in has
# somewhere to travel and step_back has somewhere to go, tight enough that the head is
# ~150px and a face can actually be judged.
FRAME = "cowboy shot, looking at the viewer, centered"

# compose.py:209 strips these from a place tag string when a character is in the shot.
PLACE_EMPTY_NOUNS = ("scenery", "no humans")

# (cell, place, motion card, keyframe tags this cell adds, long?)
# Every motion is family `subject`. The set covers the four things the brief names - a
# step, a hand, a head-turn, a turn - plus a held shot with business in it, which is the
# case where nothing displaces and drift has nowhere to hide.
CELLS = [
    ("c1_walk_in",      "stadium_concourse",    "walk_in",      "", True),
    ("c2_head_turn",    "snowfield",            "head_turn",    "", True),
    ("c3_hand_to_face", "subway_platform",      "hand_to_face", "", True),
    # cup_lift's card says `needs: a person and a cup on a surface in frame`, and this
    # project has measured that a motion naming something absent from the keyframe makes
    # LTX invent it. So the cup is put in the keyframe rather than hoped for.
    ("c4_cup_lift",     "library_reading_room", "cup_lift",
     "sitting at a table, a cup of coffee on the table in front of him", True),
    ("c5_turn_away",    "rooftop_night",        "turn_away",    "", False),
    ("c6_step_back",    "market_street",        "step_back",    "", False),
]
# THE CONTROL. Same place, same keyframe seed, same video seed, same motion string as c1 -
# one thing removed. IPAdapter is LEFT ON at 0.6, because the brief asks for the LoRA
# dropped and dropping the sheet too would have removed two things at once.
CONTROL = ("x1_walk_in_nolora", "c1_walk_in")

# Strength sweep. Two places at the ends of the value range, because the damage a
# character LoRA does to a scene is a function of how far that scene sits from the flat
# cream backdrop it was trained on.
SWEEP_PLACES = ["snowfield", "subway_platform"]
SWEEP_STRENGTHS = [0.0, 0.5, 0.85]

# ── head crop windows ─────────────────────────────────────────────────────────
# (centre x, centre y, side) as fractions of frame width / height / HEIGHT. Set by
# looking at the rendered keyframes, then checked against faces/*.png. A cell whose head
# leaves its window goes in EXCLUDE_FACE and loses its drift numbers rather than
# reporting a number computed off an ear and a wall.
HEAD_DEFAULT = (0.50, 0.30, 0.46)
# SET BY LOOKING at the first pass of faces/*.png, then re-measured. c4 is seated at a
# table on the left of frame, so the centred default caught the top of his head and, from
# f84, the cup.
HEAD_OVERRIDE = {
    "c4_cup_lift": (0.42, 0.32, 0.38),
    "c4_cup_lift_long": (0.42, 0.32, 0.38),
}
# NO FIXED WINDOW CAN MEASURE THESE, and a number that measures the wrong thing is worse
# than no number. On c3 the subject starts as a small figure at the far left of a subway
# platform and walks all the way into a medium shot, so the head crosses most of the frame
# and quadruples in size; on c6 he turns and walks away until he is a fifth of his starting
# height. Their drift figures are dropped and both clips are judged from the strips, which
# is what the strips are for.
EXCLUDE_FACE = {"c3_hand_to_face", "c3_hand_to_face_long", "c6_step_back"}

# THE BETWEEN-CLIP FIGURE IS BUILT FROM THE BEST FACE EACH CLIP OFFERS, not from a fixed
# frame index. Two of these clips end with the man's back to the lens and one begins with
# him thirty metres away, so "first and last frame of every cell" put four crops of a
# rear skull and a market awning next to each other and answered nothing. The between
# question is "is the person in clip A the person in clip D", and the fair way to ask it
# is to give every clip its best look. Which frame that is was chosen by reading
# faces/*.png, and the frame index is printed on each cell so the choice is auditable.
#   cell -> (index into the 9 sampled frames, crop box or None to use the measured one)
BETWEEN_PICK = {
    "c1_walk_in":       (0, None),
    "c2_head_turn":     (2, None),
    "c3_hand_to_face":  (8, (0.49, 0.32, 0.46)),
    "c4_cup_lift":      (3, None),
    "c5_turn_away":     (0, None),
    "c6_step_back":     (0, (0.477, 0.40, 0.44)),
    "x1_walk_in_nolora": (8, None),
}


# ═══════════════════════════════════════════════════════════════════ helpers
def sh(*a):
    r = subprocess.run([str(x) for x in a], capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write("FAIL %s\n%s\n" % (" ".join(str(x) for x in a)[:300],
                                            (r.stderr or "")[-1200:]))
    return r


def need(*dirs):
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _esc(s):
    """drawtext escaping. The apostrophe is the hazard - the label sits inside a
    single-quoted filtergraph token, so a literal ' truncates it. Substituting the UTF-8
    right single quote keeps the label readable; writing the escape as a \\u sequence made
    an earlier tool draw those six characters literally."""
    for a, b in (("\\", "\\\\"), (":", "\\:"), ("'", "\u2019"), ("%", "\\%"),
                 ("[", "\\["), ("]", "\\]")):
        s = s.replace(a, b)
    return s


def nframes(path):
    r = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
           "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", path)
    try:
        return int((r.stdout or "0").strip().split(",")[0])
    except ValueError:
        return 0


def submit(wf):
    r = api(HOST, "/prompt", {"prompt": wf, "client_id": str(uuid.uuid4())})
    if "error" in r:
        raise RuntimeError(json.dumps(r)[:400])
    return r["prompt_id"]


def wait_all(pids, label="jobs", timeout=7200):
    """Submit-then-poll, so a whole checkpoint group stays adjacent in the queue and the
    7 GB (or 22 GB) model is loaded once for the group."""
    import time
    left, recs, t0 = list(pids), {}, time.time()
    while left and time.time() - t0 < timeout:
        time.sleep(4)
        for pid in list(left):
            h = api(HOST, "/history/" + pid) or {}
            if pid in h:
                recs[pid] = h[pid]
                left.remove(pid)
        print("    %s %d/%d  %.0fs" % (label, len(recs), len(pids), time.time() - t0),
              flush=True)
    if left:
        print("  !! %d %s never finished" % (len(left), label))
    return recs


def job_file(rec):
    for _, o in (rec.get("outputs") or {}).items():
        for k in ("images", "videos", "gifs"):
            for it in (o.get(k) or []):
                sub = it.get("subfolder") or ""
                return os.path.join(COMFY, "output", sub, it["filename"])
    return None


def job_error(rec):
    st = (rec.get("status") or {})
    if st.get("status_str") == "error":
        for m in st.get("messages") or []:
            if m[0] == "execution_error":
                return str(m[1].get("exception_message"))[:200]
        return "error"
    return None


# ═══════════════════════════════════════════════════════════════════ library
def card():
    return jload(f"{CAST}/{ARGS.char}.json")


def place_tags(pid):
    t = jload(f"{PLACEDIR}/{pid}.json").get("tags", "")
    return ", ".join(p.strip() for p in t.split(",")
                     if p.strip().lower() not in PLACE_EMPTY_NOUNS)


def motion_card(mid):
    return jload(f"{MOTIONDIR}/{mid}.json")


def motion_text(c, mid):
    """The string the video model reads, built the way scripts/short.py builds it.

    The motion cards are written third-person feminine because the probe cells that
    measured them were. compose._motion_regender rewrites the pronouns to the character in
    the shot and changes no part of the grammar the sweep measured - same mover, same
    verb, same path. It is IMPORTED rather than reimplemented so this tool cannot drift
    away from what the app sends."""
    txt = motion_card(mid).get("text") or motion_card(mid).get("prompt") or ""
    try:
        sys.path.insert(0, STUDIO)
        import compose
        return compose._motion_regender(txt, compose._pronouns(c))
    except Exception as e:
        print("  !! compose pronoun rewrite unavailable (%s) - sending card text verbatim,"
              " which is FEMININE and will fight a male keyframe. Fix before trusting the"
              " result." % str(e)[:80])
        return txt


def strength():
    """The character's OWN measured strength. Falls back to the LoRA card's judgement, and
    says so loudly, because 0.85 was measured on this box to destroy a scene."""
    c = card()
    if c.get("lora_strength_measured") is not None:
        return float(c["lora_strength_measured"])
    p = f"{LORACARD}/character-{ARGS.char.lower()}.json"
    v = float(jload(p).get("strength")) if os.path.exists(p) else 0.85
    print("  !! %s carries no lora_strength_measured. Using the LoRA card's %s, which "
          "that card itself calls a judgement rather than a sweep. Run `strength` first."
          % (ARGS.char, v))
    return v


def positive(c, pid, extra=""):
    """compose.py:1476-1502's slot order, kept exactly: trigger, identity, base/sex,
    garment, shot, place, quality. Earlier and more specific wins on this engine."""
    bits = [c["id"].lower(), c.get("tags", "").strip()]
    if c.get("base_tags"):
        bits.append(c["base_tags"].strip())
    wear = c.get("wear_tags") or []
    if wear:
        bits.append(wear[0].strip())
    bits.append(FRAME)
    if extra:
        bits.append(extra)
    bits.append(place_tags(pid))
    bits.append(Q)
    return ", ".join(b for b in bits if b)


def wf_keyframe(c, pid, lora_w, seed, extra="", tag="kf"):
    """22_anime_kf_ipadapter.json exactly as scripts/short.py:358 assembles it.

    NODE 6, THE NEGATIVE, IS LEFT AS THE FILE SHIPS IT. short.py:_negative() drops any
    clause whose every word also appears in the positive; VIRO's positive shares no word
    with it, so short.py returns it byte-identical (studio/characters/NIKA.json records
    that check). Replacing it here would measure a different app."""
    wf = load_wf(WF_ANIME)
    set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
    set_path(wf, "2.inputs.image", c.get("sheet"))
    set_path(wf, "4.inputs.weight", IP_WEIGHT)
    set_path(wf, "5.inputs.text", positive(c, pid, extra))
    set_path(wf, "7.inputs.width", KFW)
    set_path(wf, "7.inputs.height", KFH)
    set_path(wf, "8.inputs.seed", int(seed))
    set_path(wf, "10.inputs.width", KFW)
    set_path(wf, "10.inputs.height", KFH)
    # Present in EVERY arm, at 0.0 for the control. LoraLoaderModelOnly is a documented
    # no-op at strength 0, so the control submits a structurally identical graph and the
    # only difference between it and c1 is one float.
    wf["90"] = {"class_type": "LoraLoaderModelOnly",
                "inputs": {"model": ["1", 0], "lora_name": c["lora"],
                           "strength_model": float(lora_w)}}
    for nid, node in list(wf.items()):
        if nid in ("1", "90") or not isinstance(node, dict):
            continue
        for k, v in (node.get("inputs") or {}).items():
            if isinstance(v, list) and len(v) == 2 and v[0] == "1" and v[1] == 0:
                node["inputs"][k] = ["90", 0]
    set_path(wf, "11.inputs.filename_prefix", f"{REL}/{tag}")
    return wf


def wf_clip(staged, text, frames, seed):
    """12_ltx23_i2v_audio.json as scripts/short.py:545 sets it. Node 9 img_compression and
    node 11 negative are LEFT AS THE FILE HAS THEM - short.py sets neither."""
    wf = load_wf(WF_LTX)
    set_path(wf, "8.inputs.image", staged)
    set_path(wf, "10.inputs.text", text)
    set_path(wf, "20.inputs.width", VW)
    set_path(wf, "20.inputs.height", VH)
    set_path(wf, "20.inputs.length", frames)
    set_path(wf, "21.inputs.frames_number", frames)
    set_path(wf, "32.inputs.noise_seed", int(seed))
    return wf


# ═══════════════════════════════════════════════════════════════════ stages
def stage_strength(force=False):
    """The sweep studio/loras/character-viro.json says was never run."""
    c = card()
    need(LAB, OUT)
    jobs, meta = [], {}
    for pid in SWEEP_PLACES:
        for s in SWEEP_STRENGTHS:
            tag = "sw_%s_%03d" % (pid, int(s * 100))
            dst = f"{LAB}/{tag}_00001_.png"
            if os.path.exists(dst) and not force:
                print("  = %s" % tag)
                continue
            # ONE seed per place across the whole ladder, so the only difference between
            # three cells in a row is the weight.
            wf = wf_keyframe(c, pid, s, KF_SEED0, tag=tag)
            j = submit(wf)
            jobs.append(j)
            meta[j] = (tag, pid, s)
            print("  > %s" % tag)
    if jobs:
        wait_all(jobs, "sweep")
    rows = []
    for pid in SWEEP_PLACES:
        row = []
        for s in SWEEP_STRENGTHS:
            tag = "sw_%s_%03d" % (pid, int(s * 100))
            f = f"{LAB}/{tag}_00001_.png"
            row.append((f if os.path.exists(f) else None,
                        "%s  strength %.2f%s" % (pid, s, "  (OFF - control)" if not s else "")))
        rows.append(row)
    _grid(rows, f"{OUT}/_strength.png", cellw=620)
    print("wrote %s/_strength.png - LOOK AT IT, then set lora_strength_measured." % OUT)


def stage_keyframes(force=False):
    c = card()
    need(LAB, OUT, f"{OUT}/keyframes")
    w = strength()
    print("  LoRA strength %.2f" % w)
    jobs, meta = [], {}
    plan = [(cid, place, extra, w) for cid, place, _m, extra, _l in CELLS]
    ctl, src = CONTROL
    src_row = [r for r in CELLS if r[0] == src][0]
    plan.append((ctl, src_row[1], src_row[3], 0.0))
    for i, (cid, place, extra, lw) in enumerate(plan):
        dst = f"{LAB}/{cid}_00001_.png"
        if os.path.exists(dst) and not force:
            print("  = %s" % cid)
            continue
        # The control shares its keyframe seed with the cell it controls. short.py's own
        # stride is i*7, kept.
        idx = [r[0] for r in CELLS].index(src) if cid == ctl else i
        wf = wf_keyframe(c, place, lw, KF_SEED0 + idx * 7, extra, tag=cid)
        j = submit(wf)
        jobs.append(j)
        meta[j] = cid
        print("  > %s  %s  lora %.2f  seed %d" % (cid, place, lw, KF_SEED0 + idx * 7))
    if jobs:
        recs = wait_all(jobs, "keyframes")
        for j in jobs:
            e = job_error(recs.get(j, {}))
            if e:
                print("  !! %s FAILED %s" % (meta[j], e))
    for cid, _p, _e, _w in plan:
        f = f"{LAB}/{cid}_00001_.png"
        if os.path.exists(f):
            shutil.copy(f, f"{COMFY}/input/cm_{cid}.png")
            shutil.copy(f, f"{OUT}/keyframes/{cid}.png")
        else:
            print("  !! %s has no keyframe" % cid)
    print("staged %d keyframes into %s/input" % (len(plan), COMFY))


def stage_clips(force=False, only=None):
    c = card()
    need(LAB, OUT)
    plan = []
    for cid, place, mid, _extra, longable in CELLS:
        plan.append((cid, cid, mid, place, SHORT_FRAMES))
        if longable:
            plan.append((cid + "_long", cid, mid, place, LONG_FRAMES))
    ctl, src = CONTROL
    src_row = [r for r in CELLS if r[0] == src][0]
    plan.append((ctl, ctl, src_row[2], src_row[1], SHORT_FRAMES))
    plan.append((ctl + "_long", ctl, src_row[2], src_row[1], LONG_FRAMES))
    man = f"{OUT}/manifest.json"
    done = {r["id"]: r.get("file") for r in (jload(man) if os.path.exists(man) else [])}
    jobs, meta = [], {}
    for tag, kf, mid, place, frames in plan:
        if only and only not in tag:
            continue
        # NOT `{tag}_00001_.mp4`. SaveVideo's counter is per PREFIX-and-directory and the
        # keyframes already wrote {tag}_00001_.png into this same folder, so every clip
        # here landed as _00002_. cast_proof.py records the same trap costing it the WRONG
        # render. The existing-clip test therefore asks the manifest, which stores the
        # filename read back out of /history.
        if done.get(tag) and os.path.exists(done[tag]) and not force:
            print("  = %s" % tag)
            continue
        staged = f"cm_{kf}.png"
        if not os.path.exists(f"{COMFY}/input/{staged}"):
            print("  !! no staged keyframe for %s - run `keyframes`" % tag)
            continue
        txt = motion_text(c, mid)
        wf = wf_clip(staged, txt, frames, VID_SEED)
        set_path(wf, "43.inputs.filename_prefix", f"{REL}/{tag}")
        j = submit(wf)
        jobs.append(j)
        meta[j] = dict(id=tag, kf=kf, motion_id=mid, place=place, frames_asked=frames,
                       text=txt, lora=(0.0 if kf.startswith("x") else strength()),
                       want=motion_card(mid).get("desc", ""))
        print("  > %-22s %3df  %s" % (tag, frames, txt))
    recs = wait_all(jobs, "clips") if jobs else {}
    prev = jload(man) if os.path.exists(man) else []
    for j in jobs:
        m = dict(meta[j])
        m["error"] = job_error(recs.get(j, {}))
        m["file"] = job_file(recs.get(j, {})) or (
            f"{LAB}/{m['id']}_00001_.mp4"
            if os.path.exists(f"{LAB}/{m['id']}_00001_.mp4") else None)
        prev = [r for r in prev if r["id"] != m["id"]]
        prev.append(m)
        print("%-24s %s" % (m["id"], m["error"] or os.path.basename(m["file"] or "NONE")))
    # cells that were already on disk still need a manifest row. glob, not _00001_ - see
    # the counter note above.
    import glob as _glob
    for tag, kf, mid, place, frames in plan:
        hits = sorted(_glob.glob(f"{LAB}/{tag}_[0-9]*_.mp4"))
        f = hits[-1] if hits else None
        if f and not any(r["id"] == tag for r in prev):
            prev.append(dict(id=tag, kf=kf, motion_id=mid, place=place, frames_asked=frames,
                             text=motion_text(c, mid),
                             lora=(0.0 if kf.startswith("x") else strength()),
                             want=motion_card(mid).get("desc", ""), error=None, file=f))
    order = [p[0] for p in plan]
    prev.sort(key=lambda r: order.index(r["id"]) if r["id"] in order else 99)
    json.dump(prev, open(man, "w"), indent=1)
    print("wrote %s (%d rows)" % (man, len(prev)))


# ═══════════════════════════════════════════════════════════════════ measuring
def _frame(clip, idx, dest):
    sh("ffmpeg", "-y", "-hide_banner", "-v", "error", "-i", clip,
       "-vf", "select=eq(n\\,%d)" % idx, "-vsync", "0", "-frames:v", "1",
       "-pix_fmt", "rgb24", dest)
    return dest


def sample_idx(n, k):
    return [round(i * (n - 1) / (k - 1)) for i in range(k)]


def frac_box(frac, W, H):
    cx, cy, side = frac
    s = side * H
    x0 = min(max(cx * W - s / 2.0, 0), W - s)
    y0 = min(max(cy * H - s / 2.0, 0), H - s)
    return (int(round(x0)), int(round(y0)), int(round(x0 + s)), int(round(y0 + s)))


def feats(path, box, size=96):
    import numpy as np
    im = Image.open(path).convert("RGB").crop(box).resize((size, size), Image.LANCZOS)
    g = np.asarray(im.convert("L"), dtype=np.float64)
    g = (g - g.mean()) / (g.std() + 1e-6)
    hsv = np.asarray(im.convert("HSV"), dtype=np.float64)
    w = (hsv[:, :, 1] / 255.0) * (hsv[:, :, 2] / 255.0)
    hist, _ = np.histogram(hsv[:, :, 0], bins=36, range=(0, 256), weights=w)
    return {"g": g, "h": hist / (hist.sum() + 1e-9)}


def d_struct(a, b):
    import numpy as np
    return float(np.abs(a["g"] - b["g"]).mean() * 100.0)


def d_hue(a, b):
    import numpy as np
    x, y = a["h"], b["h"]
    return float(0.5 * np.sum((x - y) ** 2 / (x + y + 1e-9)) * 100.0)


def creep_of(clip, tmp):
    """video_engines.zoom_est, imported rather than rewritten - motion_probe already
    solved this. 1.00 = framing held; 1.20 = crept in 20%."""
    try:
        import video_engines as ve
    except Exception:
        return {}
    n = nframes(clip)
    if n < 2:
        return {}
    a = _frame(clip, 0, f"{tmp}/z0.png")
    b = _frame(clip, n - 1, f"{tmp}/zl.png")
    try:
        z, zs, s1 = ve.zoom_est(a, b, Path(tmp), size=(VW, VH))
        return {"creep": round(z, 3), "ssim_last_vs_f0": round(s1, 3)}
    except Exception:
        return {}


def stage_measure(cols=9):
    man = jload(f"{OUT}/manifest.json")
    tmp = "/tmp/cast_motion"
    need(tmp, f"{OUT}/_frames")
    res = []
    for m in man:
        f = m.get("file")
        if not f or not os.path.exists(f):
            print("skip %s: no file" % m["id"])
            continue
        r = dict(m)
        mo, ch = ydif_motion(f)                     # THE HEADLINE. Shipped function.
        n = nframes(f)
        r.update(motion=round(mo, 4), churn=round(ch, 4),
                 frozen=round(frozen_seconds(f), 2), frames=n,
                 secs=round(n / float(FPS), 2))
        r.update(creep_of(f, tmp))
        idxs = sample_idx(n, cols)
        r["sample_idx"] = idxs
        pngs = [_frame(f, ix, "%s/_frames/%s_%02d.png" % (OUT, m["id"], i))
                for i, ix in enumerate(idxs)]
        box_frac = HEAD_OVERRIDE.get(m["id"], HEAD_DEFAULT)
        r["head_box"] = box_frac
        if m["id"] in EXCLUDE_FACE:
            r["drift_struct"] = r["drift_hue"] = None
            r["excluded"] = "head leaves the crop window - see faces/%s.png" % m["id"]
        else:
            box = frac_box(box_frac, VW, VH)
            fs = [feats(p, box) for p in pngs]
            r["drift_struct"] = [round(d_struct(fs[0], x), 2) for x in fs]
            r["drift_hue"] = [round(d_hue(fs[0], x), 2) for x in fs]
        res.append(r)
        d = r.get("drift_struct") or []
        print("%-24s motion %6.3f  churn %5.2f  creep %.3f  frozen %4.1f  "
              "drift f0->last %s"
              % (r["id"], r["motion"], r["churn"], r.get("creep", 0), r["frozen"],
                 ("%.1f" % d[-1]) if d else "excluded"), flush=True)
    json.dump(res, open(f"{OUT}/results.json", "w"), indent=1)
    print("wrote %s/results.json (%d clips)" % (OUT, len(res)))


# ═══════════════════════════════════════════════════════════════════ pictures
def _hstack(parts, labels, dst, cellw, header, sub=None, sub2=None, labsize=20,
            cellh=None):
    """hstack REFUSES inputs of unequal height, and a strip mixes a 1344x768 keyframe with
    1280x704 video frames - scale=w:-1 gives 189 for one and 181 for the other, so every
    strip failed with 'Input 1 height 216 does not match input 0 height 223'. The height is
    therefore forced, not derived."""
    if cellh is None:
        cellh = -1
    fc = []
    for i, lab in enumerate(labels):
        fc.append("[%d]scale=%d:%d,setsar=1,pad=iw+4:ih+34:2:2:0x101010,"
                  "drawtext=fontfile=%s:text='%s':x=6:y=h-27:fontsize=%d:"
                  "fontcolor=0xE0E0E0[v%d]" % (i, cellw, cellh, FONT, _esc(lab), labsize, i))
    fc.append("".join("[v%d]" % i for i in range(len(parts))) +
              "hstack=inputs=%d[row]" % len(parts))
    pad = 46 + (30 if sub else 0) + (26 if sub2 else 0)
    draw = ("drawtext=fontfile=%s:text='%s':x=12:y=10:fontsize=32:fontcolor=white"
            % (FONT, _esc(header)))
    if sub:
        draw += (",drawtext=fontfile=%s:text='%s':x=12:y=50:fontsize=24:fontcolor=0x7FD4FF"
                 % (FONT, _esc(sub)))
    if sub2:
        draw += (",drawtext=fontfile=%s:text='%s':x=12:y=80:fontsize=20:fontcolor=0x9A9A9A"
                 % (FONT, _esc(sub2)))
    fc.append("[row]pad=iw:ih+%d:0:%d:0x000000,%s[out]" % (pad, pad, draw))
    args = ["ffmpeg", "-y", "-hide_banner", "-v", "error"]
    for p in parts:
        args += ["-i", p]
    args += ["-filter_complex", ";".join(fc), "-map", "[out]", "-frames:v", "1", dst]
    sh(*args)


def stage_strips():
    rows = jload(f"{OUT}/results.json")
    sd = f"{OUT}/strips"
    need(sd)
    for m in rows:
        kf = f"{OUT}/keyframes/%s.png" % m["kf"]
        parts = ([kf] if os.path.exists(kf) else [])
        labels = (["KEYFRAME"] if parts else [])
        for i, ix in enumerate(m["sample_idx"]):
            parts.append("%s/_frames/%s_%02d.png" % (OUT, m["id"], i))
            labels.append("f%d  %.2fs" % (ix, ix / float(FPS)))
        head = ("%s   %s @ %s   lora %.2f   %.2fs"
                % (m["id"], m["motion_id"], m["place"], m["lora"], m["secs"]))
        sub = "MOTION STRING: %s" % m["text"]
        d = m.get("drift_struct")
        sub2 = ("motion %.3f  churn %.2f  creep %.3f  |  head drift f0->last  struct %s  hue %s"
                % (m["motion"], m["churn"], m.get("creep", 0),
                   ("%.1f" % d[-1]) if d else "excluded",
                   ("%.1f" % m["drift_hue"][-1]) if m.get("drift_hue") else "-"))
        _hstack(parts, labels, "%s/%s.png" % (sd, m["id"]), 330, head, sub, sub2,
                cellh=int(round(330 * VH / float(VW))))
        print("strip %s" % m["id"])


def stage_faces(size=300):
    """The same frames as HEAD CROPS, upscaled. A head is ~150px in a 1280x704 frame and
    a strip cell is 330px wide - at that scale a face that has become a different face is
    not distinguishable from one that has not, and every identity claim would be
    unearned. This is where identity is actually judged."""
    rows = jload(f"{OUT}/results.json")
    sd = f"{OUT}/faces"
    tmp = "/tmp/cast_motion_face"
    need(sd, tmp)
    for m in rows:
        box = frac_box(m["head_box"], VW, VH)
        parts, labels = [], []
        kf = f"{OUT}/keyframes/%s.png" % m["kf"]
        if os.path.exists(kf):
            k = "%s/%s_kf.png" % (tmp, m["id"])
            # the keyframe is 1344x768; scale it to the video frame before cropping so the
            # same fractions describe the same part of the picture
            Image.open(kf).convert("RGB").resize((VW, VH), Image.LANCZOS).crop(box)\
                 .resize((size, size), Image.LANCZOS).save(k)
            parts.append(k)
            labels.append("KEYFRAME")
        for i, ix in enumerate(m["sample_idx"]):
            src = "%s/_frames/%s_%02d.png" % (OUT, m["id"], i)
            if not os.path.exists(src):
                continue
            c = "%s/%s_%02d.png" % (tmp, m["id"], i)
            Image.open(src).convert("RGB").crop(box)\
                 .resize((size, size), Image.LANCZOS).save(c)
            parts.append(c)
            d = m.get("drift_struct")
            labels.append("f%d  %.2fs%s" % (ix, ix / float(FPS),
                                            "   d%.0f" % d[i] if d else ""))
        if not parts:
            continue
        head = "FACES  %s   %s @ %s   lora %.2f" % (m["id"], m["motion_id"], m["place"],
                                                    m["lora"])
        sub = ("crop window cx %.2f cy %.2f side %.2f of frame height - NOT a detector"
               % tuple(m["head_box"]))
        _hstack(parts, labels, "%s/%s.png" % (sd, m["id"]), size, head, sub, labsize=18)
        print("faces %s" % m["id"])


def stage_between(size=340):
    """The BETWEEN-clip judgement in one picture: the best face each 4s cell offers.

    Plus the reference sheet the whole cast pipeline is built on, first in the row, so the
    six clips are being compared against the thing they are supposed to look like rather
    than only against each other."""
    rows = {r["id"]: r for r in jload(f"{OUT}/results.json")}
    tmp = "/tmp/cast_motion_between"
    need(tmp)
    parts, labels = [], []
    sheet = os.path.join(COMFY, "input", card().get("sheet") or "")
    if os.path.exists(sheet):
        s = "%s/_sheet.png" % tmp
        im = Image.open(sheet).convert("RGB")
        w, h = im.size
        # the anime sheets are a row of views; the leading one is the front head
        im.crop((0, 0, min(w, h), min(w, h))).resize((size, size), Image.LANCZOS).save(s)
        parts.append(s)
        labels.append("REFERENCE SHEET")
    for cid, (idx, box_frac) in BETWEEN_PICK.items():
        m = rows.get(cid)
        if not m:
            continue
        box = frac_box(box_frac or m["head_box"], VW, VH)
        src = "%s/_frames/%s_%02d.png" % (OUT, cid, idx)
        if not os.path.exists(src):
            continue
        c = "%s/%s.png" % (tmp, cid)
        Image.open(src).convert("RGB").crop(box)\
             .resize((size, size), Image.LANCZOS).save(c)
        parts.append(c)
        labels.append("%s  f%d" % (cid, m["sample_idx"][idx]))
    _hstack(parts, labels, f"{OUT}/between.png", size,
            "BETWEEN CLIPS - the best face each 4s cell offers",
            "one character, six places, six motions, plus the LoRA-off control - "
            "is this one person?", labsize=17)
    print("wrote %s/between.png" % OUT)


def _grid(rows, dst, cellw=560):
    """rows is [[(path|None, label), ...], ...]."""
    tmp = "/tmp/cast_motion_grid"
    need(tmp)
    band = []
    for ri, row in enumerate(rows):
        parts, labels = [], []
        for p, lab in row:
            if p and os.path.exists(p):
                parts.append(p)
                labels.append(lab)
        if not parts:
            continue
        out = "%s/row%d.png" % (tmp, ri)
        _hstack(parts, labels, out, cellw, "", None, None, labsize=22)
        band.append(out)
    args = ["ffmpeg", "-y", "-hide_banner", "-v", "error"]
    for p in band:
        args += ["-i", p]
    args += ["-filter_complex", "vstack=inputs=%d" % len(band), "-frames:v", "1", dst]
    sh(*args)


# ═══════════════════════════════════════════════════════════════════ report
def stage_report():
    rows = jload(f"{OUT}/results.json")
    print("\n%-24s %-14s %6s %6s %6s %6s %7s %7s" %
          ("cell", "motion card", "secs", "YDIF", "churn", "creep", "dStruct", "dHue"))
    for r in rows:
        d, h = r.get("drift_struct"), r.get("drift_hue")
        print("%-24s %-14s %6.2f %6.3f %6.2f %6.3f %7s %7s" %
              (r["id"], r["motion_id"], r["secs"], r["motion"],
               r["churn"], r.get("creep", 0),
               ("%.1f" % d[-1]) if d else "excl", ("%.1f" % h[-1]) if h else "excl"))
    print("\nDRIFT OVER TIME (head crop vs frame 0, struct)")
    for r in rows:
        d = r.get("drift_struct")
        if not d:
            continue
        print("%-24s %s" % (r["id"], "  ".join("%4.0f" % x for x in d)))
        print("%-24s %s" % ("", "  ".join("%4.1f" % (i / float(FPS))
                                          for i in r["sample_idx"])))


def main():
    global ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument("stages", nargs="*", default=["all"])
    ap.add_argument("--char", default="VIRO")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only")
    ARGS = ap.parse_args()
    st = ARGS.stages or ["all"]
    if "all" in st:
        st = ["keyframes", "clips", "measure", "strips", "faces", "between"]
    for s in st:
        print("\n=== %s ===" % s.upper(), flush=True)
        {"strength": lambda: stage_strength(ARGS.force),
         "keyframes": lambda: stage_keyframes(ARGS.force),
         "clips": lambda: stage_clips(ARGS.force, ARGS.only),
         "measure": stage_measure,
         "strips": stage_strips,
         "faces": stage_faces,
         "between": stage_between,
         "report": stage_report}[s]()


if __name__ == "__main__":
    main()
