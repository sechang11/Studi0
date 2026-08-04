#!/usr/bin/env python3
"""Render one CLIP per style from a keyframe that differs only by style, so a style can be
judged in MOTION by looking.

    python3 studio/_tools/video_examples.py                  # the representative set
    python3 studio/_tools/video_examples.py flat_vector      # one style
    python3 studio/_tools/video_examples.py --set ready      # every status=ready card
    python3 studio/_tools/video_examples.py --measure        # re-measure, no GPU
    python3 studio/_tools/video_examples.py --cards          # stamp verdicts onto cards

THE VIDEO LAYER WAS THE ONLY UNMEASURED LAYER. 130 style cards each carry a `works_for`
sentence predicting how the style behaves through an image-to-video pass, and every one of
those sentences was INFERRED - written from what the idiom is made of, never from a clip.
The 24 mp4s in studio/samples/ are ffmpeg on stills: cameras, transitions and pacing are
all compositing, so before this tool ran, no library sample had ever been through a video
model at all. This is the tool that turns the predictions into findings.

ISOLATION, AND WHY IT IS THE WHOLE DESIGN. One subject, one seed, one motion prompt, one
clip length, one resolution, for every style. The only thing that varies between two clips
in studio/samples/video/ is the style card. This project has broken that discipline before
- 133 of 134 capability cards varied the subject alongside the variable and so demonstrated
nothing - and the video metric below is *especially* easy to fool that way, because `boil`
rises with camera movement (a plain ffmpeg crop-pan over a literal still image measures
boil 0.385 from resampling alone). Two clips whose subjects move differently cannot be
compared on it. So the motion prompt is held constant and deliberately asks for almost no
movement, and no camera move, grade or fx is ever applied before measuring.

THE SUBJECT is style_examples.py's held-constant figure with one addition. Face (rendering
idiom shows there first, and anatomy is the first thing an i2v pass breaks), a garment with
folds (line and shading), a receding street (depth and palette) - plus a brick wall, which
the stills subject did not need and this one does: a dense mid-frequency texture field is
the thing predicted to boil, and without one in frame the headline prediction cannot fail.

LENGTH IS 193 FRAMES, 8.04s, NOT THE 97 SHORT.PY DEFAULTS TO. LTX cost is nearly flat in
length (measured here: 13.7s for 193 frames against 13.5s for 97), so the long clip is
free, and style decay does not show up inside four seconds - it has a knee around 3s. A
97-frame sample would have reported "everything holds" and been misleading for anyone
cutting an 8-second shot. Because 97 is one of the sampled points, every metric is reported
TWICE, over the full 8s and over the first 4s, from a single render.

WHAT IS DELIBERATELY LEFT AT ITS SHIPPING VALUE, so this measures the pipeline that exists
rather than a better one someone might build:
  * node 11, the video negative, is never set - short.py does not set it either, so every
    clip any film has ever rendered used the workflow's built-in string. Whether the style's
    own tags/prose/negative_add SHOULD reach the video model is a different experiment.
  * node 9 LTXVPreprocess img_compression stays 18. The keyframe carrying 100% of the style
    is H.264 round-tripped before the model sees it. `kf_retention` below measures what that
    costs; changing it is a different experiment.
  * node 23 strength 1.0, node 5 distill LoRA 0.5, node 30 sigmas, node 31 cfg 1.0.

THE METRIC, and why two numbers and not one. Frame-to-frame luma difference split into two
spatial bands by a sigma=2 gaussian at 512px wide. Coherent motion displaces large
structures, so it lands in the LOW band; boiling texture is fine detail re-rolling in place
under a structure that is not moving, so it lands in the HIGH band.
    motion  mean low-band YDIF. Did anything move. The classic i2v failure sits near 0.
    churn   stdev/mean of low-band YDIF. Real movement is steady; morph thrashes.
    boil    mean high-band YDIF / mean high-band amplitude. The fraction of fine texture
            that re-rolls each frame.
    detail  high-band amplitude at the end / at frame 0. BOILING AND DISSOLVING ARE
            DIFFERENT FAILURES: boil 0.9 says the screentone is thrashing, detail 0.55 says
            it was quietly smoothed away and the style left without telling you.
    kf_retention  frame 0's high-band amplitude / the keyframe PNG's. How much of the style
            survived merely crossing into the clip, before any drift. Without it, T1 losses
            (codec + VAE) get misread as T2 drift.
512px and not smaller: the high band IS the measurement and downscaling destroys it.

Calibration measured on this box, so the numbers below have a floor and a ceiling:
    ffmpeg still, no move      motion 0.000  boil 0.000   <- exact zero, so any value is signal
    ffmpeg crop-pan on a still motion 1.400  boil 0.385   <- resampling alone
    LTX t2v 4s, real fire      motion 2.646  boil 0.196

THE NUMBER SCREENS, IT DOES NOT JUDGE. It cannot see anatomy - photorealistic's predicted
failure is faces and hands melting, and that barely moves any of the four. Every clip here
also gets a FRAME STRIP: the keyframe plus eight frames sampled across the clip, tiled with
labels, and a second strip of native-resolution crops of the same nine. Drift you can see
in a still. Looking is not optional and the strips exist so that looking is cheap.

------------------------------------------------------------------------------------------
WHAT THE FIRST RUN MEASURED (2026-08-04, 15 clips, 13 styles + both controls, 40.5s/clip).
Read this before trusting either the library's predictions or this tool's own metric.

1. THE LIBRARY'S GOVERNING PREDICTION IS NOT SUPPORTED. "Flat, high-contrast idioms hold
   through i2v; fine grain and dot fields boil" was the standing claim on 130 cards. All
   NINE illustration styles held their idiom for the full 8 seconds - including the three
   the library named as worst cases. manga_screentone, whose card called it "the WORST case
   in this set", has DEAD FLAT detail octiles (0.99 0.98 0.98 0.97 0.97 0.98 0.97 0.98) and
   boil 0.214, below the no-style qwen control's 0.228. The two clips that lost the most
   fine detail, flat_vector (0.866) and ligne_claire (0.859), were both predicted to be the
   top performers - they were simply the two highest-motion clips.

2. THE AXIS THAT PREDICTS SURVIVAL IS ILLUSTRATION vs PHOTOGRAPH, NOT FLAT vs TEXTURED.
   The two controls are the clean test - same subject, seed, motion prompt and length,
   differing only in which engine drew the keyframe:
       _control__anime  octiles 1.01 1.02 1.05 1.07 1.06 1.02 1.01 1.01   flat
       _control__qwen   octiles 1.00 0.99 0.98 0.95 0.93 0.91 0.89 0.87   monotonic decay
   Mean detail at 8s: 8 anime-engine styles 0.946, 5 qwen-engine styles 0.754
   (controls 1.007 and 0.870, excluded from both means). RECOMPUTED ON REVIEW -
   this line used to read 9 anime 0.953 / 4 qwen 0.690, which was correct when
   written but went stale when pointillism was reclassified anime->qwen by another
   agent after this sweep ran. pointillism is the one clip whose keyframe did not
   render its own idiom, and it is now the HIGHEST-scoring qwen clip (1.011), so
   moving it narrows the headline gap from 0.263 to 0.192 - about 40%% - on pure
   bookkeeping. The direction of the finding survives; its size was overstated. At MATCHED high motion the split is starker still: manga 1.50/0.977
   and pixel_art 1.35/0.970 hold, while brutalist 1.87/0.442 and photorealistic 2.41/0.510
   collapse. Caveat: engine and idiom are perfectly confounded in this library - every
   photographic style routes to qwen - so this separates ILLUSTRATION from PHOTOGRAPH and
   cannot say which of the two is the cause.

3. AT 8 SECONDS LTX DOES NOT HOLD A SHOT, IT INVENTS NARRATIVE. In two of five photographic
   clips the subject WALKED OUT OF FRAME - photorealistic ends on an empty street, and its
   octiles are flat then cliff (0.94 0.89 0.52). Both clips are clean at 4s (detail 0.964
   and 0.934). That is the real ceiling on clip length here, and it is a composition
   failure, not a style failure. This is why the tool reports 4s and 8s from one render.

4. HOLDING THE MOTION PROMPT CONSTANT DID NOT HOLD MOTION CONSTANT. One identical sentence
   produced motion from 0.345 (watercolour) to 2.772 (flat_vector), an 8x spread, and the
   pinned camera was ignored - most clips drift or push in. The isolation protocol this
   metric was designed around therefore does not deliver what it promised.

5. SO `boil` CANNOT RANK STYLE STABILITY, AND SHOULD NOT BE USED FOR IT. Across the sweep
   it tracks motion almost monotonically, with a downward correction where fine-detail
   amplitude is high. `detail` is the load-bearing number - and even it drops when the
   COMPOSITION changes rather than the texture, which is exactly what photorealistic's
   0.510 is. Neither number replaces the strips.

6. `kf_retention` CAME BACK 0.987-1.027 ON ALL 15 CLIPS. The keyframe's fine-detail
   amplitude survives the CRF-18 LTXVPreprocess round trip and the VAE essentially intact,
   so img_compression=18 is not where style is being lost. (Amplitude ratio, not a
   similarity measure - but frame 0 is visually indistinguishable from the keyframe in
   every strip.)

7. ONE STYLE COULD NOT BE TESTED. pointillism's keyframe is not pointillist: the card
   declares engine=anime while recommending a qwen LoRA, and workflow 22 has no LoRA node,
   so the dot field never rendered. Its video prediction remains open. comic_halftone and
   stop_motion_felt carry the same mismatch and will fail the same way.

n=1 per style. One subject, one seed, one motion prompt. These are findings about this
subject at this length, not laws.
"""
import argparse
import datetime
import glob
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import set_path                                    # noqa: E402
from epic import load_wf, ensure_local, submit, wait_all, HOST  # noqa: E402

