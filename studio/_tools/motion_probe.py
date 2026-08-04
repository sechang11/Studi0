#!/usr/bin/env python3
"""
motion_probe.py - find out what MOTION LANGUAGE actually moves an LTX-2.3 clip.

WHY THIS EXISTS
---------------
`motion` is the only string short.py hands the video model (short.py:411), and compile.py:603
assigns EVERY BEAT OF EVERY FILM the same constant, "Slow deliberate movement only." A
previous wave measured that constant, and four adjective-style variants, sitting in the
do-nothing band - indistinguishable from an empty prompt. So the one variable that decides
whether a film moves has never been authored, has no card library, and is not in
effects.json's registry. Before a card schema can be written, somebody has to know what
grammar the model obeys. That is this tool.

THE HYPOTHESIS UNDER TEST
-------------------------
THE MODEL RENDERS NOUNS, NOT ADJECTIVES. Qualities do nothing; things land. Predicted:
motion phrased as a manner ("slowly", "dramatically") does nothing, and motion phrased as a
NAMED MOVER performing an ACTION ("she raises her right hand", "the curtain lifts") moves.

METHOD - the discipline this project has broken before
------------------------------------------------------
ONE keyframe, ONE seed per pass, ONE clip length, ONE resolution, ONE workflow. The keyframe
is rendered ONCE and copied ONCE into ComfyUI/input; every cell loads that literal file, so
frame 0 is identical by construction and any difference between two cells is the text and
nothing else. Render config is short.py's shipping config verbatim - workflow 12, 1280x704,
97 frames, img_compression 18, the file's own negative left untouched - because the answer
has to apply to what the app actually renders, not to a nicer configuration.

THE KEYFRAME IS BUILT FOR THE QUESTION. It deliberately contains every noun the class-D and
class-E prompts name: a woman (hand, head, hair), a curtain, a rain-streaked window, a
steaming cup, a stone pillar, an iron fence. That makes "name a mover that is in the frame"
a fair test. Confetti is the one named mover deliberately ABSENT, to separate "animate a
thing that is there" from "introduce a thing that is not".

THE NUMBERS
-----------
  motion / churn   scripts/analyze_shots.py's own motion(), imported, NOT reimplemented.
                   That module carries the fix for the YDIF scientific-notation regex bug
                   (8.87784e-05 parsed as 8.87784, a ~1300x overstatement). Any motion
                   figure in this repo not produced by that function is suspect.
  frozen           analyze_shots.frozen_seconds().
  thirds/halves    SUPPLEMENTARY. Same YDIF statistic restricted to left/centre/right and
                   top/bottom, to say WHERE the movement was. This is how "she raised her
                   hand" (centre only) is told apart from "the camera tracked" (everywhere).
                   A third is cropped BEFORE the 320px normalise, so a third's number is
                   larger than the global one and is comparable only to other thirds.
  dx/dy            SUPPLEMENTARY. FFT phase correlation, first frame vs last, on the left
                   and right halves separately, run under the ComfyUI venv because system
                   python has no numpy. Signs agreeing = the whole frame slid (a camera
                   move); signs opposing = the frame diverged (a push in).
                   SIGN CONVENTION, verified against a synthetically shifted frame by
                   `selftest` and not assumed:
                       dx > 0  content moved LEFT   -> camera moved RIGHT
                       dy > 0  content moved UP     -> camera tilted DOWN
                   pk is the correlation peak. A LOW pk means the two frames no longer look
                   like a shifted copy of each other, so dx/dy is unreliable - which is
                   itself a signal that a lot of content changed. Never read dx without pk.

AND THEN YOU LOOK. Every cell gets a labelled 8-frame strip. Last wave a stability metric
ranked an anime control best while the subject's hair had covered her face and her eyes were
shut. THE NUMBER DISAGREED WITH THE EYE AND THE EYE WAS RIGHT. The numbers here rank
candidates for inspection; they do not decide anything.

FINDINGS - 27 cells x 3 seeds = 81 clips, rendered 2026-08-04, all 81 watched
-----------------------------------------------------------------------------
1. THE MOTION METRIC IS BLIND TO SUBJECT-SCALE ACTION, AND THAT IS THE HEADLINE.
   "She raises her right hand to her face" and its two variants produced the requested
   action in 9 clips out of 9, across three seeds and three grammatical forms - and all
   nine measured 0.437-0.863, AT OR BELOW the empty control (mean 0.614, max 0.990). A
   hand and forearm are a fraction of a percent of 1280x704; a mean over all pixels cannot
   see them. Ranking motion cards by this number would have thrown away every performance
   beat in the library. Use it to detect frame-scale events ONLY, and look at
   samples/motion_probe/detail/ for anything a person does.

2. NOUNS ARE NECESSARY BUT NOT SUFFICIENT. The refinement on top of the governing rule is
   that the mover must be capable of GROSS DISPLACEMENT, and it helps enormously to give
   the action a PATH.
     works   she walks forward toward the camera / confetti falls through the frame /
             the camera pushes in past the pillar / steam drifts left across the lens /
             she raises her right hand to her face
     fails   the curtain lifts (0/3) / the lamp flickers / rain runs down the window
   A mover that changes STATE IN PLACE (flicker, switch on) does nothing - which is the
   same result the previous wave got for `lights_switch`, and it scored BELOW its own
   empty control there too. Texture-scale motion (rain on glass) also does nothing.

3. A BARE INTRANSITIVE FAILS; ADD A SPATIAL ANCHOR AND IT FIRES. "The curtain lifts." did
   nothing on all three seeds. "The curtain lifts BEHIND HER." swept the curtain right
   across the frame and closed it over the window. Same mover, same verb. The prepositional
   phrase is doing the work. Same story for the camera: this sweep's "pushes in past the
   pillar" is a real 1.40x dolly-in on 3/3 seeds, while the previous wave's "pushes slowly
   forward down the street" sat at the floor. Adverb out, noun-with-relation in.

4. ADJECTIVES DO NOTHING, CONFIRMED, BUT THEY ARE NOT INERT. All five adjective cells sat
   at 0.59-1.12 with no named action visible on any seed. What they DO produce is
   undirected drift - the subject wandering toward camera or turning. The same is true of
   a bare scene description with no verb, which turned the subject away from camera. Text
   in the motion field that does not name an action still perturbs the shot.

5. THE PRODUCTION CONSTANT IS WORSE THAN AN EMPTY STRING. "Slow deliberate movement only."
   measured 0.520 against the empty control's 0.614 - it is one of the three STILLEST
   cells in the whole sweep. Every film this project has shipped has been asking the video
   model to hold still.

6. STILLNESS IS ACHIEVABLE, AND IT IS A REAL CAPABILITY. The three class-F holds are the
   quietest cells measured (0.515-0.592) and hold face, gaze and framing for the full 97
   frames. A director can ask for a held shot and get one. Note this fights workflow 12's
   own negative, which contains "static, frozen" and which short.py never overrides.

7. TWO MOVERS IN ONE STRING IS DANGEROUS. "She raises her right hand to her face. The
   curtain lifts behind her." landed both - and the curtain's traversal destroyed the
   composition, covering the window, the fence and the pillar. One mover per card.

8. HIGH MOTION AND A USABLE SHOT ARE DIFFERENT AXES. Ranked by "on brief AND the subject
   survives, across 3 seeds":
     she walks forward toward the camera   3/3 on brief, 3/3 subject intact   BEST
     hand-to-face (all three phrasings)    9/9 on brief, 9/9 subject intact
     confetti falls through the frame      3/3 on brief, 2/3 subject intact (1 buried)
     the camera pushes in past the pillar  3/3 moves,    2/3 subject intact (1 pushed past)
     steam drifts left across the lens     3/3 fires, shape wildly uncontrolled
     she turns her head to look off left   3/3 turns,    0/3 keeps the face - ALWAYS
                                           overshoots into a full body turn away
     the camera tracks right along the fence  moves 5.9-7.4 but it is a PUSH, not a track
   The two highest-scoring cells in the sweep are also the two most likely to eat the shot.

USAGE
    python3 studio/_tools/motion_probe.py keyframe        # render the one shared keyframe
    python3 studio/_tools/motion_probe.py render          # seed pass 1 (all cells)
    python3 studio/_tools/motion_probe.py render --seeds 8801,8802   # replication passes
    python3 studio/_tools/motion_probe.py measure
    python3 studio/_tools/motion_probe.py strips
    python3 studio/_tools/motion_probe.py report

Every stage is idempotent and skips finished work; render --force re-renders.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

# analyze_shots.py does os.environ.setdefault("COMFY_ROOT", "Z:/ComfyUI") - a Windows SMB
# path - and epic.py reads COMFY_ROOT at import. Set it FIRST or every path resolves to a
# share that is not mounted here.
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # .../studio
REPO = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(REPO, "scripts"))

from analyze_shots import motion as ydif_motion, frozen_seconds          # noqa: E402
from comfy import api, set_path as sp                                    # noqa: E402

COMFY = os.environ["COMFY_ROOT"]
HOST = os.environ.get("COMFY_HOST", "127.0.0.1:8188")
REL = "claude-generated/motion-probe"
LAB = f"{COMFY}/output/{REL}"
OUT = f"{ROOT}/samples/motion_probe"
VENV = os.path.expanduser("~/ComfyUI/venv/bin/python3")
FONT = "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf"

# short.py's shipping config, verbatim. VID = (1280, 704) at short.py:66; 97 frames is 8n+1,
# 4.04s at 24fps, the default 4s beat.
W, H = 1280, 704
FPS = 24
FRAMES = 97
KF_SEED = 4200
SEEDS = [4200]          # pass 1. Replication passes are --seeds.

# The staged input filename. ONE file, copied ONCE, loaded by every cell.
STAGED = "mprobe_kf.png"

# ── the one keyframe ──────────────────────────────────────────────────────────
# Authored to contain every noun the sweep names, so class D tests "animate a thing that is
# present" rather than "invent a thing from nothing" - except confetti, which is absent on
# purpose and is the control for exactly that difference.
KF = ("A young woman in a dark green wool coat stands beside a tall arched window inside an "
      "empty railway station cafe at night. Heavy rain streaks down the glass behind her. A "
      "thick stone pillar rises out of frame on the left. On the right a long red velvet "
      "curtain hangs from the ceiling to the floor. In front of her a small round marble "
      "table holds a white cup of coffee with steam rising from it. Through the window an "
      "iron railing fence runs away into the dark. She stands facing the camera with her "
      "arms down at her sides. Warm lamplight, deep perspective, sharp, detailed, "
      "cinematic, high contrast.")

# ── the sweep ─────────────────────────────────────────────────────────────────
# (id, class, text, what was asked for - the thing to check the strip against)
CELLS = [
    # A - EMPTY. The true control. Two flavours: no text at all, and text that describes the
    # frame without asking for anything to happen. The second separates "the encoder got
    # nothing" from "the encoder got a scene with no verb".
    ("a_empty", "A", "",
     "nothing asked - this is the do-nothing floor"),
    ("a_scene_noverb", "A",
     "A woman beside a window in an empty station cafe at night.",
     "a scene, no verb - text present, no motion requested"),

    # B - the production constant. compile.py:603, every beat of every film.
    ("b_production", "B", "Slow deliberate movement only.",
     "the current baseline - a manner with no mover"),

    # C - ADVERB / QUALITY. The rule predicts these do nothing.
    ("c_moves_slowly", "C", "moves slowly",
     "a manner, no mover"),
    ("c_gentle_drift", "C", "gentle drifting motion",
     "a manner, no mover"),
    ("c_dramatic", "C", "dramatic movement",
     "a manner, no mover"),
    ("c_energetic", "C", "Highly dynamic, energetic, full of movement.",
     "manner stacked hard - the strongest adjective ask in the sweep"),
    ("c_natural", "C", "Subtle natural motion throughout the frame.",
     "a manner with a location but still no mover"),

    # D - NAMED MOVER + ACTION. What the rule predicts will work.
    ("d_hand", "D", "She raises her right hand to her face.",
     "the woman's right hand rises to her face"),
    ("d_head", "D", "She turns her head to look off-screen left.",
     "the woman's head turns left (task's example, pronoun matched to the keyframe)"),
    ("d_curtain", "D", "The curtain lifts.",
     "the red curtain on the right rises"),
    ("d_rain", "D", "Rain runs down the window.",
     "water tracks down the glass behind her"),
    ("d_steam", "D", "Steam drifts left across the lens.",
     "steam from the cup crosses frame leftward"),
    ("d_hair", "D", "Her hair lifts and falls back against her shoulder.",
     "hair moves, subject otherwise held"),
    ("d_confetti", "D", "Confetti falls through the frame.",
     "A MOVER THAT IS NOT IN THE KEYFRAME - can the text introduce one?"),
    ("d_two", "D", "She raises her right hand to her face. The curtain lifts behind her.",
     "TWO movers in one string - do both land, or does one win?"),
    # The prior wave's `lights_switch` ("the streetlights switch on one after another")
    # scored BELOW its own empty control despite naming a mover. That suggests the rule is
    # sharper than noun-vs-adjective: a mover that CHANGES STATE IN PLACE may not count,
    # only a mover that TRAVELS. These two cells are the ends of that axis.
    ("d_flicker", "D", "The lamp flickers.",
     "mover present, but a state change IN PLACE - not travel"),
    ("d_walks", "D", "She walks forward toward the camera.",
     "whole-body TRAVEL - the largest displacement any single mover can make"),
    # Two grammar questions the card schema has to answer directly.
    ("d_imperative", "D", "Raise the right hand to the face.",
     "the same action as d_hand in the IMPERATIVE - does mood matter?"),
    ("d_named", "D",
     "The woman in the dark green coat raises her right hand to her face.",
     "the same action as d_hand with the mover NAMED IN FULL - does describing the "
     "mover help or dilute?"),

    # E - CAMERA-AS-MOTION. Does camera language belong in the motion string at all, or is
    # that the camera layer's job? effects.json puts camera in tier `post` (an ffmpeg crop),
    # so if the model obeys camera language here, the two layers can fight.
    ("e_push", "E", "The camera pushes in past the pillar.",
     "framing tightens, the pillar passes out of frame"),
    ("e_track", "E", "The camera tracks right along the fence.",
     "whole frame slides left as the camera moves right"),
    ("e_locked", "E", "The camera is locked off on a tripod and does not move.",
     "camera held - the negative form of a camera instruction"),

    # F - NEGATIVE / HOLDING. A director has to be able to ask for stillness too.
    ("f_nobody", "F", "Nobody moves.",
     "no movement anywhere"),
    ("f_figure_still", "F", "The figure stays completely still.",
     "the woman held, the rest free"),
    ("f_hold_all", "F", "She holds absolutely still. Nothing in the frame moves.",
     "everything held"),

    # G - MOVER + HOLD. What a director actually writes: one thing moves, nothing else does.
    # This is the cell the card schema most needs an answer about.
    ("g_hand_only", "G",
     "She raises her right hand to her face. Nothing else in the frame moves.",
     "the hand rises AND the rest stays put"),
]


# ═══════════════════════════════════════════════════════════════════ helpers
def sh(*a, **kw):
    r = subprocess.run([str(x) for x in a], capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.stderr.write(f"FAIL {' '.join(str(x) for x in a)[:300]}\n{r.stderr[-1500:]}\n")
    return r


def need(*dirs):
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def load_wf(name):
    """Strip _comment/_notes keys. ComfyUI returns a bare 500 with no node_errors if a
    top-level string survives into /prompt - see scripts/comfy.py's note."""
    with open(f"{REPO}/workflows/{name}", encoding="utf-8") as f:
        return {k: v for k, v in json.load(f).items() if not k.startswith("_")}


