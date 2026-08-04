#!/usr/bin/env python3
"""motion_staging.py - IS A MOTION CARD'S NUMBER A PROPERTY OF THE CARD, OR OF THE KEYFRAME?

    ~/ComfyUI/venv/bin/python3 studio/_tools/motion_staging.py keyframes
    ~/ComfyUI/venv/bin/python3 studio/_tools/motion_staging.py sheet
    ~/ComfyUI/venv/bin/python3 studio/_tools/motion_staging.py stage
    ~/ComfyUI/venv/bin/python3 studio/_tools/motion_staging.py clips
    ~/ComfyUI/venv/bin/python3 studio/_tools/motion_staging.py measure strips report
    ~/ComfyUI/venv/bin/python3 studio/_tools/motion_staging.py cards

    Run under the ComfyUI venv. Rendering works under system python3; every number below
    needs numpy and system python3 on this box has none.

WHY THIS TOOL EXISTS
--------------------
Every `measured` block in studio/motions/ - motion_per_seed, band 0.406-0.744, frame-scale
ceiling 1.191 - came from ONE keyframe: studio/samples/motion_probe/_keyframe.png, a
qwen-rendered woman standing at mid distance in a station cafe. motion_examples.py was
right to hold that keyframe constant; a sweep that changes two things measures neither.
But a constant that is never varied becomes an assumption, and the cards quote its numbers
at a user as though they were properties of the card.

cast_motion.py then ran the same cards against six DIFFERENT keyframes and the bands did
not survive:

    walk_in       card mean 3.191, "above the ceiling on all three seeds, the best card in
                  the library"  ->  0.380 on c1_walk_in, BELOW the do-nothing band
    hand_to_face  card mean 0.619, "a small articulated gesture"
                  ->  0.708, and it walked the subject the length of a subway platform
    cup_lift      card mean 0.809  ->  2.080
    head_turn     card mean 0.592  ->  1.221

Its own read of the strips is that THE KEYFRAME'S STAGING DECIDED HOW MUCH MOVED: c1 has
the man in a tight waist-up shot with nowhere to walk, so the biggest card in the library
did nothing; c3 has him small and distant with a platform in front of him, so a hand
gesture became a walk.

THAT READ IS PLAUSIBLE AND IT IS NOT YET MEASURED, because cast_motion's design cannot
separate the two candidate causes. Every cell there changed the card AND the place AND the
staging at once - one cell per card, one card per keyframe. `walk_in` was low and `cup_lift`
was high, but so was `stadium_concourse` low and `library_reading_room` high, and nothing in
that matrix can tell them apart. It is a fully confounded design, which is the correct
design for the question IT asked (does a cast member survive moving?) and the wrong one for
this question.

THE DESIGN THIS TOOL USES
-------------------------
CROSSED, NOT PAIRED. Every subject-family card is rendered against EVERY staging, at the
SAME three seeds, so card and keyframe are separable terms instead of one confounded term.

ONE SCENE, THREE STAGINGS. The three keyframes are the SAME woman in the SAME station cafe
with the SAME nouns present - hands, loose hair, a cup on a table, a curtain, a rain-streaked
window. The prompt differs in ONE clause: where she stands and how much of the frame she
fills. If place, subject and content had also moved, "the staging did it" would be exactly
the unfalsifiable claim this tool exists to test.

    far     a small distant figure, the whole foreground floor between her and the lens
    mid     full length head to toe - the library keyframe's own staging
    close   seated chest-up, filling the frame, no floor in shot at all

Staging is then MEASURED rather than asserted (stage `staging`): the coat is the only large
dark-green thing in the scene, so its largest connected component is her, and the fraction
of frame it covers is the run's number for how close she is staged. It came out
far 0.19%, anchor 3.80%, mid 4.33%, close 7.92% - a 42x range, with mid landing next to
anchor exactly as that control cell required.

MID IS THE CONTROL FOR "ANY DIFFERENT KEYFRAME MOVES THE NUMBER". It is a different render
from the library's keyframe - different seed, different image - staged the same way. If mid
reproduces the library's figures while far and close diverge, the cause is staging. If mid
diverges too, the cause is merely "a different keyframe" and the finding is broader and
worse: no keyframe's numbers predict any other keyframe's.

THE ANCHOR ROW IS FREE. The library's own 105 clips are still on disk at
~/ComfyUI/output/claude-generated/motion-lib/cards/, rendered at these exact seeds. Stage
`measure` re-measures those files with this tool's code and records them as the `anchor`
staging. That does two jobs at once: it supplies a fourth staging at no GPU cost, and it
CHECKS THIS TOOL AGAINST THE NUMBERS ALREADY ON THE CARDS. If the anchor row does not
reproduce motion_per_seed, the measurement changed and nothing else here can be trusted -
stage `report` fails loudly on that rather than printing a comparison of two different
statistics.

EVERY KEYFRAME DERIVES ITS OWN BAND. motion_examples.lib_band() already established that
the do-nothing band is not a constant - the same empty string measured 0.34-0.61 on one
seed set and 0.68-0.99 on another. So each staging renders its own `_ctl_empty` and
`_ctl_production` cells at the same three seeds, and its band is min/max of its own six
controls, with the ceiling at hi*1.6. Identical derivation to the run being re-examined, so
the bands are comparable.

WHAT IS BEING TESTED, STATED SO IT CAN FAIL
-------------------------------------------
Three nested claims, weakest to strongest. Stage `report` decides between them:

    RAW    the card's motion number transfers      -> keep quoting one band
    RATIO  motion / that keyframe's control mean transfers, though the raw number does not
           -> quote a ratio, and the band becomes a per-keyframe measurement
    RANK   neither transfers, but the card ORDER survives
           -> cards may say "bigger mover than X", never "3.191"
    NONE   not even the order survives
           -> the number is a property of the staging. Cards stop quoting it.

WHAT THIS RUN FOUND (2026-08-04, 14 subject cards x 4 stagings x 3 seeds = 168 cells,
144 rendered here and 24 re-measured from the library's own lab)
------------------------------------------------------------------------------------
ANCHOR CHECK PASSED EXACTLY. Re-measuring the library's own clips reproduced all 42
motion_per_seed figures on the cards to 0.0000, and re-derived its band as 0.406-0.744.
So everything below is a comparison of like with like, not of two statistics.

1. THE BAND IS NOT A CONSTANT. Measured from each staging's OWN controls at the same
   seeds: far 0.475-0.762, mid 0.311-0.734, anchor 0.406-0.744, and CLOSE 0.464-1.998.
   The close band is more than four times as wide as the one the library published, and
   its ceiling is 3.197 against the library's 1.191.

2. WHY `close` IS SO WIDE, AND IT IS NOT NOISE. WATCH close/_ctl_empty. Given NO TEXT AT
   ALL, the model has her raise both hands, cover her face, gesture and lower them - it
   invents subject business when the subject is close and nothing has been asked. So at a
   close staging the do-nothing floor already contains the very gesture hand_to_face
   exists to request, and no card can be distinguished from silence there.

3. 11 OF 14 CARDS CHANGE THEIR BAND VERDICT BETWEEN STAGINGS. The same card, same seeds,
   same clip length, is reported to a user as "does nothing" at one staging and
   "frame-scale event" at another.

4. THE NUMBER TRACKS HOW MANY PIXELS THE SUBJECT COVERS, NOT HOW MUCH SHE MOVED. The
   cleanest pair in the run: turn_away performs the SAME completed turn at all four
   stagings and measures 0.583 / 0.682 / 2.759 / 0.668 - a 4.7x spread for an identical
   action. And walk_in is measured BACKWARDS: 1.115 at `far`, where she crosses the entire
   hall and exits past the lens, against 3.592 at `close`, where she never leaves her
   chair and the number is the framing creeping behind a subject big enough to fill the
   frame. An empty prompt on a close-up (1.998) outscores the library's best card
   performing its largest possible displacement on a wide (0.878 on that seed).

5. NORMALISING DOES NOT RESCUE IT. Dividing by each staging's own control mean makes the
   spread WORSE, not better: largest between-staging swing 2.477 raw, 3.211 normalised.

6. AND IT IS NOT ONLY STAGING - IT IS THE KEYFRAME. `mid` was built to reproduce the
   anchor's staging and does, to within a tenth of a percent of subject scale (4.33% of
   frame against 3.80%). Its numbers still disagree with the anchor's by up to 1.691, and
   walk_in reads 1.500 there against 3.191 on the anchor. Two keyframes staged the same
   way, at the same seeds, do not agree. Staging is the part of it that can be MEASURED,
   which is why subject_scale is recorded on every card; it is not the whole of it.

   VERDICT: RANK. No figure transfers. The card order survives weakly (mean rank
   correlation 0.727 across the six staging pairs, but only 0.46-0.48 against `close`).
   So the cards stop quoting a band, keep their anchor figures under *_anchor_only names,
   and carry a per_staging table instead.

7. THINGS THAT ARE PROPERTIES OF THE CARD AFTER ALL, found only because staging varied:
   walk_out is the one subject card that lands at every staging - the subject is gone by
   f72-f96 whether she starts as 0.2% of the frame or fills it, because leaving frame is a
   path that exists at any shot size. step_back never produces a step backward at ANY
   staging. cup_lift's precondition is not "a cup in frame" but "a cup within reach" -
   staged across a room it becomes the subject walking out of shot. hand_to_face_only's
   hold clause does work the plain card does not, but only on wides, which is exactly why
   one mid-distance keyframe could never have shown it.

A HAZARD FOR WHOEVER TOUCHES THESE CARDS NEXT
---------------------------------------------
motion_examples.py `lib-verdict` REPLACES c["measured"] wholesale (motion_examples.py:1441)
and would silently delete every per_staging block this tool wrote, restoring the single
band. Its verdict-preserving branch does cover this run - these verdicts do not start with
"RENDERED 2026-08-04", so they would be moved to verdict_prior rather than lost - but the
MEASUREMENTS would go. Re-run `motion_staging.py cards --write` after any lib-verdict pass,
or teach that writer to merge. Not changed here: motion_examples.py belongs to another wave.

WHAT IS MEASURED
    motion / churn / frozen   scripts/analyze_shots.py, the shipped module. Headline.
    creep                     video_engines.zoom_est, as motion_probe uses it.
    regions, dx/dy            motion_probe's own helpers, IMPORTED not reimplemented, so a
                              number here means the same thing as a number on a card.

AND THE NUMBERS DO NOT DECIDE. This project has ranked a clip best in sweep while the
subject's hair had covered her face, and cast_motion's worst drift figure was its best cell.
`strips` writes a labelled strip AND a subject-crop detail strip for every cell, the detail
crop set per staging because a raised forearm is a different fraction of the frame at each
one - which is itself part of the finding. Every verdict written by `cards` came from
looking at those.

READ THE OUTPUT IN THIS ORDER
    _keyframes.png        the three stagings side by side. What the whole run varies.
    strips/<cell>.png     keyframe + 9 frames, labelled with card, staging, seed, number.
    detail/<cell>.png     the same frames cropped to the subject. Small actions live here.
    grid_<card>.png       one card, three stagings, three seeds. The transfer question in
                          one picture, per card.
    report.txt            bands per staging, the three transfer tests, and the verdict.
    results.json          every number.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid

# analyze_shots.py does os.environ.setdefault("COMFY_ROOT", "Z:/ComfyUI") - a Windows SMB
# path - and epic.py reads COMFY_ROOT at import. Set it FIRST, exactly as motion_probe.py
# does, or every path resolves to a share that is not mounted here.
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                 # .../studio
REPO = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, HERE)

from analyze_shots import motion as ydif_motion, frozen_seconds        # noqa: E402
from comfy import api, set_path as sp                                  # noqa: E402
import motion_probe as MP                                              # noqa: E402

COMFY = os.environ["COMFY_ROOT"]
HOST = os.environ.get("COMFY_HOST", "127.0.0.1:8188")
REL = "claude-generated/motion-staging"
LAB = f"{COMFY}/output/{REL}"
OUT = f"{ROOT}/samples/motion_staging"
MOTIONDIR = f"{ROOT}/motions"
FONT = "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf"
VENV = os.path.expanduser("~/ComfyUI/venv/bin/python3")

# The library run's config, verbatim, because these numbers have to be readable against the
# numbers already on the cards. 1280x704 (short.py:66), 97 frames (8n+1, 4.04s at 24fps),
# workflow 12, seeds 7701-7703.
W, H = 1280, 704
FPS = 24
FRAMES = 97
SEEDS = [7701, 7702, 7703]

# The library's own lab, re-measured for free as the `anchor` staging.
LIB_LAB = f"{COMFY}/output/claude-generated/motion-lib/cards"

# ── the three stagings ────────────────────────────────────────────────────────
# ONE scene. The clause that differs is marked. Everything else - the woman, the coat, the
# cafe, the rain, the pillar, the curtain, the cup, the fence, the light - is held word for
# word, so a difference between two of these keyframes is a difference in staging and not
# in what is in the room.
#
# The nouns are held on purpose: cup_lift needs a cup on a surface, hair_lifts needs loose
# hair, hand_to_face and hand_reach need a visible hand. A card whose precondition is absent
# is not being tested, it is being sabotaged, and this project has already measured that a
# motion naming something absent makes LTX invent it.
#
# WORD ORDER IS PART OF THE STAGING, not decoration. The first pass wrote all three
# prompts as "A young woman ... <shot size clause> ... <room>" and qwen returned three
# near-identical medium shots: leading with the person makes a portrait and the shot-size
# clause loses. The prompts below lead with whatever has to dominate the frame - the hall
# for `far`, her face for `close` - and that is what actually moved the framing. It was
# read off _sheet.png, not assumed.
_ROOM = ("an empty railway station cafe at night, heavy rain streaking down the tall arched "
         "windows, a thick stone pillar on the left, a long red velvet curtain hanging floor "
         "to ceiling on the right, a small round marble table with a white cup of coffee "
         "steaming on it")
_HER = ("a young woman in a dark green wool coat with long loose brown hair, facing the "
        "camera with her arms down at her sides and both hands visible")
_LOOK = "warm lamplight, sharp, detailed, cinematic, high contrast."

STAGINGS = [
    ("far",
     # ── THE ROOM IS THE SUBJECT AND SHE IS SCENERY IN IT. Three phrasings were swept
     # before this one. Naming her first, or asking directly for "extreme long shot" and
     # "she is very small in the frame", both returned a medium shot at ~45% of frame
     # height no matter how the size was worded - qwen renders a named person as a
     # portrait. What finally made her small was giving the sentence's subject to the
     # ARCHITECTURE and demoting her to a thing the architecture dwarfs.
     # THEN THE DEMOTION COST HER FACE. Rewriting her into a subordinate clause dropped the
     # "facing the camera" that every other staging keeps, and the first pick came back with
     # her BACK TO THE LENS - which would have given turn_away nothing to turn away from and
     # made walk_in a turn-then-walk. The facing clause is shouted here for that reason.
     "A cavernous empty railway station concourse at night photographed from very far back, "
     "the vaulted ceiling and the enormous wet tiled floor dominating the picture, tall "
     "rain-streaked arched windows, a stone pillar on the left, a long red velvet curtain "
     "on the right, a marble table with a steaming white cup of coffee. A woman in a dark "
     "green wool coat with long loose brown hair stands far away in the middle of the floor "
     "FACING THE CAMERA, a small distant figure dwarfed by the architecture, her whole body "
     "a tiny part of the frame, her arms down at her sides. Wide angle, vast scale, deep "
     "perspective, " + _LOOK,
     "subject small and distant, the whole foreground is floor she could travel across",
     5200),
    ("mid",
     # ── full length, feet on the floor, room to walk ──
     "Full length shot, head to toe, of " + _HER + ", standing on the tiled floor of " +
     _ROOM + ". Her whole body from her hair to her shoes is inside the frame with floor "
     "visible below her feet and open floor between her and the camera. Standing full body "
     "shot at conversational distance, " + _LOOK,
     "full length head to toe at conversational distance - the library keyframe's staging",
     5100),
    ("close",
     # ── HER FIRST, the room reduced to background. THE HANDS AND THE CUP ARE HELD IN
     # FRAME ON PURPOSE. A first pass asked for a head-and-shoulders portrait and got one -
     # with her hands cropped away, which would have confounded "no room to travel" with
     # "the card's noun is not in the picture", and hand_to_face, hand_reach and cup_lift
     # would have been measured against a frame that cannot contain their own precondition.
     # She is seated at the table so she can fill the frame AND keep her hands in it.
     "Close shot, the camera very close to her across a small table. " + _HER + ", seated, "
     "her head and shoulders large and filling the frame, cropped at the waist, no floor "
     "visible at all. Her hands rest on the marble table top in the near foreground at the "
     "bottom of the frame, a white cup of coffee steaming beside them. Behind her, out of "
     "focus, " + _ROOM + ". Tight close shot, shallow depth of field, " + _LOOK,
     "close - she fills the frame, the cup still in it, no floor to travel across",
     5100),
]
STAGING_IDS = [s[0] for s in STAGINGS]

# The staged input filenames. ONE file per staging, copied ONCE; every cell for that
# staging loads that literal file, so frame 0 is identical by construction and any
# difference between two cells of a staging is the text and the seed and nothing else.
def staged_name(sid):
    return f"mstage_{sid}.png"


# CHOSEN BY LOOKING at _sheet.png, not by trusting the prompt. qwen is not obliged to obey
# a shot-size clause and this run's whole validity rests on the three keyframes actually
# being far, mid and close. `sheet` renders KF_CANDIDATES seeds per staging; the index
# picked here is written down so the choice is auditable.
KF_CANDIDATES = 4
# PICKED BY LOOKING at _sheet.png. The three chosen frames, and why each beat its siblings:
#   far   [3]  the only candidate of the four where she is genuinely small - the other
#              three put her at medium distance no matter what the prompt said.
#   mid   [0]  the closest match to the ANCHOR's own staging, which is this cell's job:
#              windows left, curtain right, table and cup right, her full length at ~60% of
#              frame height. It is deliberately NOT the most different-looking mid.
#   close [3]  the only true close shot of the four; [0]-[2] came back as medium shots
#              barely tighter than `mid` and would have collapsed the ladder.
#              HONEST LIMITATION: at [3] she is cropped at the chest and HER HANDS BEGIN
#              OUTSIDE THE FRAME. The cup is in frame, her face is in frame, and a hand can
#              still rise INTO frame from below - which is what a close-up does in real
#              footage - but hand_to_face and hand_reach start this staging without their
#              mover's hand visible. That is a property of closing in, not a rigging error,
#              and it is reported with those cards rather than hidden.
KF_PICK = {"far": 0, "mid": 0, "close": 0}

# Subject crop for the detail strip. IT CANNOT BE ONE BOX ACROSS STAGINGS. That a raised
# forearm is a twentieth of a percent of the frame at `far` and several percent at `close`
# is not an inconvenience for the tool - it is the mechanism the whole finding is about, and
# a fixed crop would hide it.
#
# So it is DERIVED, not typed in: `staging` measures the coat, and the crop is that box
# grown to take in the head above it and the hands beside it. Typing four boxes by eye is
# how a crop ends up measuring an ear and a wall, which cast_motion.py had to write an
# EXCLUDE_FACE list to survive.
DETAIL_FALLBACK = "440:520:400:184"      # motion_examples.LIB_DETAIL, if no staging.json


def detail_crop(sid):
    """ffmpeg w:h:x:y around the subject, from the measured coat box."""
    p = f"{OUT}/staging.json"
    if not os.path.exists(p):
        return DETAIL_FALLBACK
    d = (jload(p) or {}).get(sid) or {}
    if not d.get("found"):
        return DETAIL_FALLBACK
    x0, y0, x1, y1 = d["box"]
    cw, chh = x1 - x0, y1 - y0
    # Up by 70% of the coat's height for the head, out by 70% of its width each side for the
    # arms, down by 20% for the hands and the table. Then clamped to the frame.
    x0 = max(0, int(x0 - 0.7 * cw))
    x1 = min(W, int(x1 + 0.7 * cw))
    y0 = max(0, int(y0 - 0.7 * chh))
    y1 = min(H, int(y1 + 0.2 * chh))
    # A crop far narrower than it is tall reads as a letterbox on a strip; keep it at least
    # 4:3-ish so a gesture to the side of the body is inside it.
    if (x1 - x0) < 0.75 * (y1 - y0):
        cx, half = (x0 + x1) // 2, int(0.375 * (y1 - y0))
        x0, x1 = max(0, cx - half), min(W, cx + half)
    return f"{x1 - x0}:{y1 - y0}:{x0}:{y0}"

# Controls. NOT cards - never written to studio/motions/. They exist so each staging's
# do-nothing band is measured on THAT staging rather than carried over from another one.
# Identical pair to motion_examples.LIB_CONTROLS, so the bands are derived the same way.
CONTROLS = [
    ("_ctl_empty", "", "the do-nothing floor - no text at all"),
    ("_ctl_production", "Slow deliberate movement only.",
     "compile.py:603 - what every beat of every film asked for until the library shipped"),
]


# ═══════════════════════════════════════════════════════════════════ helpers
def sh(*a, **kw):
    r = subprocess.run([str(x) for x in a], capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.stderr.write(f"FAIL {' '.join(str(x) for x in a)[:300]}\n{(r.stderr or '')[-1500:]}\n")
    return r


def need(*dirs):
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_wf(name):
    """Strip _comment/_notes keys. ComfyUI returns a bare 500 with no node_errors if a
    top-level string survives into /prompt - see scripts/comfy.py's note."""
    with open(f"{REPO}/workflows/{name}", encoding="utf-8") as f:
        return {k: v for k, v in json.load(f).items() if not k.startswith("_")}


