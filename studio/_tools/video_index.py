#!/usr/bin/env python3
"""studio/_tools/video_index.py - collect every clip the project has rendered into one
index, and render the replicate arm that nobody has measured yet.

    python3 studio/_tools/video_index.py render     # GPU: seed replicates
    python3 studio/_tools/video_index.py measure    # metrics on the replicates
    python3 studio/_tools/video_index.py posters    # ffmpeg poster frame per clip
    python3 studio/_tools/video_index.py build      # write studio/samples/video.json
    python3 studio/_tools/video_index.py all        # posters + build

WHY THIS FILE EXISTS. Three separate sweeps have rendered 140 clips into four unrelated
directories with four unrelated metric schemas, and none of it is reachable from the app.
`build` reads all four and emits ONE index that /api/video serves and /video renders.

THE RECIPE IS READ, NOT RETYPED. Every prompt string, filter chain, seed and frame count
on the page is imported from the tool that actually produced the clip (video_examples.py,
motion_examples.py, scripts/short.py) or read out of the card the clip belongs to. Nothing
here restates a recipe from memory, because a recipe that has drifted from its generator is
worse than no recipe at all.

THE REPLICATE ARM. Every verdict in this project's video work is n=1: one keyframe seed,
one video noise seed, one clip. That is the single caveat all three sweeps flagged about
themselves. `render` re-runs the style sweep, the prompted-camera sweep and the motion
sweep at two further video noise seeds, off the IDENTICAL keyframe PNGs the originals used,
changing node 32 and nothing else. It also re-renders three clips at the ORIGINAL seed as a
determinism check - if those do not reproduce, the whole comparison is meaningless and the
page says so.
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
REPO = os.path.dirname(STUDIO)
SAMP = os.path.join(STUDIO, "samples")
COMFY = os.environ.get("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
HOST = os.environ.get("COMFY_HOST", "127.0.0.1:8188")

sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, TOOLS)

SEEDS_DIR = os.path.join(SAMP, "video_seeds")
POSTERS = os.path.join(SAMP, "_posters")
INDEX = os.path.join(SAMP, "video.json")

STAGE = "claude-generated/studio_videoseeds"
VID = (1280, 704)
FPS = 24

# The replicate seeds. Base seeds are whatever the published sweep used - 8801 for the
# style sweep (video_examples.VSEED) and 4200 for the motion lab (motion_examples.SEED) -
# and are NOT re-rendered except by the determinism check, because the published clips came
# off the identical graph and the identical save path.
STYLE_BASE, STYLE_SEEDS = 8801, [5511, 9902]
LAB_BASE, LAB_SEEDS = 4200, [7788, 2244]

# Three clips re-rendered at the seed they were first rendered at. If LTX is deterministic
# for a fixed graph these come back identical to the published files and the cross-seed
# comparison is sound; if they do not, every number in the replicate arm is noise.
REPRO = [("style", "manga_screentone", STYLE_BASE),
         ("camp", "pan_l", LAB_BASE),
         ("mot", "car_passes", LAB_BASE)]


def sh(*a, **kw):
    return subprocess.run([str(x) for x in a], capture_output=True, text=True, **kw)


def need(*d):
    for x in d:
        os.makedirs(x, exist_ok=True)


def jload(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def card(group, cid):
    return jload(os.path.join(STUDIO, group, cid + ".json"), {}) or {}


# ═══════════════════════════════════════════════════════════ the generators' own tables
# Imported, never retyped. If a sweep is re-run with a different prompt the page follows it.
def gen_tables():
    t = {"cam_prompt": {}, "stem": "", "motion": [], "kf_a": "", "kf_b": "",
         "style_motion": "", "subj_tags": "", "subj_prose": "", "neg_base": "",
         "quality": "", "style_seed": None, "style_vseed": None, "lab_seed": None,
         "style_frames": None, "lab_frames": None, "sources": []}
    try:
        import motion_examples as me
        t.update(cam_prompt=dict(me.CAM_PROMPT), stem=me.STEM,
                 motion=[list(x) for x in me.MOTION], kf_a=me.KF_A, kf_b=me.KF_B,
                 lab_seed=me.SEED, lab_frames=me.FRAMES)
        t["sources"].append("studio/_tools/motion_examples.py")
    except Exception as e:                                    # noqa: BLE001
        t["motion_import_error"] = repr(e)
    try:
        import video_examples as ve
        t.update(style_motion=ve.MOTION, subj_tags=ve.SUBJ_TAGS, subj_prose=ve.SUBJ_PROSE,
                 neg_base=ve.NEG_BASE, quality=ve.Q, style_seed=ve.SEED,
                 style_vseed=ve.VSEED, style_frames=ve.FRAMES)
        t["sources"].append("studio/_tools/video_examples.py")
    except Exception as e:                                    # noqa: BLE001
        t["video_import_error"] = repr(e)
    return t


def fx_for(cam):
    """The literal ffmpeg fragment short.py emits for this camera value, asked of short.py.

    An EMPTY STRING here is the finding, not a lookup failure: dolly_zoom, orbit and
    rack_focus have no branch, so the chain is empty and the clip passes through untouched.
    fx_chain returns a joined STRING, not a list - joining it again splits it per character.
    """
    try:
        import short                                          # noqa: E402
        v = short.fx_chain([cam], VID[0], VID[1], FPS, seed=0, length=97 / 24.0)
        return v if isinstance(v, str) else ",".join(v)
    except Exception as e:                                    # noqa: BLE001
        return "<could not ask short.py: %r>" % (e,)


def vs(matrix, row, col):
    """Pull one cell out of a pairwise MAD matrix.

    These tables are keyed name -> {other name -> mad}, so matrix[row] is a whole row and
    reading it as a scalar puts an eleven-key dict where a number belongs.
    """
    r = (matrix or {}).get(row)
    return r.get(col) if isinstance(r, dict) else r


# ═══════════════════════════════════════════════════════════════════════ render (GPU)
PENDING = []


def submit(wf):
    req = urllib.request.Request(
        "http://%s/prompt" % HOST,
        data=json.dumps({"prompt": wf, "client_id": "video_index"}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())["prompt_id"]


def wait_all(pids, label="jobs"):
    left, t0 = dict.fromkeys(pids), time.time()
    while left:
        time.sleep(8)
        for p in list(left):
            try:
                h = json.load(urllib.request.urlopen(
                    "http://%s/history/%s" % (HOST, p), timeout=30))
            except Exception:                                 # noqa: BLE001
                continue
            if h.get(p):
                del left[p]
        print("  %s: %d/%d done  %.0fs" % (label, len(pids) - len(left), len(pids),
                                           time.time() - t0), flush=True)


def load_wf(name):
    """ComfyUI returns a bare 500 with no node_errors if a prompt dict carries a
    non-node top-level key, and every workflow in this repo has `_comment`/`_notes`."""
    with open(os.path.join(REPO, "workflows", name), encoding="utf-8") as f:
        return {k: v for k, v in json.load(f).items() if not k.startswith("_")}


def i2v(kf_png, prompt, prefix, seed, frames):
    """workflow 12 exactly as short.py drives it. Only node 32 varies across a replicate."""
    from comfy import set_path as sp                          # noqa: E402
    staged = "vidx_" + os.path.basename(kf_png)
    shutil.copy(kf_png, os.path.join(COMFY, "input", staged))
    wf = load_wf("12_ltx23_i2v_audio.json")
    sp(wf, "8.inputs.image", staged)
    sp(wf, "10.inputs.text", prompt)
    sp(wf, "20.inputs.width", VID[0])
    sp(wf, "20.inputs.height", VID[1])
    sp(wf, "20.inputs.length", frames)
    sp(wf, "21.inputs.frames_number", frames)
    sp(wf, "32.inputs.noise_seed", seed)
    sp(wf, "43.inputs.filename_prefix", prefix)
    PENDING.append(submit(wf))


def render(args):
    t = gen_tables()
    need(SEEDS_DIR, os.path.join(COMFY, "input"))
    lab = os.path.join(COMFY, "output", "claude-generated", "motion-lab")
    kf_a = os.path.join(lab, "kf_a_00001_.png")

    plan = []                       # (tag, kf_png, prompt, seed, frames, arm, base_id)
    # --- arm 1: the style sweep, same keyframe PNG, new video noise seed
    styles = sorted(f[:-7] for f in os.listdir(os.path.join(SAMP, "video"))
                    if f.endswith("_kf.png"))
    for s in styles:
        kf = os.path.join(SAMP, "video", s + "_kf.png")
        for sd in STYLE_SEEDS:
            plan.append(("style__%s__v%d" % (s, sd), kf, t["style_motion"], sd,
                         t["style_frames"] or 193, "style", s))
    # --- arm 2: prompted cameras
    for cid, clause in sorted(t["cam_prompt"].items()):
        for sd in LAB_SEEDS:
            plan.append(("camp__%s__v%d" % (cid, sd), kf_a, t["stem"] + clause, sd,
                         t["lab_frames"] or 97, "camera_prompted", cid))
    # --- arm 3: the motion vocabulary
    for mid, _kind, text in t["motion"]:
        for sd in LAB_SEEDS:
            plan.append(("mot__%s__v%d" % (mid, sd), kf_a, text, sd,
                         t["lab_frames"] or 97, "motion", mid))
    # --- arm 4: determinism check at the ORIGINAL seed
    for arm, cid, sd in REPRO:
        if arm == "style":
            plan.append(("repro__style__%s__v%d" % (cid, sd),
                         os.path.join(SAMP, "video", cid + "_kf.png"),
                         t["style_motion"], sd, t["style_frames"] or 193, "repro", cid))
        elif arm == "camp":
            plan.append(("repro__camp__%s__v%d" % (cid, sd), kf_a,
                         t["stem"] + t["cam_prompt"][cid], sd, t["lab_frames"] or 97,
                         "repro", cid))
        else:
            txt = [m[2] for m in t["motion"] if m[0] == cid][0]
            plan.append(("repro__mot__%s__v%d" % (cid, sd), kf_a, txt, sd,
                         t["lab_frames"] or 97, "repro", cid))

    if args.limit:
        plan = plan[:args.limit]
    manifest = [{"tag": p[0], "kf": p[1], "prompt": p[2], "seed": p[3], "frames": p[4],
                 "arm": p[5], "base_id": p[6]} for p in plan]
    with open(os.path.join(SEEDS_DIR, "_plan.json"), "w", encoding="utf-8") as f:
        json.dump({"plan": manifest, "style_seeds": STYLE_SEEDS, "lab_seeds": LAB_SEEDS,
                   "style_base": STYLE_BASE, "lab_base": LAB_BASE,
                   "workflow": "12_ltx23_i2v_audio.json", "size": list(VID), "fps": FPS,
                   "sources": t["sources"]}, f, indent=1)
    print("plan: %d clips" % len(plan), flush=True)
    if args.dry:
        return

    # One contiguous batch: every job is workflow 12, so the 23.8GB LTXAV checkpoint loads
    # once. Submitting serially on a shared box was measured at ~22x the cost.
    for tag, kf, prompt, sd, fr, _arm, _b in plan:
        if not os.path.isfile(kf):
            print("  MISSING KEYFRAME, skipped: %s" % kf)
            continue
        i2v(kf, prompt, "%s/%s" % (STAGE, tag), sd, fr)
    print("submitted %d" % len(PENDING), flush=True)
    wait_all(PENDING, "clips")

    out = os.path.join(COMFY, "output", STAGE)
    n = 0
    for tag, *_ in plan:
        hits = sorted(glob.glob(os.path.join(out, tag + "_*.mp4")))
        if hits:
            shutil.copy(hits[-1], os.path.join(SEEDS_DIR, tag + ".mp4"))
            n += 1
    print("published %d/%d clips to %s" % (n, len(plan), SEEDS_DIR))


# ═══════════════════════════════════════════════════════════════════════ the metric
# CALLED, NOT REIMPLEMENTED. The replicate clips exist only to be compared against the
# published numbers, so they must come off the identical function. My first version of this
# looked equivalent and was not: video_examples drops frame 0 before averaging, `churn` is
# a coefficient of variation rather than a mean, `boil` divides by the amplitude and not by
# the motion, and `detail` and the octiles are relative to FRAME 0 rather than to the mean
# of the first eighth. Every one of those differences would have produced plausible numbers
# on a different scale, which is worse than no numbers at all.
NUM = r"=([-+0-9.eE]+)"


def _mean(v):
    return sum(v) / len(v) if v else 0.0


def measure_clip(mp4, kf_png=None):
    import video_examples as ve                               # noqa: E402
    return ve.measure(mp4, kf_png)


def md5(p):
    r = sh("md5sum", p)
    return r.stdout.split()[0] if r.returncode == 0 else None


def stream_md5(p):
    """MD5 of the DECODED video stream, not of the file.

    The file md5 differs between two runs that produced identical pictures, because the
    muxer writes timestamps and metadata that are not the video. Comparing files therefore
    reports 'not reproducible' for a pipeline that is in fact bit-exact.
    """
    r = sh("ffmpeg", "-v", "error", "-i", p, "-map", "0:v", "-f", "md5", "-")
    return r.stdout.strip().replace("MD5=", "") or None


def psnr(a, b):
    """inf means every decoded pixel of every frame is identical."""
    r = sh("ffmpeg", "-hide_banner", "-i", a, "-i", b, "-lavfi", "[0:v][1:v]psnr",
           "-f", "null", "-")
    m = re.search(r"average:([a-z0-9.]+)", r.stdout + r.stderr)
    return m.group(1) if m else None


def mad(a, b):
    """Mean absolute luma difference between two clips, 0-255, over the whole clip."""
    r = sh("ffmpeg", "-hide_banner", "-v", "error", "-i", a, "-i", b, "-filter_complex",
           "[0:v]scale=320:-2,format=gray[x];[1:v]scale=320:-2,format=gray[y];"
           "[x][y]blend=all_mode=difference,signalstats,"
           "metadata=print:key=lavfi.signalstats.YAVG:file=-", "-f", "null", "-")
    v = [float(m) for m in re.findall("YAVG" + NUM, r.stdout + r.stderr)]
    return round(_mean(v), 3) if v else None


def metric_parity():
    """Re-measure a PUBLISHED clip and check it reproduces the number already on record.

    Without this the replicate arm is a pile of numbers on an unverified scale. It is the
    same check in spirit as asserting a PNG scores SSIM 1.0 against itself.
    """
    met = jload(os.path.join(SAMP, "video", "metrics.json"), {}) or {}
    checks = {}
    for name in ("manga_screentone", "photorealistic"):
        p = os.path.join(SAMP, "video", name + ".mp4")
        if not (os.path.isfile(p) and name in met):
            continue
        mine, theirs = measure_clip(p), met[name]
        ok = all(abs((mine.get("full", {}).get(k) or 0)
                     - (theirs.get("full", {}).get(k) or 0)) < 1e-9
                 for k in ("motion", "churn", "boil", "detail"))
        checks[name] = {"agrees": ok, "recomputed": mine.get("full"),
                        "on_record": theirs.get("full")}
    return checks


def determinism(args=None):
    """Does re-rendering at the ORIGINAL seed reproduce the published clip?

    Judged on the DECODED video, three ways: file md5 (expected to differ - the muxer
    writes non-video bytes), decoded-stream md5, and PSNR. If the stream md5 matches and
    PSNR is inf then the pipeline is bit-exact and every cross-seed number in the replicate
    group is a seed effect and nothing else.
    """
    pub = {"style": lambda c: os.path.join(SAMP, "video", c + ".mp4"),
           "camp": lambda c: os.path.join(SAMP, "cameras", c + "_prompted.mp4"),
           "mot": lambda c: os.path.join(SAMP, "motion", c + ".mp4")}
    det = {}
    for arm, cid, sd in REPRO:
        mine = os.path.join(SEEDS_DIR, "repro__%s__%s__v%d.mp4" % (arm, cid, sd))
        theirs = pub[arm](cid)
        if not (os.path.isfile(mine) and os.path.isfile(theirs)):
            continue
        sa, sb = stream_md5(mine), stream_md5(theirs)
        det["%s/%s" % (arm, cid)] = {
            "published": theirs.replace(STUDIO, "studio"),
            "reseed": os.path.basename(mine), "seed": sd,
            "file_md5_match": md5(mine) == md5(theirs),
            "video_stream_md5_match": bool(sa) and sa == sb,
            "psnr": psnr(mine, theirs), "mad": mad(mine, theirs)}
    if args is not None:                        # run as its own subcommand
        p = os.path.join(SEEDS_DIR, "_metrics.json")
        cur = jload(p, {}) or {}
        cur["_determinism"] = det
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cur, f, indent=1)
        print(json.dumps(det, indent=1))
    return det


def measure(args):
    plan = (jload(os.path.join(SEEDS_DIR, "_plan.json")) or {}).get("plan", [])
    parity = metric_parity()
    print("METRIC PARITY vs the published numbers:")
    for k, v in parity.items():
        print("  %-18s agrees=%s" % (k, v["agrees"]))
        if not v["agrees"]:
            print("     recomputed %s\n     on record  %s" % (v["recomputed"], v["on_record"]))
    out = {"_metric_parity": parity}
    for j in plan:
        p = os.path.join(SEEDS_DIR, j["tag"] + ".mp4")
        if not os.path.isfile(p):
            continue
        m = measure_clip(p, j["kf"] if j["kf"].endswith(".png") else None)
        if m:
            m["arm"], m["base_id"], m["seed"] = j["arm"], j["base_id"], j["seed"]
            out[j["tag"]] = m
        print("  measured %s  %s" % (j["tag"], (m or {}).get("full")), flush=True)

    det = determinism()
    out["_determinism"] = det
    out["_measured_utc"] = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    with open(os.path.join(SEEDS_DIR, "_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(det, indent=1))
    print("wrote %s (%d clips)"
          % (os.path.join(SEEDS_DIR, "_metrics.json"),
             len([k for k in out if not k.startswith("_")])))


# ═══════════════════════════════════════════════════════════════════════ posters
def posters(args):
    """A poster per clip. Without one, `preload=metadata` leaves every card blank until
    the browser has fetched a header from 140 separate files."""
    need(POSTERS)
    n = skip = 0
    for mp4 in sorted(glob.glob(os.path.join(SAMP, "**", "*.mp4"), recursive=True)):
        rel = os.path.relpath(mp4, SAMP).replace(os.sep, "__")[:-4]
        dst = os.path.join(POSTERS, rel + ".jpg")
        if os.path.isfile(dst) and not args.force:
            skip += 1
            continue
        r = sh("ffmpeg", "-hide_banner", "-v", "error", "-y", "-i", mp4,
               "-vf", "select=eq(n\\,0),scale=480:-2", "-vframes", "1", "-q:v", "5", dst)
        n += r.returncode == 0
    print("posters: %d written, %d already present -> %s" % (n, skip, POSTERS))


# ═══════════════════════════════════════════════════════════════════════ the index
def url(abspath):
    return "/samples/" + os.path.relpath(abspath, SAMP).replace(os.sep, "/")


def poster_for(mp4):
    rel = os.path.relpath(mp4, SAMP).replace(os.sep, "__")[:-4]
    p = os.path.join(POSTERS, rel + ".jpg")
    return url(p) if os.path.isfile(p) else None


def clip(abspath, label=None, metrics=None, recipe=None, note=None):
    if not os.path.isfile(abspath):
        return None
    return {"label": label, "src": url(abspath), "poster": poster_for(abspath),
            "bytes": os.path.getsize(abspath), "metrics": metrics or [],
            "recipe": recipe or [], "note": note}


def M(k, v, hint=None):
    return {"k": k, "v": v, "hint": hint}


def R(k, v):
    return {"k": k, "v": v}


# ---------------------------------------------------------------- group: style
STYLE_LORE = (
    "Fifteen clips, one subject, one keyframe seed, one video noise seed, one motion "
    "prompt, one length. Only the style card varies. The library's standing prediction was "
    "that flat high-contrast idioms would survive i2v and fine grain and dot fields would "
    "boil; all nine illustration styles held for the full 8.04s, including the three named "
    "as worst cases. The axis that actually predicts survival is illustration vs "
    "photograph - and in this library engine and idiom are perfectly confounded, so that "
    "cannot be separated from animagine vs qwen. "
    "READ THE NUMBER ON A PHOTOGRAPHIC CARD WITH CARE: the seed replicates at the bottom of "
    "this page re-ran all fifteen at two more video seeds, and while the illustration "
    "styles hold to within 0.03, film_35mm ranges 0.855-0.293 and cinestill_night "
    "0.954-0.601 across seeds. The photographic verdicts here are one draw from a wide "
    "distribution; the illustration ones are stable.")


def group_style(t, seeds_m):
    d = os.path.join(SAMP, "video")
    met = jload(os.path.join(d, "metrics.json"), {}) or {}
    ver = jload(os.path.join(d, "verdicts.json"), {}) or {}
    iso = met.get("_isolation", {})
    ctl = {"anime": os.path.join(d, "_control__anime.mp4"),
           "qwen": os.path.join(d, "_control__qwen.mp4")}
    ents = []
    # `_isolation` is the run's metadata block; `_control__anime` and `_control__qwen` are
    # CLIPS and belong on the page. Skipping every underscore key drops the two controls -
    # which are the only genuinely controlled pair in the sweep - and silently removes the
    # prepared comparison that depends on them.
    for name in sorted(k for k in met if k != "_isolation"):
        mp4 = os.path.join(d, name + ".mp4")
        if not os.path.isfile(mp4):
            continue
        m = met[name]
        st = card("styles", "_control" if name.startswith("_control") else name)
        # The _control card declares engine "either" because it renders on both. The two
        # control CLIPS are each one engine, and which one is the whole point of the pair,
        # so take it from the filename rather than the card.
        eng = ("anime" if name.endswith("anime") else "qwen") if name.startswith("_control") \
            else (st.get("engine") or "anime")
        v = ver.get(name) or ver.get("_control") or {}
        base_recipe = [
            R("workflow", "workflows/12_ltx23_i2v_audio.json (the graph short.py ships on)"),
            R("keyframe engine", "%s — %s" % (eng, "animagine-xl-4.0 (danbooru tags)"
              if eng == "anime" else "Qwen-Image 2512 (prose)")),
            R("keyframe workflow", "22_anime_kf_ipadapter.json, IPAdapter weight 0"
              if eng == "anime" else "13_qwen_t2i_styled.json"),
            R("subject", t["subj_tags"] if eng == "anime" else t["subj_prose"]),
            R("style adds", (st.get("tags") if eng == "anime" else st.get("prose")) or
              "nothing — this card contributes no text on this engine"),
            R("negative", t["neg_base"] + (", " + st["negative_add"]
              if st.get("negative_add") else "")),
            R("keyframe seed", iso.get("seed")),
            R("video noise seed (node 32)", iso.get("video_seed")),
            R("motion prompt (node 10)", iso.get("motion_prompt")),
            R("size / frames / fps", "%dx%d · %d frames · %d fps = %.2fs"
              % (VID[0], VID[1], m.get("frames", 0), FPS, m.get("frames", 1) / FPS)),
            R("left at shipping defaults", json.dumps(iso.get("left_at_shipping_defaults", {}))),
        ]
        full, f4 = m.get("full", {}), m.get("first_4s", {})
        mets = [M("detail @8.0s", full.get("detail"),
                  "fine-detail amplitude at the end over the start. 1.0 = nothing lost."),
                M("detail @4.0s", f4.get("detail"), "the same over the first 97 frames only"),
                M("kf retention", m.get("kf_retention"),
                  "frame 0 detail over the keyframe's. ~1.0 on all 15, so CRF-18 preprocess "
                  "is not where style is lost."),
                M("motion", full.get("motion"), "mean low-band frame difference"),
                M("boil", full.get("boil"),
                  "DOES NOT RANK STYLE STABILITY — it tracks motion. Read detail instead.")]
        variants = [clip(mp4, "%s · seed %s" % (name, iso.get("video_seed")), mets, base_recipe)]
        c = ctl.get(eng)
        if c and not name.startswith("_control"):
            cm = met.get("_control__" + eng, {})
            variants.append(clip(c, "no-style control · same seed, same subject",
                                 [M("detail @8.0s", cm.get("full", {}).get("detail")),
                                  M("motion", cm.get("full", {}).get("motion"))],
                                 [R("style adds", "nothing — this is the control")],
                                 "The same subject and seed with no style card at all."))
        for sd in STYLE_SEEDS:
            tag = "style__%s__v%d" % (name, sd)
            sp = os.path.join(SEEDS_DIR, tag + ".mp4")
            sm = seeds_m.get(tag) or {}
            if os.path.isfile(sp):
                variants.append(clip(
                    sp, "replicate · video seed %d" % sd,
                    [M("detail @8.0s", sm.get("full", {}).get("detail")),
                     M("motion", sm.get("full", {}).get("motion"))],
                    base_recipe[:-5] + [R("video noise seed (node 32)", sd)] + base_recipe[-3:],
                    "Identical keyframe PNG and prompt; node 32 is the only change."))
        ents.append({
            "id": "style/" + name,
            # Both controls carry the same card name, so without the engine appended the
            # two cards - and the prepared comparison between them - read identically.
            "title": (("%s · %s" % (st.get("name") or "no style (control)", eng))
                      if name.startswith("_control") else (st.get("name") or name)),
            "sub": "%s · %s" % (eng, st.get("family") or "control"),
            "badges": [x for x in [eng, st.get("compose"), st.get("status")] if x],
            "headline": M("detail @8.0s", full.get("detail")),
            "octiles": m.get("detail_octiles"),
            "strips": [x for x in [
                {"src": url(os.path.join(d, name + "_strip.png")),
                 "label": "keyframe + 8 frames across the clip"}
                if os.path.isfile(os.path.join(d, name + "_strip.png")) else None,
                {"src": url(os.path.join(d, name + "_detail.png")),
                 "label": "the same 9 frames cropped at native resolution"}
                if os.path.isfile(os.path.join(d, name + "_detail.png")) else None] if x],
            "still": url(os.path.join(d, name + "_kf.png"))
            if os.path.isfile(os.path.join(d, name + "_kf.png")) else None,
            "clips": [c for c in variants if c],
            "verdict": v.get("saw"), "holds": v.get("holds"), "failure": v.get("failure"),
            "search": " ".join(str(x) for x in [name, st.get("name"), st.get("family"), eng,
                                                v.get("saw"), v.get("failure")]),
        })
    return {"id": "style", "title": "Style through video",
            "blurb": STYLE_LORE, "measure": "detail @8.0s", "entries": ents,
            "pairs": [["style/_control__anime", "style/_control__qwen",
                       "the only genuinely controlled pair in the sweep: same subject, seed, "
                       "prompt and length, differing only in which engine drew the keyframe"],
                      ["style/film_35mm", "style/cinestill_night",
                       "both qwen photographic; the one whose signature is large smooth "
                       "halation held, the one whose signature is per-pixel grain did not"],
                      ["style/manga_screentone", "style/photorealistic",
                       "the style predicted to fail worst against the one that actually did"]]}


# ---------------------------------------------------------------- group: camera
CAM_LORE = (
    "Two tiers, rendered off one keyframe built so a move reads as a THING entering frame: "
    "a red phone box on the left edge, a yellow taxi on the right, a clock tower at top, "
    "wet asphalt at the bottom. POST is short.py's ffmpeg crop/zoompan over a finished "
    "clip. PROMPTED asks LTX for the move in words. dolly_zoom, orbit and rack_focus have "
    "no branch in short.py's fx_chain, so their post clips are byte-identical to static.")


def group_camera(t, seeds_m):
    d = os.path.join(SAMP, "cameras")
    mm = jload(os.path.join(SAMP, "motion", "_measurements.json"), {}) or {}
    post, prompted = mm.get("cameras_post_clip", {}), mm.get("cameras_prompted", {})
    mad_post = mm.get("mad_cameras_post_clip", {})
    ents = []
    for cid in sorted(set(list(post) + list(prompted))):
        cd = card("cameras", cid)
        chain = fx_for(cid)
        p, q = post.get(cid, {}), prompted.get(cid, {})
        post_recipe = [
            R("tier", "post — ffmpeg over a finished LTX clip (scripts/short.py fx_chain)"),
            R("filter chain", chain or
              "EMPTY — short.py has no branch for this value, so the clip passes through "
              "unchanged and is byte-identical to static"),
            R("input clip", "one LTX i2v clip off keyframe A, seed %s" % mm.get("seed")),
            R("size / frames", "%dx%d · %d frames at %d fps"
              % (VID[0], VID[1], mm.get("frames", 97), FPS)),
            R("encode", "libx264 crf 18, audio dropped (-an)")]
        prompt_recipe = [
            R("tier", "prompted — the move asked of LTX in the video prompt"),
            R("workflow", "workflows/12_ltx23_i2v_audio.json"),
            R("keyframe", "shared keyframe A (qwen, one seed) — see the recipe below"),
            R("keyframe prompt", t["kf_a"]),
            R("video prompt (node 10)", t["stem"] + t["cam_prompt"].get(cid, "")),
            R("video noise seed (node 32)", mm.get("seed")),
            R("size / frames / fps", "%dx%d · %d frames · %d fps"
              % (VID[0], VID[1], mm.get("frames", 97), FPS))]
        cl = []
        cl.append(clip(os.path.join(d, cid + ".mp4"), "post — ffmpeg",
                       [M("dx left/right", "%+g / %+g px" % (p.get("dx_left", 0), p.get("dx_right", 0))),
                        M("dy top/bottom", "%+g / %+g px" % (p.get("dy_top", 0), p.get("dy_bottom", 0))),
                        M("MAD vs static", vs(mad_post, cid, "static"),
                          "mean absolute luma difference against static.mp4; 0.00 means no-op"),
                        M("reading", p.get("verdict"))],
                       post_recipe))
        cl.append(clip(os.path.join(d, cid + "_prompted.mp4"), "prompted — asked of LTX",
                       [M("dx left/right", "%+g / %+g px" % (q.get("dx_left", 0), q.get("dx_right", 0))),
                        M("dy top/bottom", "%+g / %+g px" % (q.get("dy_top", 0), q.get("dy_bottom", 0))),
                        M("activity", q.get("activity"),
                          "mean frame-to-frame luma change; the empty-prompt floor is 1.01"),
                        M("reading", q.get("verdict"))],
                       prompt_recipe))
        for sd in LAB_SEEDS:
            tag = "camp__%s__v%d" % (cid, sd)
            sp_ = os.path.join(SEEDS_DIR, tag + ".mp4")
            sm = seeds_m.get(tag) or {}
            if os.path.isfile(sp_):
                cl.append(clip(sp_, "prompted replicate · seed %d" % sd,
                               [M("motion", sm.get("full", {}).get("motion")),
                                M("detail", sm.get("full", {}).get("detail"))],
                               prompt_recipe[:-2] + [R("video noise seed (node 32)", sd),
                                                     prompt_recipe[-1]],
                               "Same keyframe and prompt; node 32 is the only change."))
        noop = vs(mad_post, cid, "static") == 0.0 and cid != "static"
        ents.append({
            "id": "camera/" + cid, "title": cid, "sub": cd.get("desc", ""),
            "badges": [x for x in [cd.get("status"), "no-op in post" if noop else None] if x],
            "headline": M("MAD vs static (post)", vs(mad_post, cid, "static")),
            "strips": [], "still": None,
            "clips": [c for c in cl if c],
            "verdict": cd.get("verdict"),
            "search": " ".join(str(x) for x in [cid, cd.get("desc"), cd.get("verdict")]),
        })
    return {"id": "camera", "title": "Camera moves", "blurb": CAM_LORE,
            "measure": "MAD vs static", "entries": ents,
            "pairs": [["camera/pan_l", "camera/pan_r",
                       "the pair the whole library exists to distinguish: content moves "
                       "right 100px vs left 100px, MAD 35.43 apart"],
                      ["camera/tilt_u", "camera/tilt_d",
                       "tilts are inherently half as strong as pans (56px of travel vs 100) "
                       "because the vertical crop margin is smaller"],
                      ["camera/push", "camera/pull",
                       "10% in vs 10% out — and neither zooms about the frame centre"],
                      ["camera/static", "camera/orbit",
                       "static is the reference at 0.00; orbit's POST clip is byte-identical "
                       "to it, while its PROMPTED clip is the only real 3D move in the project"]]}


# ---------------------------------------------------------------- group: motion
MOT_LORE = (
    "`motion` is the only string the video model reads, and it had no card library at all. "
    "Fifteen prompts, one keyframe, one seed. The empty-prompt floor is activity 1.01. The "
    "rule is sharper than nouns-vs-adjectives: LARGE MOVING OBJECTS land and everything "
    "else does not. compile.py assigns the literal string 'Slow deliberate movement only.' "
    "to every beat of every compiled film; it measures 1.11 against a floor of 1.01.")


def group_motion(t, seeds_m):
    d = os.path.join(SAMP, "motion")
    mm = jload(os.path.join(d, "_measurements.json"), {}) or {}
    mo = mm.get("motion", {})
    texts = {m[0]: (m[1], m[2]) for m in t["motion"]}
    floor = (mo.get("ctl_empty") or {}).get("activity")
    ents = []
    for mid in sorted(mo):
        kind, text = texts.get(mid, ("?", ""))
        m = mo[mid]
        rec = [R("workflow", "workflows/12_ltx23_i2v_audio.json"),
               R("keyframe", "shared keyframe A (qwen)"),
               R("keyframe prompt", t["kf_a"]),
               R("video prompt (node 10)", text if text else "(empty string)"),
               R("prompt kind", kind),
               R("video noise seed (node 32)", mm.get("seed")),
               R("size / frames / fps", "%dx%d · %d frames · %d fps"
                 % (VID[0], VID[1], mm.get("frames", 97), FPS))]
        cl = [clip(os.path.join(d, mid + ".mp4"), "seed %s" % mm.get("seed"),
                   [M("activity", m.get("activity"),
                      "mean frame-to-frame luma change. Empty-prompt floor %s." % floor),
                    M("vs floor", round((m.get("activity") or 0) - (floor or 0), 2)),
                    M("reading", m.get("verdict"))], rec)]
        if mid != "ctl_empty":
            ce = mo.get("ctl_empty", {})
            cl.append(clip(os.path.join(d, "ctl_empty.mp4"), "the empty-prompt control",
                           [M("activity", ce.get("activity"))],
                           [R("video prompt (node 10)", "(empty string)")],
                           "Same keyframe and seed with no motion prompt at all."))
        for sd in LAB_SEEDS:
            tag = "mot__%s__v%d" % (mid, sd)
            sp_ = os.path.join(SEEDS_DIR, tag + ".mp4")
            sm = seeds_m.get(tag) or {}
            if os.path.isfile(sp_):
                cl.append(clip(sp_, "replicate · seed %d" % sd,
                               [M("motion", sm.get("full", {}).get("motion")),
                                M("detail", sm.get("full", {}).get("detail"))],
                               rec[:-2] + [R("video noise seed (node 32)", sd), rec[-1]],
                               "Same keyframe and prompt; node 32 is the only change."))
        ents.append({
            "id": "motion/" + mid, "title": mid, "sub": text or "(empty prompt)",
            "badges": [kind], "headline": M("activity", m.get("activity")),
            "strips": [], "still": None, "clips": [c for c in cl if c],
            "verdict": None,
            "search": " ".join(str(x) for x in [mid, kind, text, m.get("verdict")]),
        })
    return {"id": "motion", "title": "Motion — the video prompt", "blurb": MOT_LORE,
            "measure": "activity", "entries": ents,
            "pairs": [["motion/crowd_walks", "motion/ctl_compiler_default",
                       "the best result in the sweep (4.13) against the string every "
                       "compiled beat actually receives (1.11, floor 1.01)"],
                      ["motion/car_passes", "motion/adj_dynamic",
                       "a named large moving object against the adjective for the same idea"],
                      ["motion/rain_begins", "motion/ctl_empty",
                       "a noun naming fine atmospheric texture against no prompt at all"]]}


# ---------------------------------------------------------------- group: transition
TR_LORE = (
    "Rendered between two REAL generated clips for the first time; every previous sample "
    "was ffmpeg over a still. cut, j_cut, l_cut, match_cut and smash share one MD5 — "
    "correct, since those four differ only in audio or authoring intent, but it means five "
    "cards look identical here.")


def group_transition(t, seeds_m):
    d = os.path.join(SAMP, "transitions")
    mm = jload(os.path.join(SAMP, "motion", "_measurements.json"), {}) or {}
    tr, mad_tr = mm.get("transitions", {}), mm.get("mad_transitions", {})
    ents = []
    for tid in sorted(tr):
        cd, m = card("transitions", tid), tr[tid]
        rec = [R("tier", m.get("tier", "")),
               R("xfade filter", cd.get("filter") or
                 "none — a hard switch, or an audio/authoring-only card"),
               R("duration", "%s frames at %d fps" % (cd.get("frames"), FPS)),
               R("audio_lead / audio_drop", "%s / %s"
                 % (cd.get("audio_lead"), cd.get("audio_drop"))),
               R("A and B", "two real LTX clips off keyframes A and B, seed %s"
                 % mm.get("seed")),
               R("encode", "libx264 crf 18, audio dropped (-an)")]
        ents.append({
            "id": "transition/" + tid, "title": tid, "sub": cd.get("desc", ""),
            "badges": [cd.get("status")],
            "headline": M("MAD vs cut", vs(mad_tr, tid, "cut")),
            "luma": m.get("luma_curve"),
            "strips": [], "still": None,
            "clips": [c for c in [clip(os.path.join(d, tid + ".mp4"), tid,
                      [M("MAD vs cut", vs(mad_tr, tid, "cut"),
                         "0.00 means picture-identical to a hard cut"),
                       M("luma min", m.get("luma_min")), M("luma max", m.get("luma_max"))],
                      rec)] if c],
            "verdict": cd.get("verdict"),
            "search": " ".join(str(x) for x in [tid, cd.get("desc"), cd.get("verdict")]),
        })
    return {"id": "transition", "title": "Transitions", "blurb": TR_LORE,
            "measure": "MAD vs cut", "entries": ents,
            "pairs": [["transition/whip_pan", "transition/wipe_l",
                       "the closest non-identical pair in the library, MAD 5.31 apart — and "
                       "whip_pan's card says 'fast blur wipe' when hlslice has no blur"],
                      ["transition/fade_black", "transition/fade_white",
                       "one touches true 0.0 luma, the other true 255.0"],
                      ["transition/cut", "transition/smash",
                       "same MD5, MAD exactly 0.00 — they differ only in audio and intent"]]}


# ---------------------------------------------------------------- group: pacing
def group_pacing(t, seeds_m):
    mm = jload(os.path.join(SAMP, "motion", "_measurements.json"), {}) or {}
    pa = mm.get("pacing", {})
    ents = []
    for pid in sorted(pa, key=lambda k: pa[k].get("mean_shot", 0)):
        m = pa[pid]
        src = os.path.join(SAMP, "motion", "pacing_%s.mp4" % pid)
        legacy = os.path.join(SAMP, "pacing", pid + ".mp4")
        if not os.path.isfile(src):
            src, legacy = legacy, None
        rec = [R("construction", "make_samples.py's cut-length formula, 0.55 * scale with a "
                                 "rhythm ramp, applied over real generated clips"),
               R("scale", m.get("scale")), R("rhythm", m.get("rhythm")),
               R("shot lengths (s)", ", ".join(str(x) for x in m.get("shot_lengths", []))),
               R("caveat", "this is NOT the shipping pacing path — short.py and compile.py "
                           "drive pacing through scene_templates._scale and beat.intensity, "
                           "which was never executed")]
        ents.append({
            "id": "pacing/" + pid, "title": pid,
            "sub": "%s shots in %.2fs, mean %.2fs" % (m.get("n_shots"), m.get("secs", 0),
                                                      m.get("mean_shot", 0)),
            "badges": [m.get("rhythm")], "headline": M("mean shot", m.get("mean_shot")),
            "strips": [], "still": None,
            "clips": [c for c in [
                clip(src, "cut over real generated clips",
                     [M("mean shot", "%.2fs" % m.get("mean_shot", 0)),
                      M("shots", m.get("n_shots")), M("length", "%.2fs" % m.get("secs", 0))],
                     rec),
                clip(legacy, "the older sample it replaced",
                     [], [R("construction", "make_samples.py over a STILL with ffmpeg "
                                            "-loop 1 — no video model was involved")],
                     "Kept so the page accounts for every mp4 in the tree. This is what a "
                     "pacing sample looked like before any of it went through a model.")
                if legacy else None] if c],
            "verdict": None, "search": pid + " pacing " + str(m.get("rhythm")),
        })
    return {"id": "pacing", "title": "Pacing", "measure": "mean shot",
            "blurb": "Cut rhythm over real clips: frantic 0.19s to contemplative 0.92s. "
                     "Arithmetic on cut boundaries, not a model property.",
            "entries": ents,
            "pairs": [["pacing/frantic", "pacing/contemplative",
                       "the two ends of the library, 0.19s against 0.92s"]]}


# ---------------------------------------------------------------- group: engines
ENG_LORE = (
    "LTX-2.3 against Wan 2.2 on the same keyframe, same seed, same negative — short.py "
    "sets node 11 on neither graph, so comparing as-shipped would have measured that bug "
    "instead of the engines. Frame-0 fidelity is a wash and flips with content. The real, "
    "reproducible difference is that LTX applies an unrequested push-in and Wan does not, "
    "that Wan holds fine detail and faces better, and that LTX obeys 'Slow deliberate "
    "movement only.' while Wan largely ignores it. Recommendation on record: keep LTX as "
    "the default, add Wan per-beat.")


# Each manifest is one experimental arm, and the arm decides what a card compares. Pairing
# on the id string alone loses clips: the main arm's LTX member is `kfA__ltx_distill05` and
# its Wan member is `kfA__wan_lightx2v`, which no substitution rule relates. Every result
# lands in exactly one card, and every card is a side-by-side of the thing that varied.
ENG_ARMS = [
    ("bigres", "shipping resolution — 1280x704, the size short.py actually renders",
     lambda r: r["kf"], ["ltx", "wan"]),
    ("bigseeds", "seed spread at shipping resolution",
     lambda r: "%s · seed %s" % (r["kf"], r["seed"]), ["ltx", "wan"]),
    ("main", "both engines at 896x512, with the LTX distill LoRA swept",
     lambda r: r["kf"], ["ltx_distill05", "ltx_distill10", "ltx_nodistill30",
                         "wan_lightx2v"]),
    ("prodprompt", "the production prompt — compile.py's literal "
                   "'Slow deliberate movement only.'",
     lambda r: "%s · seed %s" % (r["kf"], r["seed"]), ["ltx", "wan"]),
    ("seeds", "seed spread at 896x512",
     lambda r: "%s · seed %s" % (r["kf"], r["seed"]), ["ltx", "wan"]),
    ("idlora", "the ID LoRA as a drop-in, off / 0.5 / 1.0",
     lambda r: r["kf"], ["id_off", "id_050", "id_100"]),
    ("transition", "first/last-frame conditioning, with and without the transition LoRA",
     lambda r: r["kf"], ["tr_off", "tr_100"]),
]
ENG_LABEL = {"ltx": "LTX-2.3", "wan": "Wan 2.2", "ltx_distill05": "LTX · distill 0.5",
             "ltx_distill10": "LTX · distill 1.0",
             "ltx_nodistill30": "LTX · no distill, 30 steps",
             "wan_lightx2v": "Wan 2.2 · lightx2v", "id_off": "ID LoRA off",
             "id_050": "ID LoRA 0.5", "id_100": "ID LoRA 1.0",
             "tr_off": "transition LoRA off", "tr_100": "transition LoRA 1.0"}


def group_engine(t, seeds_m):
    d = os.path.join(SAMP, "video_engines")
    res = jload(os.path.join(d, "results.json"), []) or []
    byid = {r["id"]: r for r in res}

    def mk_clip(r, label):
        f = os.path.join(d, "clips", os.path.basename(r["file"]))
        n8 = r.get("t8") or {}
        return clip(f, label, [
            M("frame-0 SSIM vs keyframe", r.get("kf_ssim_f0"),
              "the measurement ceiling — the keyframe through h264 alone — is 0.931-0.987, "
              "so this is a wash between the engines and flips with content"),
            M("zoom estimate", r.get("zoom_est"),
              "argmax SSIM over a scale sweep of the keyframe against the final frame. "
              "1.000 = no unrequested push-in. This is the number that separates the "
              "engines, and it assumes the drift is a centred zoom."),
            M("detail vs keyframe", r.get("detail_kf")),
            M("face SSIM (frame 0 / last)", "%s / %s" % (r.get("face_ssim_f0"),
                                                         r.get("face_ssim_last"))
              if r.get("face_ssim_last") is not None else None,
              "a hand-placed face crop — a global SSIM cannot see a face at 14% of the "
              "pixels. Defined in 896x512 coordinates, so it is None at 1280x704."),
            M("palette drift", r.get("pal_drift"),
              "never calibrated against a known-bad case: no clip exists where the palette "
              "demonstrably left"),
            M("motion", n8.get("motion")), M("boil", n8.get("boil")),
            M("render", "%.1fs%s" % (r["secs"], " (cold)" if r.get("cold") else "")
              if r.get("secs") else None)],
            [R("engine", "LTX-2.3 22b fp8 — workflows/12_ltx23_i2v_audio.json, 24 fps, "
                         "audio generated in-pass" if r["engine"] == "ltx"
               else "Wan 2.2 i2v — workflows/04_wan22_i2v_turbo.json, parameterised in "
                    "memory by video_engines.py, 16 fps, NO audio"
               if r["engine"] == "wan"
               else "LTX-2.3 first/last-frame graph, built inside video_engines.py from "
                    "ComfyUI's video_ltx2_3_flf2v.json template"),
             R("keyframe", r.get("kf")), R("config", r.get("cfg")),
             R("noise seed", r.get("seed")),
             R("negative", "set EXPLICITLY and identically on both engines — short.py sets "
                           "node 11 on neither graph, so comparing as-shipped would have "
                           "measured that bug instead of the engines"),
             R("cold start", r.get("cold"))])

    ents, seen = [], set()
    for arm, blurb, keyfn, order in ENG_ARMS:
        man = jload(os.path.join(d, "manifest_%s.json" % arm), []) or []
        cards_ = {}
        for j in man:
            r = byid.get(j["id"])
            if not r or r.get("error"):
                continue
            cards_.setdefault(keyfn(r), []).append(r)
            seen.add(r["id"])
        for key, rs in sorted(cards_.items()):
            def rank(r):
                for i, o in enumerate(order):
                    if r["id"].endswith("__" + o) or r["id"].endswith("_" + o):
                        return i
                return len(order)
            rs.sort(key=rank)
            cl = []
            for r in rs:
                suffix = r["id"].split("__")[-1]
                lab = ENG_LABEL.get(suffix)
                if not lab:
                    lab = ENG_LABEL.get(r["engine"], r["engine"])
                cl.append(mk_clip(r, lab))
            kfp = os.path.join(d, "keyframes", rs[0]["kf"] + ".png")
            strips = [{"src": url(os.path.join(d, "strips", r["id"] + ".png")),
                       "label": "%s — frames across the clip" % r["id"]}
                      for r in rs
                      if os.path.isfile(os.path.join(d, "strips", r["id"] + ".png"))]
            ents.append({
                "id": "engine/%s/%s" % (arm, key.replace(" · ", "_").replace(" ", "")),
                "title": key, "sub": blurb, "badges": [arm, "%d-up" % len(cl)],
                "headline": M("zoom estimate", " vs ".join(
                    str(r.get("zoom_est")) for r in rs)),
                "strips": strips,
                "still": url(kfp) if os.path.isfile(kfp) else None,
                "clips": [c for c in cl if c], "verdict": None,
                "search": " ".join(str(x) for x in [arm, key, blurb] +
                                   [r["id"] for r in rs]),
            })
    orphan = [r for r in res if r["id"] not in seen and not r.get("error")]
    for r in orphan:
        ents.append({"id": "engine/orphan/" + r["id"], "title": r["id"],
                     "sub": "not listed in any manifest", "badges": ["unpaired"],
                     "headline": M("zoom estimate", r.get("zoom_est")), "strips": [],
                     "still": None, "clips": [c for c in [mk_clip(r, r["engine"])] if c],
                     "verdict": None, "search": r["id"]})
    return {"id": "engine", "title": "Engine comparison — LTX vs Wan", "blurb": ENG_LORE,
            "measure": "zoom estimate", "entries": ents,
            "pairs": [["engine/bigres/kfAbig", "engine/bigres/kfCbig",
                       "shipping resolution. Frame-0 fidelity flips direction between these "
                       "two keyframes, which is why the headline claim is a wash"],
                      ["engine/prodprompt/kfAslow_seed1234",
                       "engine/prodprompt/kfCslow_seed1234",
                       "the production prompt, where LTX obeys 'slow' and Wan does not — "
                       "the single test that decided the recommendation"],
                      ["engine/main/kfA", "engine/main/kfB",
                       "the distill sweep: 0.5 against 1.0 against no LoRA at 30 steps. "
                       "LORAS.md says accelerators run at 'exactly 1.0'; at 1.0 kfB grows "
                       "orange particle blobs present in neither the keyframe nor the 0.5 "
                       "render"]]}


# ---------------------------------------------------------------- group: replicates
REP_LORE = (
    "Every verdict above was n=1: one keyframe seed, one video noise seed, one clip. This "
    "arm re-runs the style, prompted-camera and motion sweeps at two further video noise "
    "seeds off the IDENTICAL keyframe PNGs, changing node 32 and nothing else. "
    "FIRST: LTX i2v is bit-exact. Three clips re-rendered at their original seed come back "
    "with a matching decoded-stream md5 and PSNR inf against the published file, so every "
    "difference below is a seed effect and nothing else. "
    "SECOND, and this is the result that matters: reproducibility is not uniform. Across "
    "three seeds the ILLUSTRATION styles barely move — pixel_art 0.008, pointillism 0.011, "
    "silhouette_poster 0.021, manga_screentone 0.032 of spread in detail@8s — while the "
    "PHOTOGRAPHIC ones swing wildly: film_35mm 0.855 to 0.293, cinestill_night 0.954 to "
    "0.601, the qwen control 0.909 to 0.478. So the n=1 verdicts on illustration styles are "
    "safe and the n=1 verdicts on photographic styles are not; the ones on record happened "
    "to catch a good seed. "
    "THIRD: the motion result reproduces cleanly. Scored on video_examples' `motion` metric "
    "- NOT on the `activity` number the published motion ranking uses, which is a different "
    "construction and not comparable figure-for-figure - every adjective, every control and "
    "every fine-texture noun sits in a tight 0.37-0.61 band with the empty prompt at both "
    "new seeds, and only the large moving objects rise above it (1.25-4.12). compile.py's "
    "'Slow deliberate movement only.' lands at 0.383 and 0.425, inside the do-nothing band "
    "both times. The cameras split the same way: the six moves that work read 3.9-8.3 while "
    "handheld (0.40, 0.39) and rack_focus (0.49, 0.40) sit at or below the static floor "
    "(0.43, 0.46) at both seeds, push (0.44, 0.54) is inside its noise, and pull (0.81, "
    "1.35) rises a little above it but stays an order of magnitude below any real move.")


def group_seeds(t, seeds_m):
    plan = (jload(os.path.join(SEEDS_DIR, "_plan.json")) or {}).get("plan", [])
    det = seeds_m.get("_determinism", {})
    # A determinism clip belongs on the card of the sweep it reproduces, not on a card of
    # its own - the whole point of it is to sit next to the clips it validates.
    SUB = {"style": "style", "camp": "camera_prompted", "mot": "motion"}
    byarm = {}
    for j in plan:
        p = os.path.join(SEEDS_DIR, j["tag"] + ".mp4")
        if not os.path.isfile(p):
            continue
        arm = j["arm"]
        if arm == "repro":
            arm = SUB.get(j["tag"].split("__")[1], "repro")
            j = dict(j, repro=True)
        byarm.setdefault((arm, j["base_id"]), []).append(j)
    pub = {"style": lambda c: os.path.join(SAMP, "video", c + ".mp4"),
           "camera_prompted": lambda c: os.path.join(SAMP, "cameras", c + "_prompted.mp4"),
           "motion": lambda c: os.path.join(SAMP, "motion", c + ".mp4"),
           "repro": lambda c: None}
    ents = []
    for (arm, base), js in sorted(byarm.items()):
        cl = []
        base_mp4 = pub.get(arm, lambda c: None)(base)
        if base_mp4 and os.path.isfile(base_mp4):
            cl.append(clip(base_mp4, "published · the seed everything was judged on",
                           [], [R("note", "the original published clip, unchanged")]))
        for j in sorted(js, key=lambda x: (not x.get("repro"), x["seed"])):
            m = seeds_m.get(j["tag"]) or {}
            f = m.get("full", {})
            cl.append(clip(os.path.join(SEEDS_DIR, j["tag"] + ".mp4"),
                           ("re-rendered at the ORIGINAL seed %d" % j["seed"])
                           if j.get("repro") else "seed %d" % j["seed"],
                           [M("motion", f.get("motion")), M("detail", f.get("detail")),
                            M("boil", f.get("boil"))],
                           [R("workflow", "workflows/12_ltx23_i2v_audio.json"),
                            R("keyframe PNG", "the identical file the published clip used"),
                            R("video prompt (node 10)", j["prompt"] or "(empty string)"),
                            R("video noise seed (node 32)", j["seed"]),
                            R("frames", j["frames"]),
                            R("everything else", "unchanged from the published run")],
                           "The determinism check: same graph, same seed as the published "
                           "clip. If this is not identical to it, nothing else on this card "
                           "can be read as a seed effect." if j.get("repro") else None))
        dkey = {"style": "style/", "camera_prompted": "camp/", "motion": "mot/"}.get(arm, "")
        dd = det.get(dkey + base)
        verdict = None
        if dd:
            exact = dd.get("video_stream_md5_match") and dd.get("psnr") == "inf"
            verdict = (
                "DETERMINISM CHECK. This card's sweep was re-rendered at its ORIGINAL seed "
                "%s off the same graph. Decoded video stream md5 %s; PSNR against the "
                "published clip %s; mean absolute luma difference %s. The FILE md5 %s — "
                "expected, because the muxer writes timestamps and metadata that are not "
                "the picture. %s"
                % (dd.get("seed"),
                   "MATCHES" if dd.get("video_stream_md5_match") else "does NOT match",
                   dd.get("psnr"), dd.get("mad"),
                   "matches too" if dd.get("file_md5_match") else "differs",
                   "So LTX i2v is bit-exact for a fixed graph and seed, and every "
                   "difference between the seeds on this card is a seed effect and nothing "
                   "else." if exact else
                   "So the picture is NOT reproducible here, and the differences between "
                   "seeds on this card are confounded with run-to-run noise."))
        ents.append({
            "id": "seeds/%s/%s" % (arm, base), "title": base,
            "sub": "%s · %d clips across %d video seeds" % (arm, len(cl), len(js)),
            "badges": [arm, "replicate"] + (["determinism check"]
                                            if any(j.get("repro") for j in js) else []),
            "headline": M("video seeds", ", ".join(str(j["seed"]) for j in sorted(
                js, key=lambda x: x["seed"]))),
            "strips": [], "still": None, "clips": [c for c in cl if c],
            "verdict": verdict,
            "search": "%s %s replicate seed reproducible" % (arm, base),
        })
    return {"id": "seeds", "title": "Seed replicates — is any of it reproducible?",
            "blurb": REP_LORE, "measure": "video seeds", "entries": ents, "pairs": [],
            "determinism": det}


BUILDERS = [group_style, group_camera, group_motion, group_transition, group_pacing,
            group_engine, group_seeds]

# Sweep-wide strips and shared keyframes. These are real artifacts sitting in the samples
# tree that no page has ever shown, and several of them carry the whole comparison in one
# picture - the eleven prompted camera moves in a single grid, for instance.
GROUP_ASSETS = {
    "camera": [("cameras/_strip_post_still.png",
                "POST tier over the still keyframe — all eleven moves"),
               ("cameras/_strip_post_clip.png",
                "POST tier over a real generated clip — all eleven moves"),
               ("cameras/_strip_prompted.png",
                "PROMPTED — the same eleven moves asked of LTX in words"),
               ("motion/_kf_a.jpg",
                "keyframe A — built so a pan or tilt reads as a THING entering frame: "
                "phone box left, taxi right, clock tower top, wet asphalt bottom")],
    "motion": [("motion/_strip_motion.png",
                "the fifteen motion prompts, one keyframe, one seed"),
               ("motion/_kf_a.jpg", "keyframe A — the shared input to every motion clip")],
    "transition": [("transitions/_strip.png", "the twelve transitions"),
                   ("motion/_kf_a.jpg", "keyframe A — the outgoing shot"),
                   ("motion/_kf_b.jpg", "keyframe B — the incoming shot")],
    "pacing": [("motion/_strip_pacing.png", "the seven pacing rhythms")],
}


def build(args):
    t = gen_tables()
    seeds_m = jload(os.path.join(SEEDS_DIR, "_metrics.json"), {}) or {}
    groups, missing = [], []
    for fn in BUILDERS:
        try:
            g = fn(t, seeds_m)
        except Exception as e:                                # noqa: BLE001
            import traceback
            groups.append({"id": fn.__name__, "title": fn.__name__, "error": repr(e),
                           "trace": traceback.format_exc()[-2000:], "entries": [],
                           "pairs": [], "blurb": ""})
            continue
        g["assets"] = [{"src": "/samples/" + rel, "label": lab}
                       for rel, lab in GROUP_ASSETS.get(g["id"], [])
                       if os.path.isfile(os.path.join(SAMP, rel))]
        if g["entries"]:
            groups.append(g)
    # every src in the index must exist on disk
    n_clips = 0
    for g in groups:
        for e in g.get("entries", []):
            for c in e.get("clips", []):
                n_clips += 1
                fp = os.path.join(SAMP, c["src"][len("/samples/"):])
                if not os.path.isfile(fp):
                    missing.append(c["src"])
            for s in e.get("strips", []) + ([{"src": e["still"]}] if e.get("still") else []):
                fp = os.path.join(SAMP, s["src"][len("/samples/"):])
                if not os.path.isfile(fp):
                    missing.append(s["src"])
        for s in g.get("assets", []):
            if not os.path.isfile(os.path.join(SAMP, s["src"][len("/samples/"):])):
                missing.append(s["src"])
    doc = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
           "clips": n_clips, "groups": groups, "missing": missing,
           "recipe_sources": t.get("sources", []),
           "notes": [k for k in ("motion_import_error", "video_import_error") if k in t]}
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    print("wrote %s" % INDEX)
    print("  groups %d  entries %d  clips %d  missing-on-disk %d"
          % (len(groups), sum(len(g.get("entries", [])) for g in groups), n_clips,
             len(missing)))
    for g in groups:
        if g.get("error"):
            print("  GROUP FAILED %s: %s" % (g["id"], g["error"]))
    for m in missing[:20]:
        print("  MISSING %s" % m)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render"); r.add_argument("--dry", action="store_true")
    r.add_argument("--limit", type=int, default=0); r.set_defaults(fn=render)
    sub.add_parser("measure").set_defaults(fn=measure)
    sub.add_parser("determinism").set_defaults(fn=determinism)
    p = sub.add_parser("posters"); p.add_argument("--force", action="store_true")
    p.set_defaults(fn=posters)
    sub.add_parser("build").set_defaults(fn=build)
    a = sub.add_parser("all"); a.add_argument("--force", action="store_true")
    a.set_defaults(fn=lambda x: (posters(x), build(x)))
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