def submit(wf):
    return api(HOST, "/prompt", {"prompt": wf, "client_id": str(uuid.uuid4())})["prompt_id"]


def wait_all(pids, label="jobs", timeout=10800):
    """Poll. NEVER block on a single job: a CAST workflow shares this GPU, and the LTXAV
    checkpoint stages 23.8GB on a 32GB card, so an interleaved job means a full evict and
    reload. Submitting the whole batch contiguously keeps it resident."""
    if not pids:
        return {}
    left, done, t0 = set(pids), {}, time.time()
    while left:
        time.sleep(6)
        try:
            h = api(HOST, "/history?max_items=800")
        except SystemExit:
            continue
        fresh = {p for p in left if p in h}
        for p in fresh:
            done[p] = h[p]
        if fresh:
            left -= fresh
            print(f"  {label}: {len(pids)-len(left)}/{len(pids)} ({time.time()-t0:.0f}s)",
                  flush=True)
        if time.time() - t0 > timeout:
            print(f"  {label}: TIMEOUT, {len(left)} outstanding", flush=True)
            return done
    return done


def job_secs(rec):
    start = end = None
    for m in rec.get("status", {}).get("messages", []):
        if not isinstance(m, list) or len(m) < 2:
            continue
        ts = m[1].get("timestamp")
        if ts is None:
            continue
        if m[0] == "execution_start":
            start = ts
        elif m[0] in ("execution_success", "execution_error"):
            end = ts
    return round((end - start) / 1000.0, 2) if (start and end) else None