def submit(wf):
    r = api(HOST, "/prompt", {"prompt": wf, "client_id": str(uuid.uuid4())})
    if "error" in r:
        raise RuntimeError(json.dumps(r)[:400])
    return r["prompt_id"]


def wait_all(pids, label="jobs", timeout=14400):
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
    st = rec.get("status") or {}
    if st.get("status_str") == "error":
        for m in st.get("messages") or []:
            if m[0] == "execution_error":
                return str(m[1].get("exception_message"))[:200]
        return "error"
    return None


def job_secs(rec):
    st = rec.get("status") or {}
    ts = [m[1].get("timestamp") for m in st.get("messages") or [] if len(m) > 1
          and isinstance(m[1], dict) and m[1].get("timestamp")]
    return round((max(ts) - min(ts)) / 1000.0, 2) if len(ts) > 1 else None


# ═══════════════════════════════════════════════════════════════════ the cards
def subject_cards():
    """Every family=subject card in the library, in a stable order. Read from disk rather
    than listed here so a card added later is measured without editing this tool."""
    out = []
    for p in sorted(os.listdir(MOTIONDIR)):
        if not p.endswith(".json"):
            continue
        d = jload(f"{MOTIONDIR}/{p}")
        if d.get("family") == "subject":
            out.append((d["id"], d.get("text") or "", d.get("desc") or ""))
    return out