COMFY = os.environ.get("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
STYLES = os.path.join(STUDIO, "styles")
OUT = os.path.join(STUDIO, "samples", "video")
STAGE = "claude-generated/studio_video"

# ----------------------------------------------------------------- the constants
SEED = 7204          # keyframe seed, held for every style
VSEED = 8801         # video noise seed, held for every style
VID = (1280, 704)    # short.py's shipping clip size; the keyframe is rendered AT this size
FRAMES = 193         # 8n+1. 8.04s at 24fps
FPS = 24
HALF = 97            # the 4.04s point, so one render answers the 4s question too
SAMPLES = 8          # frames pulled for the strips, evenly across the clip

# The held-constant subject, in each engine's dialect - same scene either way, so an anime
# card and a qwen card are still showing the same thing. Taken from style_examples.py so
# each clip is readable against that style's existing still, plus the brick wall.
SUBJ_TAGS = ("1girl, solo, upper body, long dark hair, red scarf, wool coat, "
             "standing, looking at viewer, city street, brick wall, buildings, overcast")
SUBJ_PROSE = ("a young woman in a wool coat and red scarf standing on a city street in "
              "front of a brick wall, buildings receding behind her, overcast daylight, "
              "facing the camera")
Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG_BASE = "lowres, worst quality, bad anatomy, bad hands, watermark, text, signature"

# The one motion prompt. Physical events named as things that happen, per the governing
# rule that the model renders nouns and not adjectives - and mild, because the metric is
# only comparable across clips whose intended motion matches. The camera is explicitly
# pinned: a moving camera inflates boil by resampling and would swamp the style signal.
MOTION = ("She breathes and shifts her weight slightly. Her hair and the end of her scarf "
          "move in a light breeze. The camera does not move.")

# MAP 2's representative set. Only status=ready cards - a style that fails as a still would
# confound "did not render" with "did not survive" - and picked so the predictions SPLIT:
# four predicted to hold, five predicted to boil, two photographic controls, two structural
# extremes. _control is the baseline every other clip is read against.
SET = ["_control",
       "flat_vector", "ligne_claire", "silhouette_poster", "cel_anime_90s",
       "manga_screentone", "pointillism", "film_35mm", "ink_wash", "watercolour",
       "photorealistic", "cinestill_night", "brutalist", "pixel_art"]

FONT = next((p for p in (
    "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/google-carlito-fonts/Carlito-Bold.ttf") if os.path.exists(p)), "")


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


# ----------------------------------------------------------------- the keyframe
def keyframe_wf(st, engine):
    """Built exactly the way style_examples.py builds a still, so the input to the video
    pass is the library's own rendering of that style and not a second interpretation.
    Subject first, style appended: tag order is load-bearing here, the earlier and more
    specific tag wins, so the subject anchors the frame and the style modifies it.

    Rendered AT 1280x704, the size the clip is generated at, so nothing is resampled on the
    way in. That matters more here than anywhere else in the library: a resample is a
    low-pass, and the fine texture it would take off the top is the exact thing being
    measured.
    """
    neg = NEG_BASE + (", " + st["negative_add"] if st.get("negative_add") else "")
    if engine == "anime":
        wf = load_wf("22_anime_kf_ipadapter.json")
        set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
        set_path(wf, "4.inputs.weight", 0.0)          # IPAdapter off: no character here
        parts = [SUBJ_TAGS] + ([st["tags"]] if st.get("tags") else []) + [Q]
        set_path(wf, "5.inputs.text", ", ".join(parts))
        set_path(wf, "6.inputs.text", neg)
        set_path(wf, "8.inputs.seed", SEED)
        for n in ("7", "10"):
            set_path(wf, "%s.inputs.width" % n, VID[0])
            set_path(wf, "%s.inputs.height" % n, VID[1])
        return wf, "11.inputs.filename_prefix"
    wf = load_wf("13_qwen_t2i_styled.json")
    prose = SUBJ_PROSE + (". " + st["prose"] if st.get("prose") else "")
    set_path(wf, "10.inputs.text", prose)
    set_path(wf, "11.inputs.text", neg)
    set_path(wf, "12.inputs.width", VID[0])
    set_path(wf, "12.inputs.height", VID[1])
    set_path(wf, "13.inputs.seed", SEED)
    return wf, "15.inputs.filename_prefix"


def clip_wf(staged, prefix):
    """workflow 12, the graph short.py actually ships clips on, touched only where short.py
    touches it. Everything else is left at the file's value on purpose - see the header."""
    wf = load_wf("12_ltx23_i2v_audio.json")
    set_path(wf, "8.inputs.image", staged)
    set_path(wf, "10.inputs.text", MOTION)
    set_path(wf, "20.inputs.width", VID[0])
    set_path(wf, "20.inputs.height", VID[1])
    set_path(wf, "20.inputs.length", FRAMES)
    set_path(wf, "21.inputs.frames_number", FRAMES)    # must match node 20 or it errors
    set_path(wf, "32.inputs.noise_seed", VSEED)
    set_path(wf, "43.inputs.filename_prefix", prefix)
    return wf


# ----------------------------------------------------------------- the metric
W, SIGMA = 512, 2.0
# NOT [\d.]+ . signalstats prints small values in scientific notation, so YDIF=1.9e-06
# matches as 1.9 and a literally static clip measures motion 4.79. scripts/analyze_shots.py
# line 55 still has that bug and its --worst list is consequently blind to frozen shots.
NUM = r"=([-+0-9.eE]+)"
_LO = "scale=%d:-2,format=gray,gblur=sigma=%s" % (W, SIGMA)
_HI = ("scale=%d:-2,format=gray,split[a][b];[b]gblur=sigma=%s[lo];"
       "[a][lo]blend=all_mode=grainextract" % (W, SIGMA))
_AMP = _HI + ",lutyuv=y=abs(val-128)"


def _stat(path, vf, key):
    vf = "%s,signalstats,metadata=print:key=lavfi.signalstats.%s:file=-" % (vf, key)
    r = sh("ffmpeg", "-hide_banner", "-v", "error", "-i", path, "-vf", vf, "-f", "null", "-")
    return [float(x) for x in re.findall(key + NUM, r.stdout)]


def _mean(v):
    return sum(v) / len(v) if v else 0.0


def measure(mp4, kf_png=None):
    lo = _stat(mp4, _LO, "YDIF")[1:]      # frame 0 has no predecessor
    hi = _stat(mp4, _HI, "YDIF")[1:]
    amp = _stat(mp4, _AMP, "YAVG")
    if not lo or not amp:
        return None

    def window(n):
        """Same four numbers over the first n frames, so the 4s answer and the 8s answer
        come out of one render instead of two."""
        l, h, a = lo[:n - 1], hi[:n - 1], amp[:n]
        if len(a) < 8:
            return {}
        m = _mean(l)
        tail = a[-max(1, len(a) // 8):]
        return {"motion": round(m, 3),
                "churn": round(statistics.pstdev(l) / m, 3) if m else None,
                "boil": round(_mean(h) / _mean(a), 3) if _mean(a) else None,
                "detail": round(_mean(tail) / a[0], 3) if a[0] else None}

    out = {"frames": len(amp), "full": window(len(amp)), "first_4s": window(min(HALF, len(amp))),
           "hi_amp_frame0": round(amp[0], 2),
           "hi_amp_end": round(_mean(amp[-max(1, len(amp) // 8):]), 2),
           # every eighth, so decay SHAPE is visible and not just its endpoint
           "detail_octiles": [round(_mean(amp[i * len(amp) // 8:(i + 1) * len(amp) // 8])
                                    / amp[0], 3) if amp[0] else None for i in range(8)]}
    if kf_png and os.path.exists(kf_png):
        k = _stat(kf_png, _AMP, "YAVG")
        if k and amp[0]:
            out["kf_hi_amp"] = round(k[0], 2)
            out["kf_retention"] = round(amp[0] / k[0], 3) if k[0] else None
    return out


# ----------------------------------------------------------------- the strips
def _idx():
    return [round(i * (FRAMES - 1) / (SAMPLES - 1)) for i in range(SAMPLES)]


def _tile(files, dst, cols=3):
    tmp = os.path.join(OUT, "_t")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    for i, f in enumerate(files):
        shutil.copy(f, os.path.join(tmp, "t_%02d.png" % i))
    rows = int(math.ceil(len(files) / float(cols)))
    r = sh("ffmpeg", "-y", "-v", "error", "-start_number", "0", "-framerate", "1",
           "-i", os.path.join(tmp, "t_%02d.png"),
           "-vf", "tile=%dx%d:padding=6:margin=6:color=0x141414" % (cols, rows),
           "-frames:v", "1", dst)
    shutil.rmtree(tmp, ignore_errors=True)
    return r


def _label(src, dst, text, crop=None, scale=None, frame=0):
    """One tile: pull a frame, optionally crop at native resolution, burn a label."""
    vf = []
    if src.endswith(".mp4"):
        vf.append("select=eq(n\\,%d)" % frame)
    if crop:
        vf.append("crop=%d:%d:%d:%d" % crop)
    if scale:
        vf.append("scale=%d:-2" % scale)
    if FONT:
        vf.append("drawtext=fontfile=%s:text='%s':fontsize=19:fontcolor=white:box=1:"
                  "boxcolor=0x000000C0:boxborderw=7:x=9:y=9" % (FONT, text))
    return sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vf", ",".join(vf),
              "-frames:v", "1", "-vsync", "0", dst)


def strips(name, mp4, kf_png):
    """Two strips per clip, because they answer different questions.

    <name>_strip.png    keyframe + 8 frames scaled to fit, 3x3. Composition drift, palette
                        drift, anatomy collapse - anything you read at a glance.
    <name>_detail.png   the same nine at NATIVE resolution, cropped to one fixed region.
                        Screentone, grain, dither and pixel grid live above the frequency a
                        scaled tile can carry; a downscaled strip would show them holding
                        no matter what they did. The crop box is identical for every style,
                        which is the isolation rule applied to the reading as well as to
                        the render.

    PNG and not webp, unlike the rest of samples/. These get judged on fine texture and a
    lossy codec would put its own artifacts exactly where the measurement is.
    """
    tmp = os.path.join(OUT, "_f")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    cx, cy, cw, ch = (VID[0] - 512) // 2, 110, 512, 288
    wide, deep = [], []
    for k, (src, fr, lab) in enumerate(
            [(kf_png, 0, "KEYFRAME  (input to the video pass)")] +
            [(mp4, f, "f%03d   %.2fs" % (f, f / float(FPS))) for f in _idx()]):
        if not os.path.exists(src):
            continue
        a = os.path.join(tmp, "w%02d.png" % k)
        b = os.path.join(tmp, "d%02d.png" % k)
        _label(src, a, lab, scale=512, frame=fr)
        _label(src, b, lab, crop=(cw, ch, cx, cy), frame=fr)
        if os.path.exists(a):
            wide.append(a)
        if os.path.exists(b):
            deep.append(b)
    if wide:
        _tile(wide, os.path.join(OUT, name + "_strip.png"))
    if deep:
        _tile(deep, os.path.join(OUT, name + "_detail.png"))
    shutil.rmtree(tmp, ignore_errors=True)


# ----------------------------------------------------------------- the run
def jobs(names, force):
    out = []
    for n in names:
        p = os.path.join(STYLES, n + ".json")
        if not os.path.exists(p):
            print("  %-20s NO SUCH CARD" % n)
            continue
        st = json.load(open(p, encoding="utf-8"))
        engs = ["anime", "qwen"] if st.get("engine") == "either" else [st.get("engine", "qwen")]
        for e in engs:
            tag = n if len(engs) == 1 else "%s__%s" % (n, e)
            out.append({"style": n, "card": st, "engine": e, "tag": tag,
                        "kf": os.path.join(OUT, tag + "_kf.png"),
                        "mp4": os.path.join(OUT, tag + ".mp4")})
    # engine order, so animagine loads once and qwen loads once instead of alternating
    out.sort(key=lambda j: (j["engine"], j["style"]))
    return [j for j in out if force or not os.path.exists(j["mp4"])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("only", nargs="?")
    ap.add_argument("--set", default="rep", choices=["rep", "ready", "all"])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--measure", action="store_true", help="re-measure existing clips, no GPU")
    ap.add_argument("--cards", action="store_true",
                    help="stamp verdicts.json onto the style cards. Authored by hand AFTER "
                         "looking at the strips - the tool renders and measures, it does "
                         "not decide.")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    if a.cards:
        return write_cards()

    if a.only:
        names = [a.only]
    elif a.set == "rep":
        names = SET
    else:
        names = sorted(f[:-5] for f in os.listdir(STYLES) if f.endswith(".json"))
        if a.set == "ready":
            names = [n for n in names
                     if json.load(open(os.path.join(STYLES, n + ".json"),
                                       encoding="utf-8")).get("status") == "ready"]

    work = jobs(names, a.force or a.measure)
    print("ISOLATION: seed %d / vseed %d / %dx%d / %d frames (%.2fs) / one motion prompt"
          % (SEED, VSEED, VID[0], VID[1], FRAMES, FRAMES / float(FPS)))
    print("MOTION: %s" % MOTION)
    print("%d clip(s)\n" % len(work))

    if not a.measure:
        pids = []
        for j in work:
            if os.path.exists(j["kf"]) and not a.force:
                continue
            wf, pfx = keyframe_wf(j["card"], j["engine"])
            set_path(wf, pfx, "%s/kf_%s" % (STAGE, j["tag"]))
            pids.append(submit(wf))
        if pids:
            print("=== KEYFRAMES: %d submitted as one batch ===" % len(pids))
            wait_all(pids, "keyframes")
        for j in work:
            ensure_local("%s/kf_%s_00001_.png" % (STAGE, j["tag"]), j["kf"], required=True)

        pids = []
        for j in work:
            staged = "videx_%s.png" % j["tag"]
            shutil.copy(j["kf"], os.path.join(COMFY, "input", staged))
            pids.append(submit(clip_wf(staged, "%s/clip_%s" % (STAGE, j["tag"]))))
        print("\n=== CLIPS: %d submitted as one batch ===" % len(pids))
        wait_all(pids, "clips")
        for j in work:
            ensure_local("%s/clip_%s_00001_.mp4" % (STAGE, j["tag"]), j["mp4"], required=False)

    mpath = os.path.join(OUT, "metrics.json")
    all_m = json.load(open(mpath, encoding="utf-8")) if os.path.exists(mpath) else {}
    all_m["_isolation"] = {
        "seed": SEED, "video_seed": VSEED, "size": list(VID), "frames": FRAMES, "fps": FPS,
        "motion_prompt": MOTION, "subject_tags": SUBJ_TAGS, "subject_prose": SUBJ_PROSE,
        "workflow": "12_ltx23_i2v_audio.json",
        "left_at_shipping_defaults": {
            "node11_video_negative": "static, frozen, blurry, distorted, morphing, warping,"
                                     " ugly, low quality, watermark, text overlay",
            "node9_img_compression": 18, "node23_strength": 1.0,
            "node5_distill_lora": 0.5, "node31_cfg": 1.0},
        "measured_utc": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds")}
    print("\n%-24s %7s %7s %7s %7s %7s %7s" %
          ("style", "motion", "churn", "boil", "det8s", "det4s", "kfret"))
    for j in work:
        if not os.path.exists(j["mp4"]):
            print("  %-22s NO CLIP" % j["tag"])
            continue
        strips(j["tag"], j["mp4"], j["kf"])
        m = measure(j["mp4"], j["kf"])
        if not m:
            continue
        all_m[j["tag"]] = m
        f, h = m["full"], m["first_4s"]
        print("%-24s %7.3f %7.3f %7.3f %7.3f %7.3f %7s" %
              (j["tag"], f["motion"], f["churn"] or 0, f["boil"] or 0, f["detail"] or 0,
               h.get("detail") or 0,
               ("%.3f" % m["kf_retention"]) if m.get("kf_retention") else "-"))
    json.dump(all_m, open(mpath, "w", encoding="utf-8"), indent=2)
    open(mpath, "a").write("\n")
    print("\nNOW LOOK AT THE STRIPS. %s/<style>_strip.png and _detail.png. The metric "
          "screens; it cannot see a melting face or a hand growing a finger, and it will "
          "call that clip stable." % OUT)


def _numbers(met, tag):
    m = met.get(tag, {})
    f, h = m.get("full", {}), m.get("first_4s", {})
    return {"motion": f.get("motion"), "churn": f.get("churn"), "boil": f.get("boil"),
            "detail_8s": f.get("detail"), "detail_4s": h.get("detail"),
            "detail_octiles": m.get("detail_octiles"),
            "kf_retention": m.get("kf_retention"),
            "clip": "/samples/video/%s.mp4" % tag,
            "strip": "/samples/video/%s_strip.png" % tag,
            "detail_strip": "/samples/video/%s_detail.png" % tag}


def write_cards():
    """Stamp studio/samples/video/verdicts.json onto the style cards.

    Touches `works_for` and `video_verdict` ONLY. engine, compose and status are somebody
    else's measurements and stay where they are. Every number written comes from
    metrics.json; the prose comes from verdicts.json, which is authored by hand after
    looking at the strips, because the metric screens and a person judges.

    verdicts.json is keyed by CARD id. `tag` names the clip whose numbers to record, and
    defaults to the card id; `tags` records several under a per-engine dict, for a card
    like _control that renders on both engines.
    """
    vp = os.path.join(OUT, "verdicts.json")
    mp = os.path.join(OUT, "metrics.json")
    if not os.path.exists(vp):
        raise SystemExit("no %s - look at the strips and write it first" % vp)
    verd = json.load(open(vp, encoding="utf-8"))
    met = json.load(open(mp, encoding="utf-8"))
    when = met.get("_isolation", {}).get("measured_utc", "")[:10]
    n = 0
    for style, v in sorted(verd.items()):
        p = os.path.join(STYLES, style + ".json")
        if not os.path.exists(p):
            print("  %-22s NO CARD" % style)
            continue
        card = json.load(open(p, encoding="utf-8"))
        vv = {"holds": v["holds"], "failure": v["failure"], "saw": v["saw"]}
        if v.get("tags"):
            vv["per_engine"] = {t.split("__")[-1]: _numbers(met, t) for t in v["tags"]}
        else:
            vv.update(_numbers(met, v.get("tag", style)))
        vv["measured_on"] = (
            "One 193-frame (8.04s) LTX-2.3 image-to-video clip, workflow "
            "12_ltx23_i2v_audio.json at its shipping settings, from a keyframe rendered on "
            "this style's own engine at 1280x704. Held constant across every style in the "
            "sweep: subject, keyframe seed %d, video seed %d, motion prompt, clip length. "
            "MEASURED BY RENDERING AND LOOKING, NOT PREDICTED." % (SEED, VSEED))
        vv["caveats"] = (
            "boil is NOT a style-stability number in this sweep - it tracks how much the "
            "clip moved, and the identical motion prompt produced motion from 0.345 to "
            "2.772 across styles. detail is the load-bearing number, and it too drops when "
            "the COMPOSITION changes rather than the texture. Read both against the strips."
            " n=1 clip, one subject, one seed.")
        vv["measured"] = when
        vv["tool"] = "studio/_tools/video_examples.py"
        card["works_for"] = v["works_for"]
        card["video_verdict"] = vv
        json.dump(card, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        open(p, "a").write("\n")
        print("  %-22s %-8s %s" % (style, v["holds"], v["failure"]))
        n += 1
    print("\n%d card(s) updated - works_for and video_verdict only" % n)


if __name__ == "__main__":
    main()