def job_file(rec):
    for _nid, o in rec.get("outputs", {}).items():
        for key in ("videos", "gifs", "images"):
            for it in o.get(key, []) or []:
                return f"{COMFY}/output/{it.get('subfolder','')}/{it['filename']}".replace(
                    "//", "/")
    return None


def job_error(rec):
    for m in rec.get("status", {}).get("messages", []):
        if isinstance(m, list) and m and m[0] == "execution_error":
            d = m[1]
            return f"{d.get('node_type')}#{d.get('node_id')}: {str(d.get('exception_message'))[:250]}"
    return None


def nframes(path):
    r = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
           "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", path)
    try:
        return int(r.stdout.strip().split(",")[0])
    except Exception:
        return 0


# ═══════════════════════════════════════════════════════════════════ GPU stages
def stage_keyframe(force=False):
    need(LAB, OUT)
    dst = f"{LAB}/kf_00001_.png"
    if os.path.exists(dst) and not force:
        print(f"  = keyframe exists {dst}")
    else:
        wf = load_wf("13_qwen_t2i_styled.json")
        sp(wf, "10.inputs.text", KF)
        sp(wf, "12.inputs.width", W)
        sp(wf, "12.inputs.height", H)
        sp(wf, "13.inputs.seed", KF_SEED)
        sp(wf, "15.inputs.filename_prefix", f"{REL}/kf")
        print("  > keyframe")
        wait_all([submit(wf)], "keyframe")
    if not os.path.exists(dst):
        raise SystemExit(f"keyframe did not render: {dst}")
    # ONE copy into ComfyUI/input. Every cell in every pass loads this exact file.
    shutil.copy(dst, f"{COMFY}/input/{STAGED}")
    shutil.copy(dst, f"{OUT}/_keyframe.png")
    print(f"  staged {COMFY}/input/{STAGED}")