def cells():
    """(cell_id, text, want, is_control). Cards first, controls last."""
    rows = [(cid, txt, want, False) for cid, txt, want in subject_cards()]
    rows += [(cid, txt, want, True) for cid, txt, want in CONTROLS]
    return rows


# ═══════════════════════════════════════════════════════════════════ keyframes
def latest(tag, ext):
    """The NEWEST output for a tag, by ComfyUI's own numeric suffix.

    THIS FUNCTION EXISTS BECAUSE OF A BUG THAT ALREADY WASTED A PASS. ComfyUI does not
    overwrite: filename_prefix `kf_far_0` writes kf_far_0_00001_.png, and the next run of
    the SAME prefix writes kf_far_0_00002_.png. Every reader here used to hardcode
    _00001_, so `--force` faithfully re-rendered nine keyframes with a new prompt and then
    built the contact sheet out of the previous prompt's nine. Two rounds of "the prompt
    still is not obeyed" were actually "you are looking at the old picture."
    `--force` also deletes the tag's files first so the counter restarts, but every read
    goes through here regardless - belt and braces, because the failure is silent."""
    import glob
    import re as _re
    # The tag is anchored on both sides: `far__walk_in__s7701` must not also match
    # `far__walk_in_only__s7701`, and glob alone would not stop it.
    # ComfyUI's shape is <prefix>_00001_.png - note the underscore AFTER the counter and
    # before the dot. Getting that wrong matched nothing and printed MISSING for twelve
    # files that were sitting right there.
    pat = _re.compile(r"^%s_(\d+)_%s$" % (_re.escape(tag), _re.escape(ext)))
    hits = []
    for p in glob.glob(f"{LAB}/{tag}_*{ext}"):
        m = pat.match(os.path.basename(p))
        if m:
            hits.append((int(m.group(1)), p))
    return max(hits)[1] if hits else None


def clear(tag, ext):
    """Delete a tag's outputs so a forced re-render starts at _00001_ again."""
    import glob
    import re as _re
    pat = _re.compile(r"^%s_(\d+)_%s$" % (_re.escape(tag), _re.escape(ext)))
    for f in glob.glob(f"{LAB}/{tag}_*{ext}"):
        if pat.match(os.path.basename(f)):
            os.remove(f)


def _kf_wf(text, seed, tag):
    wf = load_wf("13_qwen_t2i_styled.json")
    sp(wf, "10.inputs.text", text)
    sp(wf, "12.inputs.width", W)
    sp(wf, "12.inputs.height", H)
    sp(wf, "13.inputs.seed", int(seed))
    sp(wf, "15.inputs.filename_prefix", f"{REL}/{tag}")
    return wf


def stage_keyframes(force=False):
    """KF_CANDIDATES seeds per staging. Nothing is staged yet - `sheet` then `stage` do that,
    after a person has looked."""
    need(LAB, OUT)
    jobs = []
    for sid, text, _desc, base in STAGINGS:
        if ARGS.staging and sid != ARGS.staging:
            continue
        for i in range(KF_CANDIDATES):
            tag = f"kf_{sid}_{i}"
            if latest(tag, ".png") and not force:
                print(f"  = {tag}")
                continue
            if force:
                clear(tag, ".png")
            print(f"  > {tag}")
            jobs.append(submit(_kf_wf(text, base + i, tag)))
    if jobs:
        wait_all(jobs, "keyframes")
    for sid, _t, _d, _b in STAGINGS:
        for i in range(KF_CANDIDATES):
            f = latest(f"kf_{sid}_{i}", ".png")
            print(f"  {'ok ' if f else 'MISSING'} {os.path.basename(f) if f else f'kf_{sid}_{i}'}")


def stage_sheet():
    """Every candidate, labelled, in one picture, next to the library's own keyframe. LOOK
    AT IT AND SET KF_PICK - the run is worthless if `close` is not actually close."""
    need(OUT)
    rows = []
    lib = f"{ROOT}/samples/motion_lib/_keyframe.png"
    if os.path.exists(lib):
        rows.append([(lib, "ANCHOR - the library keyframe every card was measured on")]
                    + [(None, "")] * (KF_CANDIDATES - 1))
    for sid, _t, desc, base in STAGINGS:
        row = []
        for i in range(KF_CANDIDATES):
            f = latest(f"kf_{sid}_{i}", ".png")
            row.append((f, f"{sid} [{i}] seed {base + i} - "
                           f"{os.path.basename(f).split('_')[-2] if f else '??'} - {desc}"))
        rows.append(row)
    _grid(rows, f"{OUT}/_sheet.png", cellw=560)
    print(f"wrote {OUT}/_sheet.png - LOOK AT IT, then set KF_PICK and run `stage`.")


def stage_stage(force=False):
    """Copy the picked keyframe of each staging into ComfyUI/input, ONCE."""
    need(OUT, f"{OUT}/keyframes")
    for sid, _t, _d, _b in STAGINGS:
        i = KF_PICK[sid]
        src = latest(f"kf_{sid}_{i}", ".png")
        if not src:
            raise SystemExit(f"no candidate {i} for {sid} - run `keyframes` first")
        shutil.copy(src, f"{COMFY}/input/{staged_name(sid)}")
        shutil.copy(src, f"{OUT}/keyframes/{sid}.png")
        print(f"  staged {sid} <- candidate {i} ({os.path.basename(src)})  -> "
              f"{COMFY}/input/{staged_name(sid)}")
    lib = f"{ROOT}/samples/motion_lib/_keyframe.png"
    if os.path.exists(lib):
        shutil.copy(lib, f"{OUT}/keyframes/anchor.png")
    _grid([[(f"{OUT}/keyframes/{s}.png", f"{s} - {d}") for s, _t, d, _b in STAGINGS]],
          f"{OUT}/_keyframes.png", cellw=600)
    print(f"wrote {OUT}/_keyframes.png")


