#!/usr/bin/env python3
"""
motion_examples.py - give the VIDEO-ONLY libraries real rendered clips.

camera, motion and transition cannot be shown by a still. Before this tool every mp4 in
studio/samples/ was ffmpeg run over a STILL IMAGE with `-loop 1` (make_samples.py:130-191),
so nothing in the camera, transition or pacing libraries had ever been through a video
model, and `motion` - the ONE string short.py hands to the video model - had no library
at all.

Everything here comes off ONE shared keyframe at ONE seed at ONE length. That isolation is
the whole point: if the keyframe differs, a side-by-side shows the keyframe, not the move.

Stages (run in order; each is idempotent and skips finished work):

    keyframes   the two shared keyframes (A = camera/motion subject, B = transition B-side)
    base        the shared LTX i2v clip that every POST camera move is applied to
    cam-prompt  ask the video model for each camera move (11 clips, same kf, same seed)
    motion      the motion-prompt vocabulary sweep (creates studio/samples/motion/)
    post        no GPU: post camera moves, transitions and pacing over REAL clips
    measure     per-move displacement + the full pairwise MAD matrix
    strips      side-by-side frame strips so pan_l and pan_r can be told apart

    all         every stage

Displacement is measured by FFT phase correlation between the first and last frame of a
clip, run separately on the LEFT and RIGHT halves and on the TOP and BOTTOM halves. That
four-number signature separates the move families, which a single global shift cannot:

    pan     dx_L and dx_R agree in sign          (whole frame slides)
    push    dx_L negative, dx_R positive         (content diverges - zoom in)
    pull    dx_L positive, dx_R negative         (content converges - zoom out)
    tilt    dy_T and dy_B agree in sign
    none    all four ~ 0                         <- the silent failure this tool exists for

The sign convention is checked at run time against a synthetically shifted frame
(--selftest, and it runs automatically before any measurement) because a reversed sign
would turn this report into confident nonsense.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # .../studio
REPO = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(REPO, "scripts"))

COMFY = os.environ.get("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
HOST = os.environ.get("COMFY_HOST", "127.0.0.1:8188")
REL = "claude-generated/motion-lab"
LAB = f"{COMFY}/output/{REL}"

W, H = 1280, 704          # short.py VID - the size clips are actually generated at
FPS = 24
FRAMES = 97               # 8n+1, 4.04s at 24fps - short.py's default 4s beat
SECS = FRAMES / FPS
SEED = 4200               # short.py's default seed root. One seed for every clip here.

SAMP = f"{ROOT}/samples"
VENV = os.path.expanduser("~/ComfyUI/venv/bin/python3")

# ── the two shared keyframes ──────────────────────────────────────────────────
# A is built to make every move legible: a distinct landmark on each edge, so a pan or a
# tilt is readable as a THING entering or leaving frame rather than as a vague slide, plus
# deep perspective so a push has somewhere to go.
KF_A = ("A wide empty city street at dusk just after rain. On the far left edge of the "
        "frame stands a bright red telephone box. On the far right edge a yellow taxi is "
        "parked at the kerb. In the centre a tall stone clock tower rises high above the "
        "rooftops, its lit clock face near the top of the picture. In the foreground the "
        "wet black asphalt fills the bottom of the frame and reflects green and magenta "
        "neon. Deep perspective straight down the street. Sharp, detailed, cinematic, "
        "high contrast.")
KF_B = ("A sunlit desert highway at noon. A lone rusted petrol station with a faded blue "
        "sign stands on the right. Wooden telephone poles recede into the far distance. "
        "Pale sand, hard black shadows, bleached white sky. Sharp, detailed, cinematic.")

# ── prompted camera moves ─────────────────────────────────────────────────────
# Every one shares the same scene stem so the ONLY difference between the eleven clips is
# the camera clause. Without a stem the model gets an instruction with no subject and the
# null result would be about prompt shape, not about cameras.
STEM = "A quiet city street at dusk. Neon light shivers in the wet road. "
CAM_PROMPT = {
    "static": "The camera is locked off on a tripod and does not move at all.",
    "push": "The camera pushes slowly forward down the street, a slow dolly in toward the "
            "clock tower.",
    "pull": "The camera pulls slowly backward away down the street, a slow dolly out, the "
            "scene growing smaller.",
    "pan_l": "The camera pans smoothly to the left, sweeping left across the street and "
             "revealing what lies off the left side of frame.",
    "pan_r": "The camera pans smoothly to the right, sweeping right across the street and "
             "revealing what lies off the right side of frame.",
    "tilt_u": "The camera tilts upward, craning up from the road toward the top of the "
              "clock tower and the sky above it.",
    "tilt_d": "The camera tilts downward, angling down from the rooftops to the wet road "
              "at the bottom of frame.",
    "handheld": "Handheld camera, a subtle unsteady float and drift, documentary style.",
    "dolly_zoom": "A dolly zoom vertigo effect: the camera tracks backward while the lens "
                  "zooms in, so the buildings stretch and warp behind while the centre of "
                  "frame stays the same size.",
    "orbit": "The camera orbits around the scene in a smooth arc, circling it, the "
             "buildings turning to reveal their other sides.",
    "rack_focus": "A rack focus: the focus shifts from the foreground to the far "
                  "background, the foreground going soft as the distance sharpens.",
}

# ── the motion vocabulary ─────────────────────────────────────────────────────
# `motion` is the only string the video model reads (short.py:411). It has no library and
# is not in effects.json's variable registry. This is the sweep that tests the governing
# rule - the model renders nouns, not adjectives - on the video prompt.
MOTION = [
    # named physical events - NOUNS
    ("rain_begins", "noun",
     "Rain begins to fall. Drops strike the wet asphalt and ripple in the puddles."),
    ("wind_gust", "noun",
     "A gust of wind blows scraps of paper and litter across the street."),
    ("neon_flicker", "noun",
     "The neon sign flickers and buzzes, its light pulsing on the wet ground."),
    ("steam_rises", "noun",
     "Steam rises from a grate in the road and drifts upward into the cold air."),
    ("car_passes", "noun",
     "A car drives past the camera from left to right, its headlights sweeping across "
     "the wet road."),
    ("crowd_walks", "noun",
     "People walk across the street, moving past the camera in both directions."),
    ("lights_switch", "noun",
     "The streetlights switch on one after another down the length of the street."),
    # qualities - ADJECTIVES. The prediction is that these do nothing.
    ("adj_tense", "adjective", "Tense."),
    ("adj_dread", "adjective", "Unsettling and full of dread."),
    ("adj_dynamic", "adjective", "Dynamic, energetic, full of movement."),
    ("adj_cinematic", "adjective", "Cinematic, dramatic, epic."),
    # controls
    ("ctl_empty", "control", ""),
    ("ctl_compiler_default", "control", "Slow deliberate movement only."),
    ("ctl_authored_prose", "control",
     "Rain sheets down across the street. The neon sign stutters and the puddles shiver "
     "with each drop. A train rumbles past on the overpass in the distance. Nothing else "
     "moves."),
    ("ctl_camera_word", "control", "push in"),
]

BASE_MOTION = ("Rain falls steadily on the empty street. The neon light shivers in the "
               "puddles.")


# ═══════════════════════════════════════════════════════════════════ helpers
def sh(*a, **kw):
    r = subprocess.run([str(x) for x in a], capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.stderr.write(f"FAIL {' '.join(str(x) for x in a)[:400]}\n{r.stderr[-2000:]}\n")
    return r


def card(group, cid):
    with open(f"{ROOT}/{group}/{cid}.json", encoding="utf-8") as f:
        return json.load(f)


def cards(group):
    d = f"{ROOT}/{group}"
    return sorted(x[:-5] for x in os.listdir(d) if x.endswith(".json"))


def need(*dirs):
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def nframes(path):
    r = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
           "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", path)
    try:
        return int(r.stdout.strip().split(",")[0])
    except Exception:
        return 0


# ═══════════════════════════════════════════════════════════════════ GPU stages
PENDING = []          # prompt_ids submitted this run, drained by wait_all() at the end


def _comfy():
    from comfy import run as crun, set_path as sp          # noqa: E402
    return crun, sp


def submit(wf):
    """Queue a job WITHOUT blocking, and return its prompt_id.

    This box is shared. Submitting one job and waiting for it before submitting the next
    is the worst possible pattern here: every other agent's job lands between yours, and
    LTXAV alone stages 23.8GB on a 32GB card, so each interleave is a full model evict and
    reload. Measured during this run - serial submit while two other agents were active
    cost ~8 MINUTES per 97-frame clip against a 13.5s sampling cost. Submitting the batch
    contiguously lets the checkpoint stay resident across all of them.
    """
    import uuid
    from comfy import api                                  # noqa: E402
    r = api(HOST, "/prompt", {"prompt": wf, "client_id": str(uuid.uuid4())})
    return r["prompt_id"]


def wait_all(pids, label="jobs"):
    import time
    from comfy import api                                  # noqa: E402
    if not pids:
        return
    left = set(pids)
    t0 = time.time()
    while left:
        time.sleep(6)
        try:
            h = api(HOST, "/history?max_items=800")
        except SystemExit:
            continue
        done = {p for p in left if p in h}
        if done:
            left -= done
            print(f"  {label}: {len(pids) - len(left)}/{len(pids)} "
                  f"({time.time() - t0:.0f}s)", flush=True)
        if time.time() - t0 > 7200:
            print(f"  {label}: TIMEOUT with {len(left)} outstanding", flush=True)
            return


def load_wf(name):
    """Strip the `_comment`/`_notes` keys before submit.

    Every workflow file in this repo carries them. ComfyUI 0.28.0 does NOT reject a prompt
    whose top level holds a string value - it raises inside validate_prompt and returns a
    bare `500 Internal Server Error / Server got itself in trouble` with no node_errors and
    nothing in the API response naming the cause. The real traceback
    (execution.py:1126 node_data.get('_meta') on a str) only appears in the server's stderr
    log. Anyone hand-rolling a submit here will hit this and have nothing to go on.
    """
    with open(f"{REPO}/workflows/{name}", encoding="utf-8") as f:
        return {k: v for k, v in json.load(f).items() if not k.startswith("_")}


def stage_keyframes(force=False):
    """The two shared keyframes. Everything downstream hangs off these."""
    crun, sp = _comfy()
    need(LAB)
    for tag, prompt in (("kf_a", KF_A), ("kf_b", KF_B)):
        dst = f"{LAB}/{tag}_00001_.png"
        if os.path.exists(dst) and not force:
            print(f"  = {tag} exists")
            continue
        wf = load_wf("13_qwen_t2i_styled.json")
        sp(wf, "10.inputs.text", prompt)
        sp(wf, "12.inputs.width", W)
        sp(wf, "12.inputs.height", H)
        sp(wf, "13.inputs.seed", SEED)
        sp(wf, "15.inputs.filename_prefix", f"{REL}/{tag}")
        print(f"  > {tag}")
        crun(HOST, wf, quiet=True)


def _i2v(kf_png, prompt, prefix, seed=SEED, frames=FRAMES):
    """One LTX i2v job on the SHIPPING config: workflow 12 exactly as short.py drives it.

    Deliberately not 'improved'. The point is to measure what the app actually renders,
    including node 9's img_compression=18 and node 11's untouched default negative.
    """
    crun, sp = _comfy()
    staged = "mlab_" + os.path.basename(kf_png)
    shutil.copy(kf_png, f"{COMFY}/input/{staged}")
    wf = load_wf("12_ltx23_i2v_audio.json")
    sp(wf, "8.inputs.image", staged)
    sp(wf, "10.inputs.text", prompt)
    sp(wf, "20.inputs.width", W)
    sp(wf, "20.inputs.height", H)
    sp(wf, "20.inputs.length", frames)
    sp(wf, "21.inputs.frames_number", frames)
    sp(wf, "32.inputs.noise_seed", seed)
    sp(wf, "43.inputs.filename_prefix", prefix)
    PENDING.append(submit(wf))


def stage_base(force=False):
    """The one real clip every POST camera move gets applied to, plus the B-side clip."""
    need(LAB)
    for tag, kf, mot in (("base_a", "kf_a", BASE_MOTION),
                         ("base_b", "kf_b",
                          "Heat haze shimmers over the road. Dust drifts across the sand.")):
        if os.path.exists(f"{LAB}/{tag}_00001_.mp4") and not force:
            print(f"  = {tag} exists")
            continue
        print(f"  > {tag}")
        _i2v(f"{LAB}/{kf}_00001_.png", mot, f"{REL}/{tag}")


def stage_cam_prompt(force=False):
    """Ask the video model for each camera move. Same keyframe, same seed, same length.

    No camera value in this project has ever been through a video model - the library is
    tier `post` (effects.json), an ffmpeg crop. This is the other half of the comparison.
    """
    need(LAB)
    for cid in cards("cameras"):
        dst = f"{LAB}/camp_{cid}_00001_.mp4"
        if os.path.exists(dst) and not force:
            print(f"  = camp_{cid} exists")
            continue
        print(f"  > camp_{cid}")
        _i2v(f"{LAB}/kf_a_00001_.png", STEM + CAM_PROMPT[cid], f"{REL}/camp_{cid}")


def stage_motion(force=False):
    need(LAB)
    for mid, _kind, text in MOTION:
        dst = f"{LAB}/mot_{mid}_00001_.mp4"
        if os.path.exists(dst) and not force:
            print(f"  = mot_{mid} exists")
            continue
        print(f"  > mot_{mid}")
        _i2v(f"{LAB}/kf_a_00001_.png", text, f"{REL}/mot_{mid}")


# ═══════════════════════════════════════════════════════════════════ CPU stages
X264 = ("-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p")
# One codec setting for every clip in the comparison. x264 contributes its own high
# frequency noise floor and a mixed CRF would show up as a difference between moves.


def stage_post():
    """No GPU. The three post-tier libraries, applied to REAL generated clips.

    Also renders every camera move over the STILL keyframe. That second set is the exact
    isolation of the ffmpeg operation - any difference between two of those clips is the
    move and nothing else, which is what makes the pairwise matrix a real detector.
    """
    from short import fx_chain                              # noqa: E402
    need(f"{LAB}/post", f"{LAB}/still", f"{LAB}/trans", f"{LAB}/pace")
    base_a = f"{LAB}/base_a_00001_.mp4"
    base_b = f"{LAB}/base_b_00001_.mp4"
    kf_a = f"{LAB}/kf_a_00001_.png"
    for p in (base_a, base_b, kf_a):
        if not os.path.exists(p):
            sys.exit(f"missing {p} - run the GPU stages first")

    print("  cameras (post, over the real clip + over the still)")
    for cid in cards("cameras"):
        chain = fx_chain([cid], W, H, FPS, length=SECS) or "null"
        # over the real generated clip - this is what actually ships
        sh("ffmpeg", "-y", "-v", "error", "-i", base_a,
           "-vf", f"{chain},format=yuv420p", "-r", str(FPS), *X264, "-an",
           f"{LAB}/post/{cid}.mp4")
        # over the still - isolates the ffmpeg op with zero model motion in it
        sh("ffmpeg", "-y", "-v", "error", "-loop", "1", "-t", f"{SECS:.3f}", "-i", kf_a,
           "-vf", f"scale={W}:{H},{chain},format=yuv420p", "-r", str(FPS), *X264,
           f"{LAB}/still/{cid}.mp4")
        print(f"    {cid:11s} chain={'(none)' if chain == 'null' else chain[:70]}")

    print("  transitions (between two real clips)")
    for tid in cards("transitions"):
        c = card("transitions", tid)
        dst = f"{LAB}/trans/{tid}.mp4"
        dur = max(c.get("frames", 0), 1) / float(FPS)
        if not c.get("filter"):
            # no picture filter: a hard join. cut/smash/j_cut/l_cut are audio or nothing,
            # match_cut is an authoring instruction. Rendered anyway so the card has a
            # clip showing exactly what the picture does - which is: nothing.
            sh("ffmpeg", "-y", "-v", "error", "-i", base_a, "-i", base_b,
               "-filter_complex",
               f"[0:v]trim=0:1.6,setpts=PTS-STARTPTS,format=yuv420p[a];"
               f"[1:v]trim=0:1.6,setpts=PTS-STARTPTS,format=yuv420p[b];"
               f"[a][b]concat=n=2:v=1:a=0",
               "-r", str(FPS), *X264, "-an", dst)
        else:
            f = c["filter"].format(d=f"{dur:.2f}")
            sh("ffmpeg", "-y", "-v", "error", "-i", base_a, "-i", base_b,
               "-filter_complex",
               f"[0:v]trim=0:1.6,setpts=PTS-STARTPTS,format=yuv420p[a];"
               f"[1:v]trim=0:1.6,setpts=PTS-STARTPTS,format=yuv420p[b];"
               f"[a][b]{f}:offset=0.9",
               "-r", str(FPS), *X264, "-an", dst)
        print(f"    {tid:11s} frames={c.get('frames')} filter={c.get('filter')}")

    print("  pacing (alternating real clips at each rate)")
    for pid in cards("pacing"):
        p = card("pacing", pid)
        if p.get("status") != "ready":
            continue
        unit = 0.55 * float(p.get("scale", 1.0))
        parts = []
        for i in range(6):
            src = base_a if i % 2 == 0 else base_b
            t = unit * (1.0 if p.get("rhythm") == "steady"
                        else (1.0 - i * 0.12 if p["rhythm"] == "accelerating"
                              else 1.0 + i * 0.12))
            q = f"{LAB}/pace/_p{i}.mp4"
            # take a DIFFERENT second of the source each time, so consecutive cuts are not
            # the same frames over again - otherwise the pacing demo reads as one shot
            ss = 0.4 * i
            sh("ffmpeg", "-y", "-v", "error", "-ss", f"{ss:.2f}", "-i", src,
               "-t", f"{max(t, 0.12):.2f}", "-vf", "format=yuv420p",
               "-r", str(FPS), *X264, "-an", q)
            parts.append(q)
        lst = f"{LAB}/pace/_list.txt"
        open(lst, "w").write("".join(f"file '{x}'\n" for x in parts))
        sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
           "-c", "copy", f"{LAB}/pace/{pid}.mp4")
        for x in parts:
            os.remove(x)
        os.remove(lst)
        print(f"    {pid:14s} scale={p.get('scale')} rhythm={p.get('rhythm')}")


# ═══════════════════════════════════════════════════════════════════ measurement
def _np():
    import numpy as np
    return np


def frames_gray(path, width=320, count=None):
    """Decode a clip to a stack of grayscale float arrays."""
    np = _np()
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={width}:-2,format=gray",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True)
    h = None
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        sw, shh = [int(x) for x in p.stdout.strip().split(",")[:2]]
        h = int(round(shh * width / sw / 2)) * 2
    except Exception:
        h = 176
    buf = np.frombuffer(r.stdout, dtype=np.uint8)
    n = len(buf) // (width * h)
    if n == 0:
        return np.zeros((0, h, width), dtype=np.float64)
    a = buf[:n * width * h].reshape(n, h, width).astype(np.float64)
    if count:
        idx = [int(round(i * (n - 1) / (count - 1))) for i in range(count)]
        a = a[idx]
    return a


def phase_shift(a, b):
    """Integer (dx, dy) that maps a onto b, by FFT phase correlation.

    Returns (dx, dy, peak). Positive dx means content in `b` sits FURTHER RIGHT than in
    `a`, i.e. the picture content moved right, i.e. the camera panned LEFT. The sign
    convention is asserted by selftest() before any measurement runs.
    """
    np = _np()
    if a.shape != b.shape or a.size == 0:
        return 0.0, 0.0, 0.0
    wy = np.hanning(a.shape[0])[:, None]
    wx = np.hanning(a.shape[1])[None, :]
    aw = (a - a.mean()) * wy * wx
    bw = (b - b.mean()) * wy * wx
    A = np.fft.rfft2(aw)
    B = np.fft.rfft2(bw)
    R = B * np.conj(A)
    R /= (np.abs(R) + 1e-12)
    r = np.fft.irfft2(R, s=a.shape)
    idx = np.unravel_index(np.argmax(r), r.shape)
    dy, dx = float(idx[0]), float(idx[1])
    if dy > a.shape[0] / 2:
        dy -= a.shape[0]
    if dx > a.shape[1] / 2:
        dx -= a.shape[1]
    peak = float(r.max())
    return dx, dy, peak


def selftest():
    """A reversed sign would make every verdict in this file confidently wrong."""
    np = _np()
    rng = np.random.default_rng(0)
    img = rng.random((176, 320)) * 255
    img = np.array([[img[y // 4 * 4, x // 4 * 4] for x in range(320)] for y in range(176)])
    # shift content 8px to the RIGHT
    b = np.roll(img, 8, axis=1)
    dx, dy, pk = phase_shift(img, b)
    assert abs(dx - 8) < 1.5 and abs(dy) < 1.5, f"phase_shift x broken: {dx},{dy}"
    # shift content 6px DOWN
    b = np.roll(img, 6, axis=0)
    dx, dy, pk = phase_shift(img, b)
    assert abs(dy - 6) < 1.5 and abs(dx) < 1.5, f"phase_shift y broken: {dx},{dy}"
    return True


def displacement(path, width=320):
    """The four-number move signature, in pixels at native clip width."""
    np = _np()
    fr = frames_gray(path, width=width)
    if len(fr) < 2:
        return None
    a, b = fr[0], fr[-1]
    h, w = a.shape
    scale = W / float(w)                      # report at native 1280 wide
    hw, hh = w // 2, h // 2
    dxl = phase_shift(a[:, :hw], b[:, :hw])
    dxr = phase_shift(a[:, hw:], b[:, hw:])
    dyt = phase_shift(a[:hh, :], b[:hh, :])
    dyb = phase_shift(a[hh:, :], b[hh:, :])
    # per-frame global drift, so a move that goes and comes back is not read as static
    tot = 0.0
    for i in range(1, len(fr)):
        d = phase_shift(fr[i - 1], fr[i])
        tot += math.hypot(d[0], d[1])
    # `activity` is deliberately NOT a displacement. Phase correlation answers "did the
    # frame as a whole shift", which is the camera question. It is blind to rain falling in
    # a locked-off shot, or a neon sign flickering: nothing translates, so displacement
    # reads zero and a clip where plenty happens looks identical to a frozen one. This is
    # the mean absolute frame-to-frame luma change, 0-255, which answers the other
    # question - did ANYTHING change - and the two together separate the failure modes.
    act = float(np.abs(np.diff(fr, axis=0)).mean()) if len(fr) > 1 else 0.0
    return {
        "frames": int(len(fr)),
        "dx_left": round(dxl[0] * scale, 1),
        "dx_right": round(dxr[0] * scale, 1),
        "dy_top": round(dyt[1] * scale, 1),
        "dy_bottom": round(dyb[1] * scale, 1),
        "path_len": round(tot * scale, 1),
        "activity": round(act, 2),
        "peak": round(min(dxl[2], dxr[2], dyt[2], dyb[2]), 4),
    }


def jitter(path, width=1280):
    """Peak excursion from frame 0, measured at NATIVE width.

    The 320-wide analysis quantises to 4px at 1280 and cannot see a small oscillation at
    all - `handheld` is a +/-2px crop wobble, which rounds to zero there. A move can be
    real and still be too small to see; this is the number that tells the two apart.
    """
    np = _np()
    fr = frames_gray(path, width=width)
    if len(fr) < 2:
        return None
    a = fr[0]
    xs, ys = [], []
    step = max(1, len(fr) // 24)
    for i in range(1, len(fr), step):
        dx, dy, _ = phase_shift(a, fr[i])
        xs.append(dx)
        ys.append(dy)
    return {"max_dx": round(max(abs(x) for x in xs), 1),
            "max_dy": round(max(abs(y) for y in ys), 1),
            "span_x": round(max(xs) - min(xs), 1),
            "span_y": round(max(ys) - min(ys), 1)}


def classify(d):
    """Name the move family from the signature. Thresholds in px at 1280 wide."""
    if d is None:
        return "unreadable"
    T = 6.0                                   # below this it is measurement noise
    xl, xr, yt, yb = d["dx_left"], d["dx_right"], d["dy_top"], d["dy_bottom"]
    big = max(abs(xl), abs(xr), abs(yt), abs(yb))
    if big < T:
        return "NO MOVE"
    out = []
    if abs(xl) >= T and abs(xr) >= T and xl * xr < 0:
        out.append("zoom-in (diverging)" if xl < 0 else "zoom-out (converging)")
    elif (xl + xr) / 2 <= -T:
        out.append("content left / camera pans RIGHT")
    elif (xl + xr) / 2 >= T:
        out.append("content right / camera pans LEFT")
    if abs(yt) >= T and abs(yb) >= T and yt * yb < 0:
        out.append("vertical zoom")
    elif (yt + yb) / 2 <= -T:
        out.append("content up / camera tilts DOWN")
    elif (yt + yb) / 2 >= T:
        out.append("content down / camera tilts UP")
    return "; ".join(out) or "movement, no clean family"


def luma_curve(path, n=16, width=160):
    """Mean luma per frame, resampled to n points.

    Displacement is the wrong measurement for a transition: frame 0 and the last frame are
    two DIFFERENT shots, so a phase correlation between them reports the difference between
    a wet street and a desert, not the transition. What separates these cards is what
    happens to the picture in between - fade_black dips toward 0, fade_white spikes toward
    255, a hard cut does neither.
    """
    np = _np()
    fr = frames_gray(path, width=width)
    if len(fr) == 0:
        return []
    v = fr.mean(axis=(1, 2))
    idx = [int(round(i * (len(v) - 1) / (n - 1))) for i in range(n)]
    # min/max come from EVERY frame, not from the n samples. `flash` is 2 frames long at
    # 24fps; a 16-point curve steps straight over it and reports the card as identical to
    # a hard cut, which it is not.
    return ([round(float(v[i]), 1) for i in idx],
            round(float(v.min()), 1), round(float(v.max()), 1))


def cut_times(path, thresh=18.0, width=160):
    """Shot boundaries, in seconds, from consecutive-frame luma jumps.

    For pacing the meaningful number is not displacement, it is how long each shot is held.
    The demo alternates two visually opposite clips, so a cut is a large step change.
    """
    np = _np()
    fr = frames_gray(path, width=width)
    if len(fr) < 2:
        return {"cuts": [], "shot_lengths": [], "n_shots": 0, "secs": 0.0}
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    cuts = [round((i + 1) / float(FPS), 2) for i, x in enumerate(d) if x > thresh]
    # collapse runs of adjacent frames into one boundary
    merged = []
    for c in cuts:
        if not merged or c - merged[-1] > 0.08:
            merged.append(c)
    total = len(fr) / float(FPS)
    bounds = [0.0] + merged + [round(total, 2)]
    lens = [round(bounds[i + 1] - bounds[i], 2) for i in range(len(bounds) - 1)]
    return {"cuts": merged, "shot_lengths": lens, "n_shots": len(lens),
            "secs": round(total, 2),
            "mean_shot": round(sum(lens) / max(len(lens), 1), 2)}


def mad(p1, p2, width=320):
    """Mean absolute pixel difference between two clips, 0-255 luma.

    This is the number the project already has for pan_l vs pan_r (70.9). Two moves that
    are secretly the same operation score ~0 here and nothing else catches them.
    """
    np = _np()
    a = frames_gray(p1, width=width)
    b = frames_gray(p2, width=width)
    n = min(len(a), len(b))
    if n == 0:
        return None
    return round(float(np.abs(a[:n] - b[:n]).mean()), 2)


def stage_measure():
    np = _np()
    selftest()
    print("  phase_shift selftest OK (sign convention verified)")
    out = {"_note": "displacement in px at 1280 wide, first frame to last. "
                    "mad = mean abs luma difference 0-255, whole clip.",
           "seed": SEED, "frames": FRAMES, "size": [W, H]}

    groups = {
        "cameras_post_still": (f"{LAB}/still", cards("cameras")),
        "cameras_post_clip": (f"{LAB}/post", cards("cameras")),
        "cameras_prompted": (LAB, [f"camp_{c}_00001_" for c in cards("cameras")]),
        "motion": (LAB, [f"mot_{m[0]}_00001_" for m in MOTION]),
    }
    for gname, (d, ids) in groups.items():
        print(f"\n  == {gname}")
        out[gname] = {}
        for cid in ids:
            p = f"{d}/{cid}.mp4"
            if not os.path.exists(p):
                print(f"    {cid:24s} MISSING")
                continue
            key = cid.replace("camp_", "").replace("mot_", "").replace("_00001_", "")
            dd = displacement(p)
            dd["verdict"] = classify(dd)
            if gname == "cameras_post_still":
                dd["jitter_native_px"] = jitter(p)
            out[gname][key] = dd
            extra = ""
            if dd.get("jitter_native_px"):
                j = dd["jitter_native_px"]
                extra = f"  [native span {j['span_x']:.0f}x{j['span_y']:.0f}px]"
            print(f"    {key:24s} dxL{dd['dx_left']:+7.1f} dxR{dd['dx_right']:+7.1f} "
                  f"dyT{dd['dy_top']:+7.1f} dyB{dd['dy_bottom']:+7.1f} "
                  f"path{dd['path_len']:7.1f} act{dd['activity']:6.2f}  "
                  f"{dd['verdict']}{extra}")

    # ── transitions: luma over time, not displacement ─────────────────────────
    print("\n  == transitions (luma curve; 0=black 255=white)")
    out["transitions"] = {}
    for tid in cards("transitions"):
        p = f"{LAB}/trans/{tid}.mp4"
        if not os.path.exists(p):
            print(f"    {tid:12s} MISSING")
            continue
        c = card("transitions", tid)
        cur, lmin, lmax = luma_curve(p)
        rec = {"tier": "post-ffmpeg" if c.get("filter") else "picture: none",
               "filter": c.get("filter"), "frames": c.get("frames"),
               "luma_curve": cur, "luma_min": lmin, "luma_max": lmax}
        out["transitions"][tid] = rec
        print(f"    {tid:12s} min{lmin:6.1f} max{lmax:6.1f}  "
              + " ".join(f"{v:5.0f}" for v in cur))

    # ── pacing: shot lengths, not displacement ────────────────────────────────
    print("\n  == pacing (shot lengths in seconds)")
    out["pacing"] = {}
    for pid in cards("pacing"):
        p = f"{LAB}/pace/{pid}.mp4"
        if not os.path.exists(p):
            continue
        pc = card("pacing", pid)
        rec = cut_times(p)
        rec["scale"] = pc.get("scale")
        rec["rhythm"] = pc.get("rhythm")
        out["pacing"][pid] = rec
        print(f"    {pid:14s} scale={pc.get('scale'):<5} {rec['n_shots']} shots "
              f"mean {rec['mean_shot']:.2f}s total {rec['secs']:.2f}s  "
              f"{rec['shot_lengths']}")

    # pairwise MAD matrices - the identical-move detector
    for gname, (d, ids) in (("cameras_post_still", groups["cameras_post_still"]),
                            ("cameras_post_clip", groups["cameras_post_clip"]),
                            ("cameras_prompted", groups["cameras_prompted"]),
                            ("transitions", (f"{LAB}/trans", cards("transitions")))):
        paths = {}
        for cid in ids:
            p = f"{d}/{cid}.mp4"
            if os.path.exists(p):
                paths[cid.replace("camp_", "").replace("_00001_", "")] = p
        keys = sorted(paths)
        print(f"\n  == pairwise MAD: {gname}")
        print("    " + "".join(f"{k[:8]:>9s}" for k in keys))
        m = {}
        cache = {k: frames_gray(paths[k]) for k in keys}
        for i in keys:
            row = []
            for j in keys:
                if i == j:
                    row.append(0.0)
                    continue
                a, b = cache[i], cache[j]
                n = min(len(a), len(b))
                row.append(round(float(np.abs(a[:n] - b[:n]).mean()), 2))
            m[i] = dict(zip(keys, row))
            print(f"    {i[:10]:<10s}" + "".join(f"{v:9.2f}" for v in row))
        out[f"mad_{gname}"] = m
        ident = [(i, j) for ii, i in enumerate(keys) for j in keys[ii + 1:]
                 if m[i][j] < 1.0]
        if ident:
            print("    IDENTICAL (MAD < 1.0): " + ", ".join(f"{i}=={j}" for i, j in ident))
        out[f"identical_{gname}"] = [list(x) for x in ident]

    need(f"{SAMP}/motion")
    with open(f"{SAMP}/motion/_measurements.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\n  wrote {SAMP}/motion/_measurements.json")
    return out


# ═══════════════════════════════════════════════════════════════════ strips
def _font(sz):
    from PIL import ImageFont
    for p in ("/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def strip(clips, dst, ncols=6, cell=232, title=""):
    """One row per clip: `ncols` frames evenly spaced from first to last, labelled.

    This is the artifact a human reads. A metric can say pan_l and pan_r differ by 70.9;
    only the strip says which way each one went.
    """
    from PIL import Image, ImageDraw
    np = _np()
    lab = 128
    rows = []
    for name, path in clips:
        fr = frames_gray(path, width=cell, count=ncols)
        if len(fr) == 0:
            continue
        rows.append((name, fr))
    if not rows:
        print(f"    (nothing for {dst})")
        return
    ch = rows[0][1].shape[1]
    th = 30 if title else 0
    img = Image.new("RGB", (lab + ncols * cell, th + len(rows) * (ch + 2)), (16, 16, 18))
    d = ImageDraw.Draw(img)
    if title:
        d.text((8, 7), title, font=_font(17), fill=(255, 210, 90))
    for ri, (name, fr) in enumerate(rows):
        y = th + ri * (ch + 2)
        d.text((6, y + ch // 2 - 8), name[:17], font=_font(13), fill=(235, 235, 240))
        for ci in range(min(ncols, len(fr))):
            a = np.clip(fr[ci], 0, 255).astype("uint8")
            img.paste(Image.fromarray(a).convert("RGB"), (lab + ci * cell, y))
    img.save(dst)
    print(f"    {dst}  ({len(rows)} rows)")


def stage_strips():
    need(f"{SAMP}/cameras", f"{SAMP}/motion", f"{SAMP}/transitions")
    cam = cards("cameras")
    strip([(c, f"{LAB}/still/{c}.mp4") for c in cam],
          f"{SAMP}/cameras/_strip_post_still.png",
          title="CAMERA - post tier (ffmpeg) over the STILL keyframe. left->right = time.")
    strip([(c, f"{LAB}/post/{c}.mp4") for c in cam],
          f"{SAMP}/cameras/_strip_post_clip.png",
          title="CAMERA - post tier (ffmpeg) over the REAL LTX clip. what actually ships.")
    strip([(c, f"{LAB}/camp_{c}_00001_.mp4") for c in cam],
          f"{SAMP}/cameras/_strip_prompted.png",
          title="CAMERA - asked of the video model. same keyframe, same seed, same length.")
    strip([(m[0], f"{LAB}/mot_{m[0]}_00001_.mp4") for m in MOTION],
          f"{SAMP}/motion/_strip_motion.png", cell=210,
          title="MOTION - the only string the video model reads. one keyframe, one seed.")
    strip([(t, f"{LAB}/trans/{t}.mp4") for t in cards("transitions")],
          f"{SAMP}/transitions/_strip.png", ncols=8, cell=176,
          title="TRANSITION - between two REAL clips (A=street dusk, B=desert noon).")
    strip([(p, f"{LAB}/pace/{p}.mp4") for p in cards("pacing")
           if card("pacing", p).get("status") == "ready"],
          f"{SAMP}/motion/_strip_pacing.png", ncols=10, cell=150,
          title="PACING - cut rate over real clips. A/B alternation, evenly sampled.")


def stage_publish():
    """Copy the finished clips into the sample dirs the app reads, with posters."""
    need(f"{SAMP}/cameras", f"{SAMP}/motion", f"{SAMP}/transitions")
    n = 0
    for c in cards("cameras"):
        for src, dst in ((f"{LAB}/post/{c}.mp4", f"{SAMP}/cameras/{c}.mp4"),
                         (f"{LAB}/camp_{c}_00001_.mp4",
                          f"{SAMP}/cameras/{c}_prompted.mp4")):
            if os.path.exists(src):
                shutil.copy(src, dst)
                sh("ffmpeg", "-y", "-v", "error", "-i", dst, "-vf",
                   "select=eq(n\\,0),scale=640:-2", "-vframes", "1", "-q:v", "4",
                   dst[:-4] + ".jpg")
                n += 1
    for m in MOTION:
        src = f"{LAB}/mot_{m[0]}_00001_.mp4"
        if os.path.exists(src):
            shutil.copy(src, f"{SAMP}/motion/{m[0]}.mp4")
            n += 1
    for p in cards("pacing"):
        src = f"{LAB}/pace/{p}.mp4"
        if os.path.exists(src):
            shutil.copy(src, f"{SAMP}/motion/pacing_{p}.mp4")
            n += 1
    for t in cards("transitions"):
        src = f"{LAB}/trans/{t}.mp4"
        if os.path.exists(src):
            shutil.copy(src, f"{SAMP}/transitions/{t}.mp4")
            n += 1
    for k in ("kf_a", "kf_b"):
        src = f"{LAB}/{k}_00001_.png"
        if os.path.exists(src):
            sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vf", "scale=640:-2",
               "-q:v", "4", f"{SAMP}/motion/_{k}.jpg")
    print(f"  published {n} clips")


# ═══════════════════════════════════════════════════════════════════ main
STAGES = {
    "keyframes": stage_keyframes, "base": stage_base, "cam-prompt": stage_cam_prompt,
    "motion": stage_motion, "post": stage_post, "measure": stage_measure,
    "strips": stage_strips, "publish": stage_publish,
}
ORDER = ["keyframes", "base", "cam-prompt", "motion", "post", "measure", "strips",
         "publish"]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", nargs="+", choices=ORDER + ["all", "selftest"])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if "selftest" in a.stage:
        selftest()
        print("selftest OK")
        return
    todo = ORDER if "all" in a.stage else a.stage
    gpu = ("base", "cam-prompt", "motion")

    def drain():
        if PENDING:
            wait_all(list(PENDING), "clips")
            del PENDING[:]

    for s in todo:
        print(f"\n### {s}", flush=True)
        if s == "keyframes":
            # blocking: every clip stage needs the PNG on disk to stage into COMFY/input
            stage_keyframes(force=a.force)
        elif s in gpu:
            # queue only - all three stages pile into ONE contiguous batch
            STAGES[s](force=a.force)
        else:
            drain()                       # CPU stages need the clips to exist
            STAGES[s]()
    drain()


if __name__ == "__main__":
    try:
        import numpy  # noqa: F401
    except ImportError:
        if os.path.exists(VENV) and os.environ.get("_MLAB_REEXEC") != "1":
            os.environ["_MLAB_REEXEC"] = "1"
            os.execv(VENV, [VENV, os.path.abspath(__file__)] + sys.argv[1:])
    main()