def stage_render(seeds, force=False, only=None):
    """Submit the whole matrix contiguously, then poll."""
    need(LAB, OUT)
    if not os.path.exists(f"{COMFY}/input/{STAGED}"):
        raise SystemExit("run `keyframe` first - nothing staged")
    rows = [c for c in CELLS if (not only or only in c[0])]
    jobs, meta = [], {}
    for seed in seeds:
        for cid, klass, text, want in rows:
            tag = f"{cid}_s{seed}"
            if os.path.exists(f"{LAB}/{tag}_00001_.mp4") and not force:
                print(f"  = {tag} exists")
                continue
            wf = load_wf("12_ltx23_i2v_audio.json")
            sp(wf, "8.inputs.image", STAGED)
            sp(wf, "10.inputs.text", text)
            sp(wf, "20.inputs.width", W)
            sp(wf, "20.inputs.height", H)
            sp(wf, "20.inputs.length", FRAMES)
            sp(wf, "21.inputs.frames_number", FRAMES)
            sp(wf, "32.inputs.noise_seed", seed)
            sp(wf, "43.inputs.filename_prefix", f"{REL}/{tag}")
            # node 9 img_compression and node 11 negative are LEFT AS THE FILE HAS THEM.
            # short.py sets neither; changing them here would measure a different app.
            pid = submit(wf)
            jobs.append(pid)
            meta[pid] = dict(id=tag, cell=cid, klass=klass, seed=seed, text=text, want=want)
            print(f"  > {tag}  -> {pid}")
    recs = wait_all(jobs, "clips")
    man = f"{OUT}/manifest.json"
    prev = json.load(open(man)) if os.path.exists(man) else []
    have = {r["id"] for r in prev}
    for pid in jobs:
        m = dict(meta[pid])
        rec = recs.get(pid, {})
        m["secs"] = job_secs(rec)
        m["error"] = job_error(rec)
        m["file"] = job_file(rec) or (f"{LAB}/{m['id']}_00001_.mp4"
                                      if os.path.exists(f"{LAB}/{m['id']}_00001_.mp4")
                                      else None)
        if m["id"] in have:
            prev = [r for r in prev if r["id"] != m["id"]]
        prev.append(m)
        print(f"{m['id']:26s} {str(m['secs']):>7s}s  {m['error'] or os.path.basename(m['file'] or 'NO OUTPUT')}")
    # rows that already existed and were skipped this run still need manifest entries
    for seed in seeds:
        for cid, klass, text, want in rows:
            tag = f"{cid}_s{seed}"
            f = f"{LAB}/{tag}_00001_.mp4"
            if os.path.exists(f) and not any(r["id"] == tag for r in prev):
                prev.append(dict(id=tag, cell=cid, klass=klass, seed=seed, text=text,
                                 want=want, secs=None, error=None, file=f))
    json.dump(prev, open(man, "w"), indent=1)
    print(f"wrote {man} ({len(prev)} rows)")