# ══════════════════════════════════════════════════════════ staging as a number
# `far`, `mid` and `close` are adjectives, and this project has been burned by adjectives
# before - the whole motion library exists because "slow deliberate movement" turned out to
# mean nothing to the model. If the finding is going to be "the staging set the number",
# then staging has to BE a number measured off the keyframe, or the claim is prose that
# cannot be checked.
#
# There is no person detector on this box; cast_proof.py records one being built and thrown
# away. What there IS, by construction, is a woman in a DARK GREEN WOOL COAT in a scene
# whose every other surface is stone, glass, red velvet or warm lamplight. So the coat is
# the marker: green-dominant dark pixels are hers, and their bounding box is her. That is a
# cheap trick, and it is CHECKED - `staging` draws the box it found back onto the keyframe
# and _staging.png was looked at before any of these numbers were used for anything.
COAT_SRC = '''
import sys, json
import numpy as np
from PIL import Image
from scipy import ndimage
a = np.asarray(Image.open(sys.argv[1]).convert("RGB"), dtype=np.int16)
R, G, B = a[..., 0], a[..., 1], a[..., 2]
m = (G > R + 8) & (G > B + 4) & (G < 130) & (a.max(axis=2) < 150)
h, w = m.shape
# LARGEST CONNECTED COMPONENT, not every matching pixel. A first pass took the bounding box
# of the whole mask and drew a box a third of the frame wide around a woman the size of a
# thumbnail: dim arches and rain-dark window glass also pass a "green-ish and dark" test,
# and they are scattered right across the picture. The coat is one blob; the contamination
# is confetti. Closing first so the coat does not split at her belt.
m = ndimage.binary_closing(m, np.ones((5, 5)))
lab, n = ndimage.label(m)
if n == 0:
    print(json.dumps({"found": 0}))
    sys.exit()
sizes = ndimage.sum(m, lab, range(1, n + 1))
big = int(np.argmax(sizes)) + 1
coat = lab == big
ys, xs = np.nonzero(coat)
y0, y1, x0, x1 = int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())
print(json.dumps({
    "found": int(coat.sum()),
    "components": int(n),
    "box": [x0, y0, x1, y1],
    "coat_h_frac": round((y1 - y0) / h, 4),
    "coat_area_frac": round(float(coat.sum()) / (h * w), 4),
    "cx": round((x0 + x1) / 2 / w, 4),
    "feet_y_frac": round(y1 / h, 4),
    "frame_below_frac": round((h - y1) / h, 4),
}))
'''


def coat_box(png):
    tmp = "/tmp/mstage_coat"
    need(tmp)
    src = f"{tmp}/_coat.py"
    open(src, "w").write(COAT_SRC)
    r = subprocess.run([VENV, src, png], capture_output=True, text=True)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {"found": 0, "err": (r.stderr or "")[-200:]}


def stage_staging():
    """Measure each keyframe's staging and DRAW THE BOX so the measurement can be checked."""
    need(OUT, f"{OUT}/keyframes")
    out, rows = {}, []
    for sid in STAGING_IDS + ["anchor"]:
        kf = f"{OUT}/keyframes/{sid}.png"
        if not os.path.exists(kf):
            continue
        d = coat_box(kf)
        out[sid] = d
        if not d.get("found"):
            print(f"  {sid:8s} NO COAT FOUND {d}")
            continue
        x0, y0, x1, y1 = d["box"]
        drawn = f"{OUT}/keyframes/_boxed_{sid}.png"
        sh("ffmpeg", "-y", "-v", "error", "-i", kf, "-vf",
           f"drawbox=x={x0}:y={y0}:w={x1 - x0}:h={y1 - y0}:color=yellow:t=3", drawn)
        rows.append([(drawn, f"{sid}   coat {d['coat_h_frac'] * 100:.0f}% of frame height   "
                             f"area {d['coat_area_frac'] * 100:.1f}%   "
                             f"frame below her feet {d['frame_below_frac'] * 100:.0f}%")])
        print(f"  {sid:8s} coat h {d['coat_h_frac']:.3f}  area {d['coat_area_frac']:.4f}  "
              f"cx {d['cx']:.3f}  feet {d['feet_y_frac']:.3f}  "
              f"below {d['frame_below_frac']:.3f}")
    _grid(rows, f"{OUT}/_staging.png", cellw=900)
    json.dump(out, open(f"{OUT}/staging.json", "w"), indent=1)
    print(f"wrote {OUT}/staging.json and {OUT}/_staging.png - LOOK at the boxes.")


# ═══════════════════════════════════════════════════════════════════ clips
def stage_clips(force=False, only=None, only_staging=None):
    """The whole matrix, submitted contiguously so the LTX checkpoint loads once."""
    need(LAB, OUT)
    rows = [c for c in cells() if (not only or only in c[0])]
    sids = [s for s in STAGING_IDS if (not only_staging or s == only_staging)]
    for sid in sids:
        if not os.path.exists(f"{COMFY}/input/{staged_name(sid)}"):
            raise SystemExit(f"run `stage` first - {staged_name(sid)} is not in input/")
    jobs, meta = [], {}
    for sid in sids:
        for seed in SEEDS:
            for cid, text, want, isctl in rows:
                tag = f"{sid}__{cid}__s{seed}"
                if latest(tag, ".mp4") and not force:
                    print(f"  = {tag}")
                    continue
                if force:
                    clear(tag, ".mp4")
                wf = load_wf("12_ltx23_i2v_audio.json")
                sp(wf, "8.inputs.image", staged_name(sid))
                sp(wf, "10.inputs.text", text)
                sp(wf, "20.inputs.width", W)
                sp(wf, "20.inputs.height", H)
                sp(wf, "20.inputs.length", FRAMES)
                sp(wf, "21.inputs.frames_number", FRAMES)
                sp(wf, "32.inputs.noise_seed", int(seed))
                sp(wf, "43.inputs.filename_prefix", f"{REL}/{tag}")
                # node 9 img_compression and node 11 negative are LEFT AS THE FILE HAS THEM.
                # short.py sets neither; changing them would measure a different app.
                pid = submit(wf)
                jobs.append(pid)
                meta[pid] = dict(id=tag, staging=sid, card=cid, seed=seed, text=text,
                                 want=want, control=isctl)
                print(f"  > {tag}")
    recs = wait_all(jobs, "clips")
    man = f"{OUT}/manifest.json"
    prev = jload(man) if os.path.exists(man) else []
    for pid in jobs:
        m = dict(meta[pid])
        rec = recs.get(pid, {})
        m["secs"] = job_secs(rec)
        m["error"] = job_error(rec)
        m["file"] = job_file(rec) or latest(m["id"], ".mp4")
        prev = [r for r in prev if r["id"] != m["id"]]
        prev.append(m)
    # cells that already existed and were skipped still need manifest rows
    for sid in sids:
        for seed in SEEDS:
            for cid, text, want, isctl in rows:
                tag = f"{sid}__{cid}__s{seed}"
                f = latest(tag, ".mp4")
                if f and not any(r["id"] == tag for r in prev):
                    prev.append(dict(id=tag, staging=sid, card=cid, seed=seed, text=text,
                                     want=want, control=isctl, secs=None, error=None, file=f))
    json.dump(prev, open(man, "w"), indent=1)
    print(f"wrote {man} ({len(prev)} rows)")


def anchor_rows():
    """The library's own clips, still on disk at the same seeds. Free fourth staging AND the
    check that this tool's measurement is the one the cards were written from."""
    out = []
    ids = [c[0] for c in cells()]
    for cid, text, want, isctl in cells():
        for seed in SEEDS:
            f = f"{LIB_LAB}/{cid}_s{seed}_00001_.mp4"
            if os.path.exists(f):
                out.append(dict(id=f"anchor__{cid}__s{seed}", staging="anchor", card=cid,
                                seed=seed, text=text, want=want, control=isctl,
                                secs=None, error=None, file=f))
    missing = {r for r in ids} - {r["card"] for r in out}
    if missing:
        print(f"  !! anchor missing {len(missing)} cards: {sorted(missing)}")
    return out


# ═══════════════════════════════════════════════════════════════════ measure
def stage_measure():
    MP.selftest()
    # The anchor row is on disk already and needs no GPU, so `measure` is allowed to run
    # before `clips` has produced anything - which is how the anchor check got run while
    # another job held the card.
    mp = f"{OUT}/manifest.json"
    man = jload(mp) if os.path.exists(mp) else []
    rows = man + anchor_rows()
    tmp = "/tmp/mstage"
    need(tmp)
    res = []
    for m in rows:
        f = m.get("file")
        if not f or not os.path.exists(f):
            print(f"skip {m['id']}: no file")
            continue
        r = dict(m)
        mo, ch = ydif_motion(f)                  # THE HEADLINE NUMBER. Shipped function.
        r["motion"] = round(mo, 4)
        r["churn"] = round(ch, 4)
        r["frozen"] = round(frozen_seconds(f), 2)
        r["frames"] = MP.nframes(f)
        r["regions"] = {k: MP._region_ydif(f, c) for k, c in MP.REGIONS.items()}
        r.update(MP.displacement(f, tmp))
        r.update(MP.framing_drift(f, tmp))
        res.append(r)
        print(f"{r['id']:36s} motion {r['motion']:7.3f}  churn {r['churn']:6.3f}  "
              f"creep {r.get('creep', 0):.3f}", flush=True)
    json.dump(res, open(f"{OUT}/results.json", "w"), indent=1)
    print(f"wrote {OUT}/results.json ({len(res)} clips)")


