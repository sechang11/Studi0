#!/usr/bin/env python3
"""video_engine_ab.py - A/B HunyuanVideo 1.5 against LTX-2.3 on this project's own material.

The video layer runs entirely on LTX-2.3. Three HunyuanVideo 1.5 models (720p t2v, 720p
i2v, 1080p SR distill) have sat on the disk unused since 2026-07-29. This tool decides
whether that is a mistake, using the two things this project already knows to care about:

  KEYFRAME FIDELITY   does frame 1 still look like the image you fed it
  TEMPORAL STABILITY  does it boil

WHY THE CONTROL ARM IS FREE. studio/_tools/motion_examples.py stage lib-cards rendered
the whole MOTIONS library through 12_ltx23_i2v_audio.json off ONE keyframe
(studio/samples/motion_lib/_keyframe.png) at 1280x704, length 97, seeds 7701/7702/7703.
Those clips are still on disk. So the LTX arm needs no GPU time and - more importantly -
it is not a re-creation of the app, it IS the app: same workflow file, same settings,
same seed. This tool renders only the Hunyuan arm and holds everything else fixed.

  keyframe   studio/samples/motion_lib/_keyframe.png     (identical, staged to input/)
  prompt     read from motion_lib/manifest.json          (identical, per card)
  length     97 frames @ 24fps = 4.04s                   (identical; LTX 8n+1, Hunyuan 4n+1)
  size       1280x704 = epic.VID["16:9-hd"]              (identical)
  seed       7701                                        (identical integer)

The one thing that CANNOT be held fixed is the sampler: LTX is cfg-distilled at cfg 1.0 on
an 8-step ManualSigmas schedule, Hunyuan runs cfg 6.0 for 20 steps with a live negative
branch. There is no seed-parity between two different schedulers - identical integers do
not mean identical noise. This is an engine comparison, not a noise comparison, and that
limit is reported rather than papered over.

METRICS. motion and churn come from scripts/analyze_shots.py - the SHIPPED module, whose
YDIF scientific-notation bug is fixed there, so it is imported rather than reimplemented.
Everything else is ffmpeg:

  kf_ssim / kf_psnr   frame 1 of the clip vs the input keyframe. THE fidelity number.
  drift_ssim          last frame vs first frame. Low = the subject decayed or left.
  motion              mean frame-to-frame luma difference   (analyze_shots.motion)
  churn               stdev of that difference              (analyze_shots.motion)
  boil                churn / motion. Normalised instability: real movement is steady,
                      hallucinated movement thrashes. Comparing raw churn across engines
                      is unfair to whichever one moves more, so divide it out.
  frozen              seconds of literally static frames    (analyze_shots.frozen_seconds)

NO METRIC HERE DECIDES ANYTHING. This project once ranked a clip best in sweep while the
subject had her face hidden and her eyes shut. The strips stage exists so the numbers get
overruled by looking.

USAGE
    python3 studio/_tools/video_engine_ab.py render          # Hunyuan i2v arm
    python3 studio/_tools/video_engine_ab.py render --sr     # ... with the 1080p SR stage
    python3 studio/_tools/video_engine_ab.py t2v             # text-to-video probe
    python3 studio/_tools/video_engine_ab.py measure         # metrics for both arms
    python3 studio/_tools/video_engine_ab.py strips          # side-by-side frame strips
    python3 studio/_tools/video_engine_ab.py all

Every stage is idempotent and skips finished work; pass --force to re-render.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))          # studio/_tools
STUDIO = os.path.dirname(HERE)                             # studio
REPO = os.path.dirname(STUDIO)                             # comfy-studio
sys.path.insert(0, os.path.join(REPO, "scripts"))
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

COMFY = os.environ.get("COMFY_ROOT")
HOST = os.environ.get("COMFY_HOST")

REL = "claude-generated/hunyuan-ab"
LAB = f"{COMFY}/output/{REL}"
OUT = f"{STUDIO}/samples/hunyuan"
LTX_LAB = f"{COMFY}/output/claude-generated/motion-lib/cards"
KF_SRC = f"{STUDIO}/samples/motion_lib/_keyframe.png"
KF_STAGED = "hunyuan_ab_kf.png"
MANIFEST = f"{STUDIO}/samples/motion_lib/manifest.json"

W, H, FRAMES, FPS, SEED = 1280, 704, 97, 24, 7701

# The A/B set. Chosen to span the failure modes this project has already been bitten by,
# not to flatter either engine:
#   hold_all      must NOT move. Catches an engine that invents drift on a held shot.
#   walk_in       large subject translation - the hardest case for keeping a face.
#   hand_to_face  small precise limb motion, historically where video models fall apart.
#   head_turn     face rotation. The face is this project's measured weak spot.
#   steam         ambient micro-motion only (steam off the cup) - a pure boil test.
#   cam_push      camera move rather than subject move.
CARDS = ["hold_all", "walk_in", "hand_to_face", "head_turn", "steam", "cam_push"]


# ── shell helpers ─────────────────────────────────────────────────────────────
def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def card_texts():
    """The exact motion strings the LTX arm was rendered with, from its own manifest."""
    man = json.load(open(MANIFEST, encoding="utf-8"))
    out = {}
    for r in man:
        if r.get("seed") == SEED and r.get("card") in CARDS:
            out[r["card"]] = r["text"]
    missing = [c for c in CARDS if c not in out]
    if missing:
        raise SystemExit(f"no seed-{SEED} manifest row for: {missing}")
    return out


def ltx_clip(card):
    return f"{LTX_LAB}/{card}_s{SEED}_00001_.mp4"


def hy_clip(card, tag="i2v"):
    return f"{LAB}/hy_{tag}_{card}_00001_.mp4"


# ── comfy ─────────────────────────────────────────────────────────────────────
def load_wf(name):
    p = f"{REPO}/workflows/{name}"
    return {k: v for k, v in json.load(open(p, encoding="utf-8")).items()
            if not k.startswith("_")}


def strip_sr(wf):
    """Drop the SR block (nodes 60-76). Documented in the workflow _notes as safe:
    nothing in the base graph reads back from it."""
    for n in [str(i) for i in range(60, 77)]:
        wf.pop(n, None)
    return wf


def submit(wf):
    req = urllib.request.Request(
        f"http://{HOST}/prompt",
        data=json.dumps({"prompt": wf, "client_id": "video_engine_ab"}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())["prompt_id"]
    except urllib.error.HTTPError as e:
        print(e.read().decode(errors="replace")[:3000], file=sys.stderr)
        raise SystemExit("submit rejected - graph did not validate")


def wait(pids, label="jobs", timeout=21600):
    """Wait for queued prompts. Returns {pid: seconds} using ComfyUI's own execution
    timestamps, which exclude queue wait - that is the number worth quoting."""
    left, t0, last, secs = dict.fromkeys(pids), time.time(), -1, {}
    while left:
        if time.time() - t0 > timeout:
            print(f"  ! timeout with {len(left)} outstanding", file=sys.stderr)
            break
        time.sleep(6)
        try:
            h = json.load(urllib.request.urlopen(
                f"http://{HOST}/history?max_items=400", timeout=60))
        except Exception:
            continue
        for pid in list(left):
            e = h.get(pid)
            if not e:
                continue
            st = e.get("status", {})
            if st.get("status_str") == "error":
                print(f"  ! {pid} FAILED", file=sys.stderr)
                for m in st.get("messages", [])[-4:]:
                    print(f"    {str(m)[:600]}", file=sys.stderr)
                left.pop(pid, None)
                secs[pid] = None
            elif st.get("completed"):
                ts = {}
                for m in st.get("messages", []):
                    if isinstance(m, list) and len(m) > 1 and isinstance(m[1], dict):
                        if "timestamp" in m[1]:
                            ts[m[0]] = m[1]["timestamp"]
                if "execution_start" in ts and "execution_success" in ts:
                    secs[pid] = (ts["execution_success"] - ts["execution_start"]) / 1000.0
                else:
                    secs[pid] = None
                left.pop(pid, None)
        done = len(pids) - len(left)
        if done != last:
            print(f"  [{time.time()-t0:6.0f}s] {label} {done}/{len(pids)}", flush=True)
            last = done
    return secs


# ── metrics ───────────────────────────────────────────────────────────────────
def _frame(clip, idx, dest):
    """Write one frame to PNG. idx -1 means the last frame."""
    if idx < 0:
        r = sh("ffmpeg", "-y", "-hide_banner", "-sseof", "-0.2", "-i", clip,
               "-update", "1", "-q:v", "2", dest)
    else:
        r = sh("ffmpeg", "-y", "-hide_banner", "-i", clip, "-vf", f"select=eq(n\\,{idx})",
               "-vsync", "0", "-frames:v", "1", "-q:v", "2", dest)
    return os.path.exists(dest) and r.returncode == 0


def compare(a, b):
    """(ssim, psnr) between two images of equal size."""
    r = sh("ffmpeg", "-hide_banner", "-i", a, "-i", b,
           "-lavfi", "[0:v][1:v]ssim;[0:v][1:v]psnr", "-f", "null", "-")
    e = r.stderr or ""
    ms = re.search(r"SSIM .*All:([\d.]+)", e)
    mp = re.search(r"PSNR .*average:([\d.inf]+)", e)
    ssim = float(ms.group(1)) if ms else None
    try:
        psnr = float(mp.group(1)) if mp else None
    except ValueError:
        psnr = None
    return ssim, psnr


def measure_clip(clip, kf, tmp):
    """Every number for one clip. motion/churn/frozen come from the shipped module."""
    import analyze_shots as A
    m, churn = A.motion(clip)
    frozen = A.frozen_seconds(clip)
    f0, fl = f"{tmp}/_f0.png", f"{tmp}/_fl.png"
    kf_ssim = kf_psnr = drift = None
    if _frame(clip, 0, f0):
        kf_ssim, kf_psnr = compare(f0, kf)
        if _frame(clip, -1, fl):
            drift, _ = compare(f0, fl)
    r = sh("ffprobe", "-v", "error", "-show_entries",
           "stream=width,height,nb_frames", "-of", "csv=p=0", clip)
    dims = (r.stdout or "").strip().split("\n")[0]
    return {"motion": round(m, 3), "churn": round(churn, 3),
            "boil": round(churn / m, 3) if m > 1e-6 else None,
            "frozen": round(frozen, 2),
            "kf_ssim": round(kf_ssim, 4) if kf_ssim is not None else None,
            "kf_psnr": round(kf_psnr, 2) if kf_psnr is not None else None,
            "drift_ssim": round(drift, 4) if drift is not None else None,
            "dims": dims}


# ── stages ────────────────────────────────────────────────────────────────────
def stage_render(force=False, sr=False, cards=None, steps=20, length=FRAMES):
    """The Hunyuan i2v arm."""
    os.makedirs(LAB, exist_ok=True)
    if not os.path.exists(f"{COMFY}/input/{KF_STAGED}"):
        shutil.copy(KF_SRC, f"{COMFY}/input/{KF_STAGED}")
        print(f"  staged keyframe -> input/{KF_STAGED}")
    texts = card_texts()
    todo = [c for c in (cards or CARDS)]
    jobs, meta = [], {}
    for card in todo:
        tag = "i2v"
        if os.path.exists(hy_clip(card, tag)) and not force:
            print(f"  = {card} exists")
            continue
        wf = load_wf("42_hunyuan_i2v.json")
        if not sr:
            wf = strip_sr(wf)
        wf["8"]["inputs"]["image"] = KF_STAGED
        wf["10"]["inputs"]["text"] = texts[card]
        wf["20"]["inputs"]["width"] = W
        wf["20"]["inputs"]["height"] = H
        wf["20"]["inputs"]["length"] = length
        wf["32"]["inputs"]["noise_seed"] = SEED
        wf["34"]["inputs"]["steps"] = steps
        wf["42"]["inputs"]["filename_prefix"] = f"{REL}/hy_{tag}_{card}"
        if sr:
            wf["76"]["inputs"]["filename_prefix"] = f"{REL}/hy_sr_{card}"
        pid = submit(wf)
        jobs.append(pid)
        meta[pid] = card
        print(f"  > {card:14} {texts[card][:52]!r} -> {pid}", flush=True)
    if not jobs:
        return {}
    secs = wait(jobs, "hunyuan i2v")
    out = {meta[p]: secs.get(p) for p in jobs}
    for c, s in out.items():
        print(f"  {c:14} {('%.1fs' % s) if s else 'FAILED'}")
    p = f"{OUT}/render_secs.json"
    os.makedirs(OUT, exist_ok=True)
    prev = json.load(open(p)) if os.path.exists(p) else {}
    prev.update({k: v for k, v in out.items()})
    json.dump(prev, open(p, "w"), indent=1)
    return out


def stage_t2v(force=False, steps=20, length=FRAMES):
    """Text-to-video probe. Not part of the A/B - LTX i2v is what the app uses - but the
    t2v model is installed and the question 'does it run and what does it cost' is owed
    an answer."""
    os.makedirs(LAB, exist_ok=True)
    prompt = ("A woman in a dark green wool coat stands by a tall rain-streaked window in "
              "a quiet cafe. Red velvet curtains hang behind her. Steam rises from a white "
              "cup on a marble table. She breathes slowly and turns her head toward the "
              "window. Warm lamplight, cold blue daylight through the glass.")
    out = f"{LAB}/hy_t2v_cafe_00001_.mp4"
    if os.path.exists(out) and not force:
        print("  = t2v exists")
        return {}
    wf = strip_sr(load_wf("41_hunyuan_t2v.json"))
    wf["10"]["inputs"]["text"] = prompt
    wf["20"]["inputs"].update(width=W, height=H, length=length)
    wf["32"]["inputs"]["noise_seed"] = SEED
    wf["34"]["inputs"]["steps"] = steps
    wf["42"]["inputs"]["filename_prefix"] = f"{REL}/hy_t2v_cafe"
    pid = submit(wf)
    print(f"  > t2v cafe -> {pid}", flush=True)
    secs = wait([pid], "hunyuan t2v")
    print(f"  t2v {secs.get(pid)}s")
    return secs


def stage_sr(force=False, card="head_turn"):
    """The 1080p SR distill, run as the second stage of a fresh i2v render.

    NOTE ON 'AN EXISTING CLIP': HunyuanVideo15SuperResolution consumes a LATENT, not a
    video file, and the latent must come from the Hunyuan VAE at the Hunyuan latent
    layout. There is no supported path from a finished LTX mp4 into that node - see the
    sr-ltx stage for the attempt and what it costs."""
    return stage_render(force=force, sr=True, cards=[card])


def stage_sr_ltx(force=False, card="head_turn", length=None, src=None, noise_aug=None,
                 tag=None):
    """Run the 1080p SR distill over an EXISTING clip - by default an LTX one.

    This is the version of the SR test worth running. The supported path (stage sr) only
    upscales a latent Hunyuan just produced, which is no help to a library of finished LTX
    clips. HunyuanVideo15SuperResolution takes a LATENT, so the route in is
    LoadVideo -> GetVideoComponents -> VAEEncode(hunyuan vae), which puts arbitrary
    pixels into the Hunyuan latent layout. Whether the SR model accepts a latent that
    never came from its own sampler is exactly the open question.

    Built by reusing the SR block of 42_hunyuan_i2v.json and repointing node 62 at the
    encoded clip, so there is one definition of the SR settings, not two."""
    os.makedirs(LAB, exist_ok=True)
    src = src or ltx_clip(card)
    if not os.path.exists(src):
        raise SystemExit(f"no source clip: {src}")
    staged = f"hyab_src_{card}.mp4"
    shutil.copy(src, f"{COMFY}/input/{staged}")
    wf = load_wf("42_hunyuan_i2v.json")
    # keep only the SR block plus the loaders it needs
    for n in ["8", "9", "20", "30", "31", "32", "33", "34", "35", "40", "41", "42", "2", "4"]:
        wf.pop(n, None)
    wf["80"] = {"class_type": "LoadVideo", "inputs": {"file": staged}}
    wf["81"] = {"class_type": "GetVideoComponents", "inputs": {"video": ["80", 0]}}
    wf["82"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["81", 0], "vae": ["3", 0]}}
    wf["62"]["inputs"]["samples"] = ["82", 0]
    # no keyframe/clip-vision conditioning available for an arbitrary clip
    for k in ("start_image", "clip_vision_output"):
        wf["63"]["inputs"].pop(k, None)
    if noise_aug is not None:
        wf["63"]["inputs"]["noise_augmentation"] = noise_aug
    wf["10"]["inputs"]["text"] = card_texts().get(card, "")
    name = f"hy_srltx_{card}" + (f"-na{tag}" if tag else "")
    wf["76"]["inputs"]["filename_prefix"] = f"{REL}/{name}"
    out = f"{LAB}/{name}_00001_.mp4"
    if os.path.exists(out) and not force:
        print("  = sr-ltx output exists")
        return {}
    pid = submit(wf)
    print(f"  > sr-ltx {card} from {os.path.basename(src)} -> {pid}", flush=True)
    secs = wait([pid], "sr-ltx")
    print(f"  sr-ltx {card}: {secs.get(pid)}")
    return secs


def stage_measure(force=False):
    os.makedirs(OUT, exist_ok=True)
    tmp = f"{OUT}/_tmp"
    os.makedirs(tmp, exist_ok=True)
    kf = KF_SRC
    rows = []
    for card in CARDS:
        for engine, path in (("ltx", ltx_clip(card)), ("hunyuan", hy_clip(card))):
            if not os.path.exists(path):
                print(f"  - {engine:8} {card:14} MISSING")
                continue
            r = measure_clip(path, kf, tmp)
            r.update(card=card, engine=engine, file=path)
            rows.append(r)
            print(f"  {engine:8} {card:14} kf_ssim {r['kf_ssim']}  motion {r['motion']:6.2f}"
                  f"  boil {r['boil']}  drift {r['drift_ssim']}  frozen {r['frozen']}")
    # SR clips, if any. Two distinct engines share this prefix and they are NOT the same
    # experiment, so they are labelled apart:
    #   hy_sr_     SR over a latent Hunyuan itself just sampled  (the supported path)
    #   hy_srltx_  SR over an LTX clip pushed through VAEEncode  (the foreign-latent path)
    for f in (sorted(os.listdir(LAB)) if os.path.isdir(LAB) else []):
        if not (f.startswith("hy_sr") and f.endswith(".mp4")):
            continue
        srltx = f.startswith("hy_srltx_")
        eng = "hunyuan_sr_from_ltx" if srltx else "hunyuan_sr"
        card = f[len("hy_srltx_" if srltx else "hy_sr_"):].split("_00001")[0]
        path = f"{LAB}/{f}"
        r = measure_clip(path, kf, tmp)
        r.update(card=card, engine=eng, file=path)
        rows.append(r)
        print(f"  {eng:20} {card:14} dims {r['dims']}  kf_ssim {r['kf_ssim']}  "
              f"motion {r['motion']:6.2f}  boil {r['boil']}")
    json.dump(rows, open(f"{OUT}/results.json", "w"), indent=1)
    print(f"\nwrote {OUT}/results.json  ({len(rows)} clips)")
    summary(rows)
    return rows


def summary(rows):
    print(f"\n{'='*78}\nENGINE MEANS (n per engine in brackets)")
    print(f"{'engine':12} {'n':>3} {'kf_ssim':>8} {'kf_psnr':>8} {'motion':>8} "
          f"{'boil':>7} {'drift':>7} {'frozen':>7}")
    for eng in ("ltx", "hunyuan", "hunyuan_sr"):
        g = [r for r in rows if r["engine"] == eng]
        if not g:
            continue

        def mean(k):
            v = [r[k] for r in g if r.get(k) is not None]
            return sum(v) / len(v) if v else float("nan")
        print(f"{eng:12} {len(g):3} {mean('kf_ssim'):8.4f} {mean('kf_psnr'):8.2f} "
              f"{mean('motion'):8.2f} {mean('boil'):7.3f} {mean('drift_ssim'):7.4f} "
              f"{mean('frozen'):7.2f}")
    print("\nPER CARD (ltx -> hunyuan)")
    print(f"{'card':14} {'kf_ssim':>17} {'motion':>17} {'boil':>17}")
    for card in CARDS:
        d = {r["engine"]: r for r in rows if r["card"] == card}
        if "ltx" not in d or "hunyuan" not in d:
            continue
        l, h = d["ltx"], d["hunyuan"]

        def pair(k, f="%.4f"):
            return f"{f % l[k]} -> {f % h[k]}" if l.get(k) is not None and h.get(k) is not None else "n/a"
        print(f"{card:14} {pair('kf_ssim'):>17} {pair('motion','%.2f'):>17} "
              f"{pair('boil','%.3f'):>17}")


def stage_strips(force=False, n=6):
    """Side-by-side frame strips: LTX row over Hunyuan row, same card, same timestamps.

    ffmpeg tile= with a glob silently drops cells when inputs differ in size (this repo
    has been bitten). Explicit -i args, hstack, and the cell count is asserted."""
    sdir = f"{OUT}/strips"
    os.makedirs(sdir, exist_ok=True)
    tmp = f"{OUT}/_tmp"
    os.makedirs(tmp, exist_ok=True)
    made = []
    for card in CARDS:
        dest = f"{sdir}/{card}.png"
        if os.path.exists(dest) and not force:
            print(f"  = {card} strip exists")
            made.append(dest)
            continue
        rows_in = []
        for engine, path in (("ltx", ltx_clip(card)), ("hunyuan", hy_clip(card))):
            if not os.path.exists(path):
                print(f"  - {engine} {card} missing, skipping strip")
                rows_in = []
                break
            cells = []
            for i in range(n):
                idx = round(i * (FRAMES - 1) / (n - 1))
                c = f"{tmp}/{engine}_{card}_{i}.png"
                if not _frame(path, idx, c):
                    print(f"  ! could not extract frame {idx} from {path}")
                    break
                cells.append(c)
            if len(cells) != n:
                rows_in = []
                break
            rowp = f"{tmp}/row_{engine}_{card}.png"
            args = ["ffmpeg", "-y", "-hide_banner"]
            for c in cells:
                args += ["-i", c]
            fc = "".join(f"[{i}:v]scale=320:176,drawtext=text='{engine} f"
                         f"{round(i*(FRAMES-1)/(n-1))}':x=6:y=6:fontsize=16:"
                         f"fontcolor=white:box=1:boxcolor=black@0.6[v{i}];"
                         for i in range(n))
            fc += "".join(f"[v{i}]" for i in range(n)) + f"hstack=inputs={n}[out]"
            args += ["-filter_complex", fc, "-map", "[out]", "-frames:v", "1", rowp]
            r = sh(*args)
            if not os.path.exists(rowp):
                print(f"  ! row build failed for {engine} {card}")
                print((r.stderr or "")[-1500:])
                rows_in = []
                break
            rows_in.append(rowp)
        if len(rows_in) != 2:
            continue
        r = sh("ffmpeg", "-y", "-hide_banner", "-i", rows_in[0], "-i", rows_in[1],
               "-filter_complex", "[0:v][1:v]vstack=inputs=2[out]",
               "-map", "[out]", "-frames:v", "1", dest)
        if not os.path.exists(dest):
            print(f"  ! vstack failed for {card}")
            print((r.stderr or "")[-1500:])
            continue
        # assert the strip is the size the cell count implies
        pr = sh("ffprobe", "-v", "error", "-show_entries", "stream=width,height",
                "-of", "csv=p=0", dest)
        got = (pr.stdout or "").strip()
        want = f"{320*n},{176*2}"
        flag = "OK" if got == want else f"WRONG (want {want}) - CELLS WERE DROPPED"
        print(f"  {card:14} strip {got} {flag}")
        made.append(dest)
    return made


STAGES = {"render": stage_render, "t2v": stage_t2v, "sr": stage_sr,
          "sr-ltx": stage_sr_ltx, "measure": stage_measure, "strips": stage_strips}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("stage", choices=list(STAGES) + ["all"])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--sr", action="store_true", help="render stage: keep the SR block")
    ap.add_argument("--card", action="append", help="limit to these cards")
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--length", type=int, default=FRAMES)
    ap.add_argument("--noise-aug", dest="noise_aug", type=float, default=None,
                    help="sr-ltx: override HunyuanVideo15SuperResolution "
                         "noise_augmentation (template default 0.7)")
    a = ap.parse_args()

    if a.stage == "all":
        stage_render(force=a.force, sr=a.sr, cards=a.card, steps=a.steps,
                     length=a.length)
        stage_measure()
        stage_strips(force=a.force)
        return
    if a.stage == "render":
        stage_render(force=a.force, sr=a.sr, cards=a.card, steps=a.steps,
                     length=a.length)
    elif a.stage == "t2v":
        stage_t2v(force=a.force, steps=a.steps, length=a.length)
    elif a.stage == "sr":
        stage_sr(force=a.force, card=(a.card or ["head_turn"])[0])
    elif a.stage == "sr-ltx":
        stage_sr_ltx(force=a.force, card=(a.card or ["head_turn"])[0],
                     noise_aug=a.noise_aug,
                     tag=(str(a.noise_aug).replace(".", "")
                          if a.noise_aug is not None else None))
    elif a.stage == "measure":
        stage_measure(force=a.force)
    elif a.stage == "strips":
        stage_strips(force=a.force)


if __name__ == "__main__":
    main()