# ═══════════════════════════════════════════════════════════════════ measuring
YDIF_RE = r"YDIF=([-+0-9.eE]+)"     # NOT [\d.]+ - the bug analyze_shots.py documents


def _region_ydif(path, crop):
    """SUPPLEMENTARY. Same YDIF statistic as the headline metric, restricted to a crop, to
    say WHERE the frame moved. The headline number itself is analyze_shots.motion()."""
    import re
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", path, "-vf",
         f"crop={crop},scale=320:-2,signalstats,"
         "metadata=print:key=lavfi.signalstats.YDIF", "-f", "null", "-"],
        capture_output=True, text=True)
    v = [float(x) for x in re.findall(YDIF_RE, r.stderr or "")]
    return round(sum(v) / len(v), 4) if v else 0.0


REGIONS = {
    "left":   f"{W//3}:{H}:0:0",
    "centre": f"{W//3}:{H}:{W//3}:0",
    "right":  f"{W//3}:{H}:{2*(W//3)}:0",
    "top":    f"{W}:{H//2}:0:0",
    "bottom": f"{W}:{H//2}:0:{H//2}",
}

DISP_SRC = r'''
import sys, numpy as np
from PIL import Image
def g(p):
    return np.asarray(Image.open(p).convert("L"), dtype=np.float64)
def shift(a, b):
    # FFT phase correlation. Returns (dx, dy) of b relative to a, in pixels.
    A, B = np.fft.fft2(a), np.fft.fft2(b)
    R = A * np.conj(B)
    R /= np.maximum(np.abs(R), 1e-9)
    c = np.fft.ifft2(R).real
    iy, ix = np.unravel_index(np.argmax(c), c.shape)
    h, w = a.shape
    dx = ix - w if ix > w // 2 else ix
    dy = iy - h if iy > h // 2 else iy
    return float(dx), float(dy), float(c.max())
a, b = g(sys.argv[1]), g(sys.argv[2])
h, w = a.shape
out = {}
for name, sl in (("L", slice(0, w // 2)), ("R", slice(w // 2, w))):
    dx, dy, pk = shift(a[:, sl], b[:, sl])
    out[f"dx_{name}"], out[f"dy_{name}"], out[f"pk_{name}"] = dx, dy, round(pk, 4)
print(__import__("json").dumps(out))
'''


def _frame_png(clip, idx, dest):
    sh("ffmpeg", "-y", "-hide_banner", "-v", "error", "-i", clip,
       "-vf", f"select=eq(n\\,{idx})", "-vsync", "0", "-frames:v", "1",
       "-pix_fmt", "rgb24", dest)
    return dest


def displacement(clip, tmp):
    """SUPPLEMENTARY. First frame vs last, left half and right half separately.
    signs agree -> the whole frame slid (camera pan/track)
    signs oppose -> the frame diverged/converged (push in / pull out)
    both ~0      -> the framing never moved, whatever else did."""
    n = nframes(clip)
    if n < 2:
        return {}
    a = _frame_png(clip, 0, f"{tmp}/d0.png")
    b = _frame_png(clip, n - 1, f"{tmp}/d1.png")
    src = f"{tmp}/_disp.py"
    open(src, "w").write(DISP_SRC)
    r = subprocess.run([VENV, src, a, b], capture_output=True, text=True)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {}


def selftest():
    """A reversed sign turns this report into confident nonsense, so the convention is
    checked against a frame shifted by a known amount rather than assumed."""
    tmp = "/tmp/mprobe_selftest"
    need(tmp)
    src = f"{OUT}/_keyframe.png"
    if not os.path.exists(src):
        src = f"{ROOT}/samples/motion/_kf_a.jpg"
    sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vf", f"scale={W}:{H}",
       "-pix_fmt", "rgb24", f"{tmp}/a.png")
    sh("ffmpeg", "-y", "-v", "error", "-i", f"{tmp}/a.png",
       "-vf", f"crop={W-40}:{H}:40:0,pad={W}:{H}:0:0", "-pix_fmt", "rgb24", f"{tmp}/b.png")
    sh("ffmpeg", "-y", "-v", "error", "-i", f"{tmp}/a.png",
       "-vf", f"crop={W}:{H-40}:0:40,pad={W}:{H}:0:0", "-pix_fmt", "rgb24", f"{tmp}/c.png")
    open(f"{tmp}/_disp.py", "w").write(DISP_SRC)
    for tag, f, key, want in (("content LEFT 40px (camera RIGHT)", "b.png", "dx_L", 40.0),
                              ("content UP 40px (camera tilt DOWN)", "c.png", "dy_L", 40.0)):
        r = subprocess.run([VENV, f"{tmp}/_disp.py", f"{tmp}/a.png", f"{tmp}/{f}"],
                           capture_output=True, text=True)
        d = json.loads(r.stdout.strip().splitlines()[-1])
        ok = abs(d[key] - want) < 2
        print(f"  selftest {tag:36s} {key}={d[key]:+.0f} want {want:+.0f}  "
              f"{'OK' if ok else 'FAILED'}")
        if not ok:
            raise SystemExit("displacement sign convention is WRONG - do not trust dx/dy")