def bands(res):
    """Each staging's do-nothing band, from ITS OWN controls at these seeds. Same derivation
    as motion_examples.lib_band(): lo/hi are min/max of the controls, ceiling is hi*1.6."""
    out = {}
    for sid in STAGING_IDS + ["anchor"]:
        ctl = [r["motion"] for r in res if r["staging"] == sid and r.get("control")]
        if not ctl:
            continue
        out[sid] = dict(lo=round(min(ctl), 4), hi=round(max(ctl), 4),
                        ceiling=round(max(ctl) * 1.6, 3),
                        mean=round(sum(ctl) / len(ctl), 4), n=len(ctl))
    return out


def by_card(res):
    """{card: {staging: {motions, mean, creep}}}"""
    out = {}
    for r in res:
        out.setdefault(r["card"], {}).setdefault(r["staging"], []).append(r)
    agg = {}
    for card, per in out.items():
        agg[card] = {}
        for sid, rows in per.items():
            rows = sorted(rows, key=lambda x: x["seed"])
            ms = [x["motion"] for x in rows]
            agg[card][sid] = dict(motions=ms, mean=round(sum(ms) / len(ms), 4),
                                  seeds=[x["seed"] for x in rows],
                                  creep=round(sum(x.get("creep", 1.0) for x in rows) / len(rows), 3))
    return agg


# ═══════════════════════════════════════════════════════════════════ strips
def _esc(s):
    """drawtext escaping. The apostrophe is the hazard - the label sits inside a
    single-quoted filtergraph token, so a literal ' truncates it."""
    for a, b in (("\\", "\\\\"), (":", "\\:"), ("'", "\u2019"), ("%", "\\%"),
                 ("[", "\\["), ("]", "\\]")):
        s = s.replace(a, b)
    return s


def _label(src, dst, text, w=330, fs=13):
    sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vf",
       f"scale={w}:-2,pad=iw:ih+22:0:22:black,"
       f"drawtext=fontfile={FONT}:text='{_esc(text)}':x=4:y=4:fontsize={fs}:fontcolor=white",
       dst)
    return dst


def _grid(rows, dst, cellw=330, fs=13):
    """rows = [[(path|None, label), ...], ...]. Missing cells become black placeholders so a
    hole in the matrix is visible rather than silently reflowing the grid."""
    tmp = "/tmp/mstage_grid"
    need(tmp)
    shutil.rmtree(tmp, ignore_errors=True)
    need(tmp)
    rowpngs = []
    for ri, row in enumerate(rows):
        parts = []
        for ci, (p, lab) in enumerate(row):
            d = f"{tmp}/r{ri}c{ci}.png"
            if p and os.path.exists(p):
                _label(p, d, lab, cellw, fs)
            else:
                sh("ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                   f"color=c=black:s={cellw}x{int(cellw*0.55)+22}", "-frames:v", "1", d)
            parts.append(d)
        rp = f"{tmp}/row{ri}.png"
        # hstack, like vstack, needs two or more inputs. A one-cell row is legitimate here
        # (one keyframe per row in _staging.png) and silently produced nothing.
        if len(parts) == 1:
            shutil.copy(parts[0], rp)
        else:
            args = ["ffmpeg", "-y", "-v", "error"]
            for p in parts:
                args += ["-i", p]
            args += ["-filter_complex", f"hstack=inputs={len(parts)}", "-frames:v", "1", rp]
            sh(*args)
        rowpngs.append(rp)
    # vstack needs two or more inputs; a one-row grid is a legitimate call (the three
    # stagings side by side) and silently produced nothing until this branch existed.
    if len(rowpngs) == 1:
        shutil.copy(rowpngs[0], dst)
        return
    args = ["ffmpeg", "-y", "-v", "error"]
    for p in rowpngs:
        args += ["-i", p]
    args += ["-filter_complex", f"vstack=inputs={len(rowpngs)}", "-frames:v", "1", dst]
    sh(*args)


def _strip(m, dst, cols=9, crop=None, kf=None):
    """keyframe | N frames evenly spaced, LABELLED. The label is the point - a strip you
    cannot identify at a glance does not get looked at properly."""
    tmp = "/tmp/mstage_strip"
    need(tmp, os.path.dirname(dst))
    n = m.get("frames") or MP.nframes(m["file"])
    if n < 2:
        return None
    idxs = [round(i * (n - 1) / (cols - 1)) for i in range(cols)]
    parts, labels = ([kf], ["KEYFRAME"]) if kf and os.path.exists(kf) else ([], [])
    for i, ix in enumerate(idxs):
        parts.append(MP._frame_png(m["file"], ix, f"{tmp}/{i}.png"))
        labels.append(f"f{ix}")
    cut = []
    for i, (p, lab) in enumerate(zip(parts, labels)):
        d = f"{tmp}/c{i}.png"
        if crop:
            sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
               f"crop={crop},scale=330:-2,pad=iw:ih+22:0:22:black,"
               f"drawtext=fontfile={FONT}:text='{_esc(lab)}':x=4:y=4:fontsize=13:fontcolor=white",
               d)
        else:
            _label(p, d, lab)
        cut.append(d)
    band = f"{tmp}/band.png"
    args = ["ffmpeg", "-y", "-v", "error"]
    for p in cut:
        args += ["-i", p]
    args += ["-filter_complex", f"hstack=inputs={len(cut)}", "-frames:v", "1", band]
    sh(*args)
    head = (f"{m['staging']}  |  {m['card']}  |  seed {m['seed']}  |  "
            f"motion {m.get('motion', 0):.3f}  creep {m.get('creep', 1.0):.3f}  |  "
            f"\"{(m.get('text') or '(empty)')[:70]}\"")
    sh("ffmpeg", "-y", "-v", "error", "-i", band, "-vf",
       f"pad=iw:ih+30:0:30:black,"
       f"drawtext=fontfile={FONT}:text='{_esc(head)}':x=6:y=7:fontsize=17:fontcolor=yellow",
       dst)
    return dst


def stage_strips(only=None):
    res = jload(f"{OUT}/results.json")
    need(f"{OUT}/strips", f"{OUT}/detail")
    for m in res:
        if only and only not in m["id"]:
            continue
        kf = f"{OUT}/keyframes/{m['staging']}.png"
        _strip(m, f"{OUT}/strips/{m['id']}.png", kf=kf)
        _strip(m, f"{OUT}/detail/{m['id']}.png", crop=detail_crop(m["staging"]))
        print(f"  strip {m['id']}")
    print(f"wrote {OUT}/strips and {OUT}/detail")


def stage_grids():
    """One picture per card: three seeds down, four stagings across, last frame of each.
    This is the transfer question made visible for a card at a glance."""
    res = jload(f"{OUT}/results.json")
    need(f"{OUT}/grids")
    idx = {(r["staging"], r["card"], r["seed"]): r for r in res}
    tmp = "/tmp/mstage_last"
    need(tmp)
    for cid, _t, _w in subject_cards() + [(c[0], c[1], c[2]) for c in CONTROLS]:
        rows = []
        for seed in SEEDS:
            row = []
            for sid in STAGING_IDS + ["anchor"]:
                r = idx.get((sid, cid, seed))
                if not r:
                    row.append((None, f"{sid} s{seed} MISSING"))
                    continue
                n = r.get("frames") or 97
                p = MP._frame_png(r["file"], n - 1, f"{tmp}/{sid}_{cid}_{seed}.png")
                row.append((p, f"{sid} s{seed}  f{n-1}  motion {r['motion']:.3f}"))
            rows.append(row)
        _grid(rows, f"{OUT}/grids/{cid}.png", cellw=420)
        print(f"  grid {cid}")
    print(f"wrote {OUT}/grids")