def framing_drift(clip, tmp):
    """How far the framing CREPT IN over the clip, with nothing asking it to.

    Every cell here drifts toward a push-in - visible on the strips, invisible to dx/dy
    because a zoom is not a translation. video_engines.zoom_est already solves exactly this
    (scale the reference by z, centre-crop, argmax SSIM against the final frame), so it is
    IMPORTED rather than rewritten. 1.00 = framing held; 1.20 = crept in 20%.

    This is the number that separates "asking for stillness works" from "nothing happened":
    a cell can be flat on the motion metric and still have wandered.
    """
    try:
        import video_engines as ve
    except Exception:
        return {}
    n = nframes(clip)
    if n < 2:
        return {}
    f0 = _frame_png(clip, 0, f"{tmp}/z0.png")
    fl = _frame_png(clip, n - 1, f"{tmp}/zl.png")
    try:
        z, zs, s1 = ve.zoom_est(f0, fl, Path(tmp), size=(W, H))
        return {"creep": z, "ssim_last_vs_f0": s1, "ssim_dezoomed": zs}
    except Exception:
        return {}


def stage_measure():
    selftest()
    man = json.load(open(f"{OUT}/manifest.json"))
    tmp = "/tmp/mprobe"
    need(tmp)
    res = []
    for m in man:
        f = m.get("file")
        if not f or not os.path.exists(f):
            print(f"skip {m['id']}: no file")
            continue
        r = dict(m)
        mo, ch = ydif_motion(f)                 # THE HEADLINE NUMBER. Shipped function.
        r["motion"] = round(mo, 4)
        r["churn"] = round(ch, 4)
        r["frozen"] = round(frozen_seconds(f), 2)
        r["frames"] = nframes(f)
        r["regions"] = {k: _region_ydif(f, c) for k, c in REGIONS.items()}
        r.update(displacement(f, tmp))
        r.update(framing_drift(f, tmp))
        res.append(r)
        print(f"{r['id']:26s} motion {r['motion']:7.3f}  churn {r['churn']:6.3f}  "
              f"creep {r.get('creep', 0):.3f}  "
              f"L/C/R {r['regions']['left']:6.2f}/{r['regions']['centre']:6.2f}/"
              f"{r['regions']['right']:6.2f}  dx {r.get('dx_L',0):5.0f},{r.get('dx_R',0):5.0f}",
              flush=True)
    json.dump(res, open(f"{OUT}/results.json", "w"), indent=1)
    print(f"wrote {OUT}/results.json ({len(res)} clips)")


# ═══════════════════════════════════════════════════════════════════ strips
def _esc(s):
    """drawtext escaping. The apostrophe is the hazard: the text sits inside a
    single-quoted filtergraph token, so a literal ' truncates it. Substituting the UTF-8
    right single quote keeps the label readable - an earlier version wrote the escape
    "\\u2019" and ffmpeg drew those six characters, so "the woman's hand" was labelled
    "the womanu2019s hand"."""
    for a, b in (("\\", "\\\\"), (":", "\\:"), ("'", "’"), ("%", "\\%"),
                 ("[", "\\["), ("]", "\\]")):
        s = s.replace(a, b)
    return s


# w:h:x:y around the subject in the 1280x704 keyframe: head, both arms, both hands, the
# steaming cup and a slice of rain-streaked glass. Small articulated motion is a fraction
# of a percent of the whole frame; if it is only ever viewed at strip scale it cannot be
# judged, and the whole-frame metric cannot see it either.
DETAIL = "440:520:400:184"


def stage_detail(cols=6, only=None):
    """Same idea as strips, cropped to the subject and scaled UP.

    A raised hand is well under 1% of a 1280x704 frame. At strip scale it is invisible, and
    the whole-frame YDIF cannot see it either - so "the metric says nothing moved" and "I
    looked and nothing moved" would both be unearned without this. Every claim in this
    report that a SMALL articulated motion failed rests on these, not on the wide strip."""
    rows = json.load(open(f"{OUT}/results.json"))
    sd = f"{OUT}/detail"
    tmp = "/tmp/mprobe_detail"
    need(sd, tmp)
    for m in rows:
        if only and only not in m["id"]:
            continue
        n = m["frames"]
        idxs = [round(i * (n - 1) / (cols - 1)) for i in range(cols)]
        parts, labels = [], []
        for i, ix in enumerate(idxs):
            p = _frame_png(m["file"], ix, f"{tmp}/{m['id']}_{i}.png")
            c = f"{tmp}/{m['id']}_{i}c.png"
            sh("ffmpeg", "-y", "-hide_banner", "-v", "error", "-i", p,
               "-vf", f"crop={DETAIL}", "-pix_fmt", "rgb24", c)
            parts.append(c)
            labels.append(f"f{ix}")
        fc = []
        for i, lab in enumerate(labels):
            fc.append(f"[{i}]scale=430:-1,pad=iw+4:ih+30:2:2:0x101010,"
                      f"drawtext=fontfile={FONT}:text='{_esc(lab)}':x=6:y=h-24:"
                      f"fontsize=18:fontcolor=0xC0C0C0[v{i}]")
        fc.append("".join(f"[v{i}]" for i in range(len(parts))) +
                  f"hstack=inputs={len(parts)}[row]")
        head = f"DETAIL  {m['id']}  [class {m['klass']}]  motion {m['motion']:.3f}"
        fc.append(f"[row]pad=iw:ih+70:0:70:0x000000,"
                  f"drawtext=fontfile={FONT}:text='{_esc(head)}':x=10:y=8:"
                  f"fontsize=28:fontcolor=white,"
                  f"drawtext=fontfile={FONT}:text='{_esc('TEXT: ' + (m['text'] or '(empty string)'))}'"
                  f":x=10:y=42:fontsize=22:fontcolor=0x7FD4FF[out]")
        args = ["ffmpeg", "-y", "-hide_banner", "-v", "error"]
        for p in parts:
            args += ["-i", p]
        args += ["-filter_complex", ";".join(fc), "-map", "[out]",
                 "-frames:v", "1", f"{sd}/{m['id']}.png"]
        sh(*args)
        print(f"detail {m['id']}")


def stage_sheet(name="sheet", cells=None, cols=4):
    """One contact sheet: several cells stacked as rows, subject-cropped, labelled.

    For checking a GROUP of cells that the numbers say are flat. Looking at them one strip
    at a time invites skimming; side by side, a cell that actually did something cannot
    hide next to five that did not."""
    rows = json.load(open(f"{OUT}/results.json"))
    if cells:
        want = [c.strip() for c in cells.split(",")]
        rows = [r for r in rows if r["cell"] in want]
        rows.sort(key=lambda r: want.index(r["cell"]))
    tmp = "/tmp/mprobe_sheet"
    need(tmp, OUT)
    band = []
    for m in rows:
        n = m["frames"]
        idxs = [round(i * (n - 1) / (cols - 1)) for i in range(cols)]
        parts = []
        for i, ix in enumerate(idxs):
            p = _frame_png(m["file"], ix, f"{tmp}/{m['id']}_{i}.png")
            c = f"{tmp}/{m['id']}_{i}c.png"
            sh("ffmpeg", "-y", "-hide_banner", "-v", "error", "-i", p,
               "-vf", f"crop={DETAIL}", "-pix_fmt", "rgb24", c)
            parts.append(c)
        fc = [f"[{i}]scale=330:-1,pad=iw+3:ih+3:1:1:0x101010[v{i}]" for i in range(len(parts))]
        fc.append("".join(f"[v{i}]" for i in range(len(parts))) +
                  f"hstack=inputs={len(parts)}[h]")
        lab = f"{m['cell']}  [{m['klass']}]  motion {m['motion']:.3f}  |  {m['text'] or '(empty)'}"
        fc.append(f"[h]pad=iw:ih+38:0:38:0x000000,"
                  f"drawtext=fontfile={FONT}:text='{_esc(lab)}':x=8:y=8:"
                  f"fontsize=24:fontcolor=0x7FD4FF[out]")
        args = ["ffmpeg", "-y", "-hide_banner", "-v", "error"]
        for p in parts:
            args += ["-i", p]
        rowpng = f"{tmp}/row_{m['id']}.png"
        args += ["-filter_complex", ";".join(fc), "-map", "[out]", "-frames:v", "1", rowpng]
        sh(*args)
        band.append(rowpng)
    args = ["ffmpeg", "-y", "-hide_banner", "-v", "error"]
    for p in band:
        args += ["-i", p]
    args += ["-filter_complex", f"vstack=inputs={len(band)}", "-frames:v", "1",
             f"{OUT}/{name}.png"]
    sh(*args)
    print(f"wrote {OUT}/{name}.png ({len(band)} rows)")


def stage_strips(cols=8):
    """keyframe | 8 frames evenly spaced across the clip, LABELLED.

    The label is the whole point. Last wave a clip was ranked best while the subject had
    turned away with her eyes shut; a strip you cannot identify at a glance does not get
    looked at properly."""
    rows = json.load(open(f"{OUT}/results.json"))
    sd = f"{OUT}/strips"
    tmp = "/tmp/mprobe_strip"
    need(sd, tmp)
    kf = f"{OUT}/_keyframe.png"
    for m in rows:
        n = m["frames"]
        idxs = [round(i * (n - 1) / (cols - 1)) for i in range(cols)]
        parts, labels = [kf], ["KEYFRAME"]
        for i, ix in enumerate(idxs):
            parts.append(_frame_png(m["file"], ix, f"{tmp}/{m['id']}_{i}.png"))
            labels.append(f"f{ix}")
        fc = []
        for i, lab in enumerate(labels):
            fc.append(f"[{i}]scale=340:-1,pad=iw+4:ih+30:2:2:0x101010,"
                      f"drawtext=fontfile={FONT}:text='{_esc(lab)}':x=6:y=h-24:"
                      f"fontsize=17:fontcolor=0xC0C0C0[v{i}]")
        fc.append("".join(f"[v{i}]" for i in range(len(parts))) +
                  f"hstack=inputs={len(parts)}[row]")
        head = (f"{m['id']}   [class {m['klass']}]   motion {m['motion']:.3f}   "
                f"churn {m['churn']:.2f}   dx {m.get('dx_L',0):.0f}/{m.get('dx_R',0):.0f}")
        body = f"TEXT: {m['text'] or '(empty string)'}"
        want = f"ASKED FOR: {m['want']}"
        fc.append(f"[row]pad=iw:ih+96:0:96:0x000000,"
                  f"drawtext=fontfile={FONT}:text='{_esc(head)}':x=10:y=10:"
                  f"fontsize=30:fontcolor=white,"
                  f"drawtext=fontfile={FONT}:text='{_esc(body)}':x=10:y=46:"
                  f"fontsize=24:fontcolor=0x7FD4FF,"
                  f"drawtext=fontfile={FONT}:text='{_esc(want)}':x=10:y=72:"
                  f"fontsize=20:fontcolor=0x9A9A9A[out]")
        args = ["ffmpeg", "-y", "-hide_banner", "-v", "error"]
        for p in parts:
            args += ["-i", p]
        args += ["-filter_complex", ";".join(fc), "-map", "[out]",
                 "-frames:v", "1", f"{sd}/{m['id']}.png"]
        sh(*args)
        print(f"strip {m['id']}")