# ═══════════════════════════════════════════════════════════════════ report
def _spearman(a, b):
    """Rank correlation without scipy. Ties get average ranks."""
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    ra, rb = ranks(a), ranks(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = sum((x - ma) ** 2 for x in ra) ** 0.5
    db = sum((y - mb) ** 2 for y in rb) ** 0.5
    return round(num / (da * db), 3) if da and db else 0.0


def stage_report():
    res = jload(f"{OUT}/results.json")
    bnd = bands(res)
    agg = by_card(res)
    sids = [s for s in STAGING_IDS + ["anchor"] if s in bnd]
    L = []

    def p(s=""):
        print(s)
        L.append(s)

    # ── the check that has to pass before anything else is readable ──────────
    p("ANCHOR CHECK - does this tool reproduce the numbers already on the cards?")
    p("  If these disagree, the measurement changed and nothing below is a comparison.")
    worst = 0.0
    for cid in sorted(agg):
        card_p = f"{MOTIONDIR}/{cid}.json"
        if not os.path.exists(card_p) or "anchor" not in agg[cid]:
            continue
        was = (jload(card_p).get("measured") or {}).get("motion_per_seed")
        if not was:
            continue
        now = agg[cid]["anchor"]["motions"]
        d = max(abs(a - b) for a, b in zip(was, now)) if len(was) == len(now) else 99
        worst = max(worst, d)
        flag = "" if d < 0.001 else "   <-- MISMATCH"
        p(f"  {cid:20s} card {['%.3f' % x for x in was]}  remeasured "
          f"{['%.3f' % x for x in now]}  maxdiff {d:.4f}{flag}")
    p(f"  worst disagreement {worst:.4f}  "
      f"{'OK - same statistic, same clips' if worst < 0.001 else 'FAILED'}")
    p()

    p("DO-NOTHING BAND, derived per staging from that staging's OWN controls, seeds "
      f"{SEEDS}")
    p("  staging    lo      hi      mean    ceiling(hi*1.6)")
    for sid in sids:
        b = bnd[sid]
        p(f"  {sid:9s}  {b['lo']:6.3f}  {b['hi']:6.3f}  {b['mean']:6.3f}  {b['ceiling']:6.3f}")
    p()

    p("PER-CARD MOTION MEAN BY STAGING   (ratio = mean / that staging's control mean)")
    hdr = "  card                " + "".join(f"{s:>18s}" for s in sids)
    p(hdr)
    for cid in sorted(agg, key=lambda c: -(agg[c].get("mid", {}).get("mean") or 0)):
        line = f"  {cid:20s}"
        for sid in sids:
            a = agg[cid].get(sid)
            if not a:
                line += f"{'-':>18s}"
                continue
            line += f"{a['mean']:9.3f}{a['mean'] / bnd[sid]['mean']:8.2f}x"
        p(line)
    p()

    # ── the three transfer tests ─────────────────────────────────────────────
    common = [c for c in agg if all(s in agg[c] for s in sids) and not c.startswith("_ctl")]
    common.sort()
    p(f"TRANSFER TESTS across {len(common)} cards present in every staging")
    p("  RAW    does the card's motion number survive a change of staging?")
    p("  RATIO  does motion / that staging's control mean survive?")
    p("  RANK   does the ORDER of the cards survive?")
    p()
    p("  NOTE ON THE TWO SPEARMAN COLUMNS: they are identical and MUST be. Dividing every")
    p("  card in a staging by that staging's control mean is one positive constant per")
    p("  staging, which cannot reorder anything, so rank correlation is blind to it. The")
    p("  column is printed anyway because seeing the two agree exactly is the check that")
    p("  the normalisation was applied per staging and not globally. What actually")
    p("  separates RAW from RATIO is the two max|diff| columns, which are on magnitudes.")
    p()
    p(f"  {'pair':22s} {'raw spearman':>13s} {'ratio spearman':>15s} "
      f"{'raw max |diff|':>15s} {'ratio max |diff|':>17s}")
    pairs = [(sids[i], sids[j]) for i in range(len(sids)) for j in range(i + 1, len(sids))]
    rho_raw, rho_ratio = [], []
    for a, b in pairs:
        va = [agg[c][a]["mean"] for c in common]
        vb = [agg[c][b]["mean"] for c in common]
        ra = [agg[c][a]["mean"] / bnd[a]["mean"] for c in common]
        rb = [agg[c][b]["mean"] / bnd[b]["mean"] for c in common]
        sr, ss = _spearman(va, vb), _spearman(ra, rb)
        rho_raw.append(sr)
        rho_ratio.append(ss)
        p(f"  {a + ' vs ' + b:22s} {sr:13.3f} {ss:15.3f} "
          f"{max(abs(x - y) for x, y in zip(va, vb)):15.3f} "
          f"{max(abs(x - y) for x, y in zip(ra, rb)):17.3f}")
    p()
    p(f"  mean rank correlation, raw {sum(rho_raw) / len(rho_raw):.3f}   "
      f"ratio {sum(rho_ratio) / len(rho_ratio):.3f}")
    p()

    p("BAND VERDICT PER CARD PER STAGING - what a user would be told at each staging")
    p("  (in band = indistinguishable from asking for nothing; above ceiling = frame-scale)")
    for cid in sorted(common):
        v = []
        for sid in sids:
            m = agg[cid][sid]["mean"]
            b = bnd[sid]
            v.append(f"{sid}:{'BELOW' if m < b['lo'] else 'IN-BAND' if m <= b['hi'] else 'MID' if m <= b['ceiling'] else 'FRAME-SCALE'}")
        same = len(set(x.split(":")[1] for x in v)) == 1
        p(f"  {cid:20s} {'  '.join(v):64s} {'consistent' if same else '<-- DISAGREES'}")
    p()

    # ── the verdict, decided by the thresholds and not by the writer's mood ──────
    # RAW survives only if a user could quote one number everywhere: no card may cross a
    # band boundary between stagings, and no card's mean may move by more than the width of
    # the band it is being judged against. That is the actual promise the cards make today.
    widest = max(b["hi"] - b["lo"] for b in bnd.values())
    raw_max = max(max(abs(agg[c][a]["mean"] - agg[c][b_]["mean"]) for a, b_ in pairs)
                  for c in common)
    crossers = [c for c in common
                if len({("below" if agg[c][s]["mean"] < bnd[s]["lo"] else
                         "in-band" if agg[c][s]["mean"] <= bnd[s]["hi"] else
                         "between" if agg[c][s]["mean"] <= bnd[s]["ceiling"] else
                         "frame-scale") for s in sids}) > 1]
    mean_raw = sum(rho_raw) / len(rho_raw)
    mean_ratio = sum(rho_ratio) / len(rho_ratio)
    # RATIO is judged on MAGNITUDE agreement, not on rank - see the note above, the rank
    # test cannot tell the two apart. Normalising has to actually shrink the spread to earn
    # the verdict, so it is compared against the raw spread it claims to fix.
    ratio_max = max(max(abs(agg[c][a]["mean"] / bnd[a]["mean"] -
                            agg[c][b_]["mean"] / bnd[b_]["mean"]) for a, b_ in pairs)
                    for c in common)
    if not crossers and raw_max <= widest:
        verdict = "raw"
    elif ratio_max < raw_max * 0.5:
        verdict = "ratio"
    elif mean_raw >= 0.6:
        verdict = "rank"
    else:
        verdict = "none"
    p("VERDICT")
    p(f"  cards that change band verdict between stagings: {len(crossers)}/{len(common)}"
      f"  {sorted(crossers)}")
    p(f"  widest band {widest:.3f}; largest between-staging swing in a card mean {raw_max:.3f}")
    p(f"  largest swing after control-normalising {ratio_max:.3f} - normalising "
      f"{'shrinks' if ratio_max < raw_max else 'does NOT shrink'} the spread")
    p(f"  mean rank correlation raw {mean_raw:.3f}, control-normalised {mean_ratio:.3f} "
      f"(identical by construction - see note above)")
    p(f"  -> TRANSFER = {verdict.upper()}")
    p({"raw": "  one band may keep being quoted.",
       "ratio": "  the raw number does not travel, but motion/control does - quote the "
                "ratio and measure the band per keyframe.",
       "rank": "  no number travels. The ORDER of the cards does. Cards may say bigger or "
               "smaller than another card; they may not quote a figure.",
       "none": "  nothing travels, not even the order. The number is a property of the "
               "staging and the cards must stop quoting it."}[verdict])
    p()

    open(f"{OUT}/report.txt", "w").write("\n".join(L) + "\n")
    json.dump(dict(bands=bnd, by_card=agg, seeds=SEEDS, stagings=sids,
                   spearman_raw=rho_raw, spearman_ratio=rho_ratio, pairs=pairs,
                   transfer=verdict, band_crossers=sorted(crossers),
                   widest_band=round(widest, 4), raw_max_swing=round(raw_max, 4),
                   anchor_check_worst=round(worst, 4)),
              open(f"{OUT}/summary.json", "w"), indent=1)
    print(f"wrote {OUT}/report.txt and {OUT}/summary.json")


# ═══════════════════════════════════════════════════════════════════ cards
# THE VERDICTS ARE TYPED HERE, NOT COMPUTED. Anything a number alone could tell you is
# generated below from results.json; this dict is only for what had to be WATCHED.
#
# THE EVIDENCE BEHIND EVERY LINE, stated so the claims can be weighed:
#   - samples/motion_staging/percard/<card>.png - the subject-crop strip at ALL FOUR
#     stagings, nine frames each, at SEED 7702. Every card below was read there.
#   - samples/motion_staging/grids/<card>.png - the LAST FRAME at all four stagings by all
#     THREE seeds. Read for walk_in, turn_away, cup_lift, hand_to_face and both controls.
#   - the three-seed numbers in measured.per_staging, for every card.
# So "lands 4/4 stagings" below means WATCHED AT ONE SEED across four stagings, with three
# seeds of numbers behind it - not watched at nine cells. Where a card's behaviour is
# claimed to be reliable, that is the strength of evidence available and it is said here
# rather than implied. `status` is deliberately NOT upgraded off it.
WATCHED = {
    "walk_in": (
        "RE-MEASURED ACROSS FOUR STAGINGS 2026-08-04, 3 seeds each, watched at 7702. THE "
        "CLEAREST CASE IN THE LIBRARY THAT THE NUMBER IS NOT THE CARD. far 1.115 / mid "
        "1.500 / close 3.592 / anchor 3.191 - and the ranking is BACKWARDS against what "
        "actually happens. At `far`, the lowest number in the row, she walks the entire "
        "length of the station hall and leaves the frame past the lens by f96: the largest "
        "displacement in the whole run. At `close`, the highest number in the entire "
        "matrix, SHE NEVER LEAVES HER CHAIR - the 4.278 on seed 7702 is the framing "
        "creeping (creep 1.325) and the background sliding behind a subject big enough to "
        "fill the frame. At `mid` she does not close distance either. THE CARD NEEDS "
        "DISTANCE TO CLOSE, and the metric rewards the stagings where there is none. Ask "
        "for it on a wide; do not read its number."),
    "walk_in_only": (
        "RE-MEASURED ACROSS FOUR STAGINGS 2026-08-04, 3 seeds each, watched at 7702. far "
        "0.823 / mid 1.151 / close 2.943 / anchor 2.476 on that seed, and it behaves "
        "exactly as [[walk_in]] does: full traverse and exit at `far`, no approach at all "
        "at `mid`, and at `close` she rises and drifts right without ever coming toward "
        "the lens. The `Nothing else in the frame moves` clause does not change where the "
        "card works, only how much of the rest of the frame joins in. Same rule: it needs "
        "distance to close."),
    "walk_out": (
        "RE-MEASURED ACROSS FOUR STAGINGS 2026-08-04, 3 seeds each, watched at 7702. THE "
        "MOST STAGING-ROBUST SUBJECT CARD IN THE LIBRARY. She is gone from the frame by "
        "f84 at `far`, f72 at `mid`, f72 at `close` and f96 at `anchor` - the ask lands at "
        "every subject scale from a figure 0.2% of the frame to one filling it, because "
        "leaving the frame is the one path that is available at any staging. Numbers 1.395 "
        "/ 1.266 / 2.036 / 1.226; they say nothing the strips do not say better. If a beat "
        "needs a subject exit and the staging is not known in advance, this is the card."),
    "turn_away": (
        "RE-MEASURED ACROSS FOUR STAGINGS 2026-08-04, 3 seeds each, watched at 7702. THE "
        "CLEANEST DEMONSTRATION IN THE RUN THAT THE NUMBER TRACKS SUBJECT SIZE AND NOT "
        "PERFORMANCE: she completes the same turn, back to the lens, in ALL FOUR stagings "
        "- and measures 0.583 / 0.682 / 2.759 / 0.668, a 4.7x spread for an identical "
        "action. The only thing that changed was how many pixels she covers while doing "
        "it. Reliable across staging; its figure is meaningless across staging."),
    "hand_to_face": (
        "RE-MEASURED ACROSS FOUR STAGINGS 2026-08-04, 3 seeds each, watched at 7702. The "
        "gesture COMPLETES at all four stagings - hand to the face by f48-f72 and held - "
        "and every one of the four means sits INSIDE that staging's own do-nothing band: "
        "0.571 in far's 0.475-0.762, 0.389 in mid's 0.311-0.734, 1.077 in close's "
        "0.464-1.998, 0.619 in anchor's 0.406-0.744. A card that works everywhere and is "
        "invisible to the metric everywhere. One staging-dependent side effect: at `far` "
        "the model also walks her most of the way to the lens while she does it - the "
        "gesture is not enough to fill four seconds of a wide shot. Use [[hand_to_face_only]] "
        "if the framing has to hold."),
    "hand_to_face_only": (
        "RE-MEASURED ACROSS FOUR STAGINGS 2026-08-04, 3 seeds each, watched at 7702. Lands "
        "at all four, 0.625 / 0.385 / 1.058 / 0.564, every one inside its own band. AND "
        "THE HOLD CLAUSE EARNS ITS KEEP AT WIDE STAGINGS: where plain [[hand_to_face]] "
        "walked her the length of the hall at `far`, this one leaves her standing and "
        "raises only the hand. That difference does not show up at `close`, where there is "
        "nowhere to walk anyway - which is why it was never visible on the single keyframe "
        "the library was measured on."),
    "head_turn": (
        "RE-MEASURED ACROSS FOUR STAGINGS 2026-08-04, 3 seeds each, watched at 7702. The "
        "head turns off-screen left at all four stagings; 0.570 / 0.709 / 0.857 / 0.592, "
        "all inside their own bands. AT THE TWO WIDE STAGINGS IT DOES NOT STOP AT THE "
        "HEAD - by f84 at `far` and f72 at `mid` the turn has carried the whole body round "
        "and she walks off. At `close` and `anchor` it stays a head turn and the shot "
        "still ends on her. A card whose SCOPE, not just its size, is set by the staging."),
    "cup_lift": (
        "RE-MEASURED ACROSS FOUR STAGINGS 2026-08-04, 3 seeds each, watched at 7702. THE "
        "PRECONDITION IS NOT `a cup in frame`, IT IS `a cup WITHIN REACH`. At `close` and "
        "`anchor`, where the cup is on the table at her hand, the four-stage action lands "
        "in full - look down, reach, lift, drink - at 1.144 and 0.809. At `far` and `mid` "
        "the cup is a table's length or a hall's length away and the card collapses into "
        "her walking out of frame entirely by f48: 0.909 and 1.178, numbers that look "
        "respectable and describe an exit, not a drink. The card's own `needs` line should "
        "be read as a reach test, not a visibility test."),
    "hand_reach": (
        "RE-MEASURED ACROSS FOUR STAGINGS 2026-08-04, 3 seeds each, watched at 7702. Lands "
        "as a reach only where the hand is already large in frame: at `close` (0.904) and "
        "`anchor` (2.231) the arm comes forward at the lens by f72. At `far` (1.618) and "
        "`mid` (1.385) `toward the camera` is obeyed by the WHOLE BODY - she walks in, and "
        "at `far` ends as a coat filling the frame. Its two highest numbers are its two "
        "failures."),
    "lean_in": (
        "RE-MEASURED ACROSS FOUR STAGINGS 2026-08-04, 3 seeds each, watched at 7702. Same "
        "split as [[hand_reach]] and for the same reason. At `close` (1.725) she genuinely "
        "leans forward over the table; at `anchor` (2.591) it reads as a lean too. At "
        "`far` (1.486) and `mid` (1.968) it is not a lean, it is an approach that does not "
        "stop - the `far` cell ends on her mouth alone, subject destroyed. Above the "
        "frame-scale ceiling at three stagings, and at two of those the shot is unusable."),
    "step_back": (
        "RE-MEASURED ACROSS FOUR STAGINGS 2026-08-04, 3 seeds each, watched at 7702. IT "
        "DOES NOT DO WHAT IT SAYS AT ANY STAGING, and that failure is the one thing in "
        "this run that IS a property of the card. She goes forward at `far`, forward and "
        "out right at `mid`, out of frame at `close`, out of frame at `anchor`. Nothing in "
        "the four cells is a step backward. Its numbers - 0.648 / 0.905 / 2.882 / 1.409 - "
        "are measuring exits. Use [[walk_out]] if an exit is what is wanted and say so."),
    "walk_away": (
        "RE-MEASURED ACROSS FOUR STAGINGS 2026-08-04, 3 seeds each, watched at 7702. "
        "UNRELIABLE IN BOTH DIRECTIONS. At `far` (0.647) she walks TOWARD the camera - the "
        "exact opposite of the ask. At `mid` (0.812) she turns her back and recedes, which "
        "is right. At `close` (2.604) she turns and exits. At `anchor` (1.000) she mostly "
        "stands. One cell in four does what the card says, and it is not the cell with the "
        "biggest number."),
    "hair_lifts": (
        "RE-MEASURED ACROSS FOUR STAGINGS 2026-08-04, 3 seeds each, watched at 7702. The "
        "hair does lift at all four - f84 at `far`, f60 at `mid`, f36 at `close`, f36 at "
        "`anchor` - but WHAT LIFTS IT CHANGES WITH THE STAGING. At the two wide stagings it "
        "is wind, subject otherwise held, which is what the card promises. At `close` and "
        "`anchor` she puts her own hands into her hair instead, which is a different beat "
        "and occupies the hands. 0.573 / 0.461 / 1.916 / 0.745."),
    "breath": (
        "RE-MEASURED ACROSS FOUR STAGINGS 2026-08-04, 3 seeds each, watched at 7702. THE "
        "BEST HOLD IN THE SUBJECT FAMILY, AND IT SHOULD BE FILED AS ONE. Lowest figure at "
        "every staging - 0.475 / 0.333 / 0.619 / 0.484, at or under each band's floor - "
        "and the strips agree: the subject stands, the framing holds, nothing wanders, at "
        "every subject scale from a distant figure to a close-up. As a MOTION card it is "
        "correctly marked weak. As the thing to put on a beat that must not move while a "
        "person is in it, nothing in `stillness` beats it."),
}

# Set by `report` after the transfer tests, and read by `cards` so the two cannot disagree.
# One of: raw | ratio | rank | none.
TRANSFER = None

# `desc` and `needs` ARE THE FIELDS A USER ACTUALLY READS when choosing a card - compose.py
# never shows them a `measured` block. Leaving a correct measurement next to a sales line
# the measurement contradicts would be the same defect in a new place, so the lines this run
# falsified are rewritten too. Only cards whose old text is now WRONG appear here.
#   card -> {"desc": ..., "needs": ...}   either key optional
# DOES THE CARD LAND WHEN YOU DO NOT KNOW THE STAGING IN ADVANCE? This is the question this
# run can actually answer, and it is not the question `status` answers - `status` was earned
# on one keyframe by a different method and is left alone rather than overwritten. Recorded
# separately so a card can say "reliable everywhere" and "weak on the metric" at once, which
# for walk_out is precisely the truth.
#   all-stagings  the ask landed at every staging watched
#   conditional   lands only where a stated precondition holds; see `needs`
#   unreliable    landed at some stagings and did the opposite at others
#   fails         did not do what it says at any staging
STAGING_ROBUSTNESS = {
    "walk_out": "all-stagings", "turn_away": "all-stagings",
    "hand_to_face": "all-stagings", "hand_to_face_only": "all-stagings",
    "head_turn": "all-stagings", "hair_lifts": "all-stagings",
    "breath": "all-stagings",
    "walk_in": "conditional", "walk_in_only": "conditional", "cup_lift": "conditional",
    "hand_reach": "conditional", "lean_in": "conditional",
    "walk_away": "unreliable",
    "step_back": "fails",
}

RETEXT = {
    "walk_in": {
        # Was: "The single most reliable motion in the library and the largest displacement
        # one mover can make." Measured across four stagings, it is neither: it is the most
        # STAGING-DEPENDENT card in the family, and walk_out is the reliable one.
        "desc": "Closing the distance. Confrontation, arrival, a decision already taken. "
                "The largest displacement one mover can make WHEN THERE IS DISTANCE TO "
                "CLOSE - on a wide it crosses the room, and on a close shot it does "
                "nothing at all while its number goes up. Stage it wide.",
        "needs": "a person in frame with open ground between them and the lens",
    },
    "walk_in_only": {
        "desc": "walk_in with the rest of the frame held. Same precondition and same "
                "failure: it needs distance to close, and returns its biggest numbers on "
                "the stagings where it does not move her at all.",
        "needs": "a person in frame with open ground between them and the lens",
    },
    "walk_out": {
        "desc": "Departure, and the one subject card that survives any staging - the "
                "subject is gone from frame by f72-f96 whether they start as a distant "
                "figure or fill the lens, because leaving the frame is a path that exists "
                "at every shot size. Reach for it when the staging is not known in advance.",
    },
    "cup_lift": {
        # The run's sharpest precondition finding: in frame is not the test, in reach is.
        "desc": "Business - the small practical action that makes a held shot feel "
                "inhabited rather than paused. Needs the cup WITHIN REACH, not merely in "
                "shot: staged across a room it becomes the subject walking out of frame.",
        "needs": "a person with a cup on a surface WITHIN ARM'S REACH of them",
    },
    "hand_reach": {
        "desc": "An arm offered to the lens. Only reads as a reach when the hand is "
                "already large in frame; staged wide, `toward the camera` is obeyed by the "
                "whole body and the card becomes a walk-in.",
        "needs": "a person staged close enough that a hand is a visible part of the frame",
    },
    "lean_in": {
        "desc": "Pressure, intimacy, a confidence. Reads as a lean only on a close shot; "
                "staged wide it becomes an approach that does not stop, and can end the "
                "shot on a fragment of a face.",
        "needs": "a person staged close, with the shot already on them",
    },
    "step_back": {
        "desc": "ASKS FOR A STEP BACKWARD AND DOES NOT PRODUCE ONE. Measured against four "
                "stagings it rendered as walking forward, walking out to the side, or "
                "leaving frame - never as retreat. Use walk_out for an exit and say exit.",
    },
    "walk_away": {
        "desc": "Departure into depth. UNRELIABLE - across four stagings only one gave the "
                "receding walk the card names; another walked the subject toward the lens "
                "instead. Prefer walk_out when the beat needs the subject gone.",
    },
    "breath": {
        "desc": "The smallest sign of life. Measured lowest of every subject card at every "
                "staging, with the framing intact each time - which makes it the best HOLD "
                "in the library for a beat that has a person in it, rather than a motion.",
    },
    "hair_lifts": {
        "desc": "Wind in the hair, subject otherwise held - on a wide. On a close shot the "
                "model lands it by putting her own hands in her hair instead, which is a "
                "different beat and occupies the hands.",
    },
    "head_turn": {
        "desc": "Directs the audience at something outside the frame; sets up the next "
                "cut. On a close shot it stays a head turn; staged wide it keeps going and "
                "carries the whole body round into a walk-off.",
    },
    "hand_to_face": {
        "desc": "The classic reaction gesture - grief, exhaustion, realisation. Lands at "
                "every staging measured. On a wide the model also walks the subject toward "
                "the lens while she does it; use hand_to_face_only to hold the framing.",
    },
    "hand_to_face_only": {
        "desc": "hand_to_face with the frame held, and the hold clause earns its keep on "
                "wides specifically: it is what stops the gesture turning into a walk-in "
                "when the subject is small and there is time to fill.",
    },
}


def stage_cards(dry=True):
    """Rewrite the subject cards' measured blocks from this run.

    WHAT THIS DOES TO A CARD depends on what `report` found, which is the whole point of
    the exercise, so it is not decided here in advance:

      transfer == raw    the single band stands. Add the per-staging table as corroboration
                         and leave band_lo/band_hi/frame_scale_ceiling where they are.
      otherwise          band_lo, band_hi and frame_scale_ceiling STOP BEING QUOTED as
                         properties of the card. They move into measured.per_staging, one
                         set per staging, each with the keyframe it came from and the
                         subject scale that keyframe was staged at. The card gains
                         `number_is_staging_dependent: true` so any tool that reads these
                         files can tell that a single figure is not available.

    In both cases motion_per_seed keeps the ANCHOR figures - the same keyframe, the same
    seeds, the same clips the card was written from - so nothing already published silently
    changes value. What changes is what those figures are CLAIMED to mean."""
    res = jload(f"{OUT}/results.json")
    bnd, agg = bands(res), by_card(res)
    stg = jload(f"{OUT}/staging.json") if os.path.exists(f"{OUT}/staging.json") else {}
    summ = jload(f"{OUT}/summary.json") if os.path.exists(f"{OUT}/summary.json") else {}
    transfer = TRANSFER or summ.get("transfer")
    if not transfer:
        raise SystemExit("run `report` first - the verdict decides what gets written")
    sids = [s for s in STAGING_IDS + ["anchor"] if s in bnd]
    n = 0
    for cid, _text, _want in subject_cards():
        p = f"{MOTIONDIR}/{cid}.json"
        c = jload(p)
        a = agg.get(cid)
        if not a:
            print(f"  skip {cid}: not measured")
            continue
        m = dict(c.get("measured") or {})
        per = {}
        for sid in sids:
            if sid not in a:
                continue
            b = bnd[sid]
            mean = a[sid]["mean"]
            per[sid] = {
                "motion_per_seed": a[sid]["motions"],
                "motion_mean": mean,
                "creep_mean": a[sid]["creep"],
                "band_lo": b["lo"],
                "band_hi": b["hi"],
                "frame_scale_ceiling": b["ceiling"],
                "vs_band": ("below" if mean < b["lo"] else "in-band" if mean <= b["hi"]
                            else "between" if mean <= b["ceiling"] else "frame-scale"),
                "x_control": round(mean / b["mean"], 3),
                "keyframe": (f"studio/samples/motion_staging/keyframes/{sid}.png"
                             if sid != "anchor" else
                             "studio/samples/motion_lib/_keyframe.png"),
                "subject_scale": (stg.get(sid) or {}).get("coat_area_frac"),
            }
        m["per_staging"] = per
        m["seeds"] = SEEDS
        m["frames"] = FRAMES
        m["workflow"] = "12_ltx23_i2v_audio.json"
        m["staging_note"] = (
            "subject_scale is the fraction of the frame the subject's coat occupies in that "
            "staging's keyframe - the run's measure of how close the subject is staged.")
        if transfer != "raw":
            # The single-keyframe figures are KEPT but relabelled, so no number silently
            # changes meaning and nothing that reads this file loses data.
            #
            # THE RENAME MUST BE IDEMPOTENT. A first draft wrote
            #   m["band_lo_anchor_only"] = m.pop("band_lo", None)
            # which is correct exactly once: on a second `cards --write` the source key is
            # already gone, pop returns None, and the preserved figure is overwritten with
            # null. Re-running a writer is normal - after a lib-verdict pass it is the
            # documented recovery - so the second run has to be a no-op, not a data loss.
            for src, dst in (("motion_mean", "motion_mean_anchor_only"),
                             ("band_lo", "band_lo_anchor_only"),
                             ("band_hi", "band_hi_anchor_only"),
                             ("frame_scale_ceiling", "frame_scale_ceiling_anchor_only")):
                if src in m:
                    m[dst] = m.pop(src)
                elif dst not in m:
                    raise SystemExit(
                        f"{cid}: neither {src} nor {dst} present - this card did not come "
                        f"from the library pass and cannot be relabelled blindly")
            c["number_is_staging_dependent"] = True
        c["measured"] = m
        if cid in WATCHED:
            c["verdict"] = WATCHED[cid]
        for k, v in (RETEXT.get(cid) or {}).items():
            c[k] = v
        if cid in STAGING_ROBUSTNESS:
            c["staging_robustness"] = STAGING_ROBUSTNESS[cid]
            c["staging_robustness_evidence"] = (
                f"four stagings (subject 0.19%-7.92% of frame), three seeds of numbers, "
                f"strips watched at seed 7702: samples/motion_staging/percard/{cid}.png")
        if dry:
            shown = "  ".join("%s %.3f %s" % (k, v["motion_mean"], v["vs_band"])
                              for k, v in per.items())
            print(f"  [dry] {cid:20s} {shown}")
        else:
            json.dump(c, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
            print(f"  wrote {p}")
        n += 1
    print(f"{'would rewrite' if dry else 'rewrote'} {n} cards  (transfer verdict: {transfer})")


# ═══════════════════════════════════════════════════════════════════ main
def main():
    global ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument("stages", nargs="+")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default=None)
    ap.add_argument("--staging", default=None)
    ap.add_argument("--write", action="store_true",
                    help="cards: actually rewrite studio/motions/*.json (default is a dry run)")
    ARGS = ap.parse_args()
    for s in ARGS.stages:
        print(f"\n=== {s} ===")
        if s == "keyframes":
            stage_keyframes(ARGS.force)
        elif s == "sheet":
            stage_sheet()
        elif s == "stage":
            stage_stage(ARGS.force)
        elif s == "staging":
            stage_staging()
        elif s == "clips":
            stage_clips(ARGS.force, ARGS.only, ARGS.staging)
        elif s == "measure":
            stage_measure()
        elif s == "strips":
            stage_strips(ARGS.only)
        elif s == "grids":
            stage_grids()
        elif s == "report":
            stage_report()
        elif s == "cards":
            stage_cards(dry=not ARGS.write)
        else:
            raise SystemExit(f"unknown stage {s}")


if __name__ == "__main__":
    main()