# ═══════════════════════════════════════════════════════════════════ report
def stage_report():
    import statistics
    rows = json.load(open(f"{OUT}/results.json"))
    byc = {}
    for r in rows:
        byc.setdefault(r["cell"], []).append(r)
    order = {c[0]: i for i, c in enumerate(CELLS)}
    ctl = [r for r in rows if r["cell"] in ("a_empty", "a_scene_noverb")]
    floor = statistics.mean([r["motion"] for r in ctl]) if ctl else 0.0
    fmax = max([r["motion"] for r in ctl]) if ctl else 0.0
    print(f"\nDO-NOTHING FLOOR from the class-A controls: mean {floor:.3f}, max {fmax:.3f}")
    print("A cell at or under the control max is indistinguishable from asking for nothing.\n")
    hdr = (f"{'cell':18s} {'cl':2s} {'n':>2s} {'motion':>16s} {'churn':>7s} "
           f"{'L':>6s} {'C':>6s} {'R':>6s} {'dxL':>5s} {'dxR':>5s} {'pk':>5s} "
           f"{'x floor':>8s}")
    print(hdr)
    print("-" * len(hdr))
    out = []
    for cid, rs in sorted(byc.items(), key=lambda kv: -statistics.mean(
            [r["motion"] for r in kv[1]])):
        mos = [r["motion"] for r in rs]
        mo = statistics.mean(mos)
        span = f"{mo:.3f}[{min(mos):.2f}-{max(mos):.2f}]" if len(mos) > 1 else f"{mo:.3f}"
        g = rs[0]
        reg = {k: statistics.mean([r["regions"][k] for r in rs]) for k in REGIONS}
        line = (f"{cid:18s} {g['klass']:2s} {len(rs):>2d} {span:>16s} "
                f"{statistics.mean([r['churn'] for r in rs]):>7.2f} "
                f"{reg['left']:>6.2f} {reg['centre']:>6.2f} {reg['right']:>6.2f} "
                f"{statistics.mean([r.get('dx_L',0) for r in rs]):>5.0f} "
                f"{statistics.mean([r.get('dx_R',0) for r in rs]):>5.0f} "
                f"{statistics.mean([r.get('pk_L',0) for r in rs]):>5.2f} "
                f"{mo/max(floor,1e-6):>8.2f}")
        print(line)
        out.append(dict(cell=cid, klass=g["klass"], n=len(rs), text=g["text"],
                        want=g["want"], motion=round(mo, 4),
                        motion_min=round(min(mos), 4), motion_max=round(max(mos), 4),
                        x_floor=round(mo / max(floor, 1e-6), 2),
                        dx_L=round(statistics.mean([r.get("dx_L", 0) for r in rs]), 1),
                        dx_R=round(statistics.mean([r.get("dx_R", 0) for r in rs]), 1),
                        pk_L=round(statistics.mean([r.get("pk_L", 0) for r in rs]), 3),
                        regions={k: round(v, 3) for k, v in reg.items()},
                        rank_hint=order.get(cid, 99)))
    json.dump({"floor_mean": round(floor, 4), "floor_max": round(fmax, 4), "cells": out},
              open(f"{OUT}/summary.json", "w"), indent=1)
    print(f"\nwrote {OUT}/summary.json")
    print("\nNumbers rank candidates. Now open studio/samples/motion_probe/strips/ and LOOK.")


# ═══════════════════════════════════════════════════════════════════ cli
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["keyframe", "render", "measure", "strips", "detail",
                                      "sheet", "report", "selftest", "all"])
    ap.add_argument("--seeds", default=",".join(str(s) for s in SEEDS))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--name", default="sheet")
    a = ap.parse_args()
    seeds = [int(s) for s in a.seeds.split(",") if s.strip()]
    if a.stage == "selftest":
        selftest()
        return
    if a.stage in ("keyframe", "all"):
        stage_keyframe(a.force)
    if a.stage in ("render", "all"):
        stage_render(seeds, a.force, a.only)
    if a.stage in ("measure", "all"):
        stage_measure()
    if a.stage in ("strips", "all"):
        stage_strips()
    if a.stage in ("detail", "all"):
        stage_detail(only=a.only)
    if a.stage == "sheet":
        stage_sheet(name=a.name, cells=a.only)
    if a.stage in ("report", "all"):
        stage_report()


if __name__ == "__main__":
    main()
