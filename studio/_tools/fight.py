#!/usr/bin/env python3
"""studio/_tools/fight.py - an action sequence built the way the Alter Anime Studio breakdown builds one,
on local weights, with every step this studio can measure measured.

THE BREAKDOWN'S PIPELINE (Vol. 01, "Lee vs Gaara"): refs -> start frame -> a seven-block prompt ->
one long generation -> post. Its engine is Seedance 2.0/2.5 (paid, 15 s, native multi-reference).
Ours is LTX-2.5 (local, 30 s at 0.9 MP) and H3, and the multi-reference is resolved one step
earlier - Flux 2 chains the character and place references into the START FRAME (workflow 75),
which is the substitute WHERE-WE-STAND §2 reasoned its way to before the node existed.

WHAT IS TAKEN FROM THE BREAKDOWN, AND WHAT IS NOT
  taken      refs carry identity; never describe a character the picture carries
  taken      one mover per beat ("freeze the defender") - and it is our own measured rule
  taken      effects exist at the instant of impact and then vanish - his rule 3, measured here
             for the first time by the --ab arm
  taken      the camera always has a job; handheld float for photoreal
  taken      write the sound; no music where the edit owns the score
  taken      one grade line, applied once, after the cuts
  taken      AVOID is a spellbook that grows from what broke on the last roll
  NOT taken   timecoded beats - measured dead on LTX-2.5 (§95 S5): the word *cut* makes the cut,
             and pacing is decided at assembly
  NOT taken   a shot-for-shot recreation of somebody's copyrighted fight. The cast, the court and
             the story here are invented; no real person and no existing character is referenced.

    python3 studio/_tools/fight.py --cast      three character references and the court plate
    python3 studio/_tools/fight.py --anchors   one composited start frame per shot (workflow 75)
    python3 studio/_tools/fight.py --shots     LTX-2.5 renders, one retry on a fault
    python3 studio/_tools/fight.py --ab        rule 3: effects as instants vs a standing wall
    python3 studio/_tools/fight.py --score     identity across shots, camera against the ask
    python3 studio/_tools/fight.py --finish    assemble, one grade, loudness
Every stage skips work already on disk, so a killed run is resumed by running it again.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
TOOLS = os.path.join(STUDIO, "_tools")
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run                       # noqa: E402
from epic import COMFY, HOST, load_wf       # noqa: E402

PY = os.path.expanduser("~/ComfyUI/venv/bin/python3")

# ----------------------------------------------------------------- the sequence
# The story lives in studio/sequences/<film>.json, not here: cast, place, look and shots. The
# sequence is chosen before argparse runs because the rule-3 A/B is built at import time.
SEQ_DIR = os.path.join(STUDIO, "shotscripts")   # studio/sequences/ holds edit ANALYSES


def _which_sequence(argv):
    for i, a in enumerate(argv):
        if a == "--sequence" and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith("--sequence="):
            return a.split("=", 1)[1]
    return os.environ.get("FIGHT_SEQUENCE", "ash-court")


SEQUENCE = _which_sequence(sys.argv)
_path = os.path.join(SEQ_DIR, "%s.json" % SEQUENCE)
if not os.path.exists(_path):
    raise SystemExit("no shot script at %s\n  have: %s" % (
        _path, ", ".join(sorted(f[:-5] for f in os.listdir(SEQ_DIR) if f.endswith(".json")))
        if os.path.isdir(SEQ_DIR) else "none"))
_seq = json.load(open(_path, encoding="utf-8"))
if not all(k in _seq for k in ("film", "cast", "place", "shots")):
    raise SystemExit("%s is not a shot script (it needs film, cast, place, shots). "
                     "studio/sequences/ holds edit analyses, not films." % _path)

FILM = _seq["film"]
OUT = os.path.join(STUDIO, "samples", "fight", FILM)
REAL = _seq.get("realism", "")
GRADE = _seq["grade"]
AVOID = _seq["avoid"]
SCORE_TAGS = _seq["score_tags"]
COURT = _seq["place"]["prompt"]
PLACE_ID = _seq["place"].get("id", "court")
CAST = {k: {"role": v["role"], "ref": v["prompt"]} for k, v in _seq["cast"].items()}
SHOTS = _seq["shots"]


def shot(sid):
    """A shot by its id - never by position: the running order changes."""
    for x in SHOTS:
        if x["id"] == sid:
            return x
    raise SystemExit("no shot %s in sequence %s" % (sid, SEQUENCE))


def _build_ab():
    """The breakdown's rule 3, as an A/B on shot 010: the effect as an INSTANT against the effect
    as a STANDING state. The swap is asserted - a silent no-op would be a prompt against itself."""
    instants = shot("010")["prompt"]
    hit = ("At the exact instant each punch arrives a sharp burst of grey ash snaps up between them "
           "to stop it dead, and drops away at once; between the punches there is no ash in the air.")
    wall = ("A standing wall of grey ash hangs in the air between them for the whole shot, swirling "
            "continuously as it turns each punch aside.")
    if hit not in instants:
        return {}
    return {"instants": instants, "standing": instants.replace(hit, wall)}


AB = _build_ab()


def sh(*a, **kw):
    return subprocess.run(a, capture_output=True, text=True, **kw)


def comfy_up(budget=90):
    for _ in range(budget):
        try:
            urllib.request.urlopen("http://%s/system_stats" % HOST, timeout=3).read()
            return True
        except Exception:
            time.sleep(1)
    return False


def submit(wf, tag, tries=3):
    """Render, and survive the box: the kernel OOM killer takes ComfyUI when another process on
    this host is large (playbook §97.4), which arrives here as a closed socket."""
    for attempt in range(1, tries + 1):
        try:
            _, outs = run(HOST, wf, quiet=True)
            return outs or []
        except (urllib.error.URLError, ConnectionRefusedError, OSError, RuntimeError) as e:
            msg = str(e)[:120]
            print("  %s attempt %d failed: %s" % (tag, attempt, msg), flush=True)
            if attempt == tries:
                return []
            if not comfy_up(5):
                print("  ComfyUI is down - restarting it", flush=True)
                sh("bash", os.path.join(ROOT, "scripts", "restart-comfy.sh"))
                comfy_up()
            time.sleep(5)
    return []


def wait_for_queue(budget=1800):
    t0 = time.time()
    while time.time() - t0 < budget:
        try:
            q = json.load(urllib.request.urlopen("http://%s/queue" % HOST, timeout=20))
            if not q["queue_running"] and not q["queue_pending"]:
                return True
        except Exception:
            return True
        print("  someone else's job is running - waiting", flush=True)
        time.sleep(20)
    return False


def collect(outs, dst, kinds=(".png", ".jpg", ".mp4")):
    got = [o for o in outs if str(o).lower().endswith(kinds)]
    if not got:
        return None
    shutil.copy(os.path.join(COMFY, "output", got[0]), dst)
    return dst


# --------------------------------------------------------------------------- stages
def stage_cast(force=False, only="", seed=4242):
    os.makedirs(OUT, exist_ok=True)
    jobs = [(k, v["ref"]) for k, v in CAST.items()] + [(PLACE_ID, COURT)]
    if only:
        jobs = [j for j in jobs if j[0] == only] or sys.exit("no such reference: %s" % only)
    for name, prompt in jobs:
        dst = os.path.join(OUT, "ref_%s.png" % name)
        if os.path.exists(dst) and not force:
            print("  ref_%s.png already there" % name, flush=True)
            continue
        wf = {k: v for k, v in load_wf("40_flux2_t2i.json").items()
              if isinstance(v, dict) and "class_type" in v}
        wf["6"]["inputs"]["text"] = prompt
        w, h = (1280, 720) if name == PLACE_ID else (768, 1344)
        for n in ("9", "12"):
            wf[n]["inputs"]["width"], wf[n]["inputs"]["height"] = w, h
        wf["11"]["inputs"]["noise_seed"] = int(seed)
        wf["15"]["inputs"]["filename_prefix"] = "claude-generated/fight/ref_%s" % name
        wait_for_queue()
        t0 = time.time()
        if collect(submit(wf, "ref_" + name), dst):
            print("  ref_%-8s %4.0fs  %dx%d" % (name, time.time() - t0, w, h), flush=True)
        else:
            print("  ref_%s FAILED" % name, flush=True)


def stage_anchors(force=False):
    for s in SHOTS:
        dst = os.path.join(OUT, "anchor_%s.png" % s["id"])
        if os.path.exists(dst) and not force:
            print("  anchor_%s.png already there" % s["id"], flush=True)
            continue
        refs = [os.path.join(OUT, "ref_%s.png" % r) for r in s["refs"]]
        if not all(os.path.exists(p) for p in refs):
            sys.exit("cast first: missing %s" % [p for p in refs if not os.path.exists(p)])
        if s.get("anchor") is None:
            # nobody in it: the plate is already the start frame
            shutil.copy(refs[0], dst)
            print("  anchor_%s  <- the plate itself (no cast in this shot)" % s["id"], flush=True)
            continue
        for i, p in enumerate(refs, 1):
            shutil.copy(p, os.path.join(COMFY, "input", "fight_ref%d.png" % i))
        wf = {k: v for k, v in load_wf("75_flux2_ref3.json").items()
              if isinstance(v, dict) and "class_type" in v}
        wf["sg1_6"]["inputs"]["text"] = s["anchor"]
        wf["sg1_25"]["inputs"]["noise_seed"] = 4242
        wf["9"]["inputs"]["filename_prefix"] = "claude-generated/fight/anchor_%s" % s["id"]
        wait_for_queue()
        t0 = time.time()
        if collect(submit(wf, "anchor_" + s["id"]), dst):
            print("  anchor_%s  %4.0fs  refs %s" % (s["id"], time.time() - t0, ",".join(s["refs"])), flush=True)
        else:
            print("  anchor_%s FAILED" % s["id"], flush=True)


def ltx_graph(start_png, prompt, secs, seed, prefix):
    wf = {k: v for k, v in load_wf("70_ltx25_i2v.json").items()
          if isinstance(v, dict) and "class_type" in v}
    shutil.copy(start_png, os.path.join(COMFY, "input", "fight_start.png"))
    wf["395"]["inputs"]["image"] = "fight_start.png"
    wf["sg1_383"]["inputs"]["value"] = False          # the Gemma prompt enhancer rewrites the direction
    wf["sg1_376"]["inputs"]["value"] = prompt
    wf["sg1_373"]["inputs"]["text"] = AVOID
    wf["sg1_362"]["inputs"]["value"] = int(secs)
    wf["sg1_339"]["inputs"]["noise_seed"] = int(seed)
    wf["sg1_338"]["inputs"]["noise_seed"] = int(seed) + 1
    wf["75"]["inputs"]["filename_prefix"] = prefix
    return wf


def stage_shots(seeds=(11,), force=False):
    for s in SHOTS:
        anchor = os.path.join(OUT, "anchor_%s.png" % s["id"])
        if not os.path.exists(anchor):
            sys.exit("anchors first: %s missing" % anchor)
        for seed in seeds:
            dst = os.path.join(OUT, "shot_%s_s%d.mp4" % (s["id"], seed))
            if os.path.exists(dst) and not force:
                print("  shot_%s_s%d already there" % (s["id"], seed), flush=True)
                continue
            wf = ltx_graph(anchor, s["prompt"], s["secs"], seed,
                           "claude-generated/fight/shot_%s_s%d" % (s["id"], seed))
            if s.get("avoid_extra"):
                wf["sg1_373"]["inputs"]["text"] = AVOID + ", " + s["avoid_extra"]
            wait_for_queue()
            t0 = time.time()
            if collect(submit(wf, "shot_%s_s%d" % (s["id"], seed)), dst):
                print("  shot_%s_s%-5d %4.0fs  %ss" % (s["id"], seed, time.time() - t0, s["secs"]), flush=True)
            else:
                print("  shot_%s_s%d FAILED" % (s["id"], seed), flush=True)


def stage_ab(seeds=(11, 202, 3003), force=False):
    if not AB:
        sys.exit("this sequence has no rule-3 A/B: shot 010's prompt does not carry the "
                 "instants sentence the standing-wall arm swaps out")
    s = shot("010")
    anchor = os.path.join(OUT, "anchor_%s.png" % s["id"])
    for arm, prompt in AB.items():
        for seed in seeds:
            dst = os.path.join(OUT, "ab_%s_s%d.mp4" % (arm, seed))
            if os.path.exists(dst) and not force:
                continue
            wf = ltx_graph(anchor, prompt, s["secs"], seed,
                           "claude-generated/fight/ab_%s_s%d" % (arm, seed))
            wait_for_queue()
            t0 = time.time()
            if collect(submit(wf, "ab_%s_s%d" % (arm, seed)), dst):
                print("  ab_%-9s s%-5d %4.0fs" % (arm, seed, time.time() - t0), flush=True)
            else:
                print("  ab_%s_s%d FAILED" % (arm, seed), flush=True)


def strip(video, dst, n=8, h=150):
    dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                   video).stdout.strip() or 0)
    from PIL import Image
    ims = []
    for i in range(n):
        p = dst + ".%d.png" % i
        sh("ffmpeg", "-y", "-v", "error", "-ss", "%.2f" % (dur * i / max(1, n - 1) * 0.98), "-i", video,
           "-frames:v", "1", "-vf", "scale=-2:%d" % h, p)
        if os.path.exists(p):
            ims.append(Image.open(p).convert("RGB"))
            os.remove(p)
    if ims:
        S = Image.new("RGB", (sum(i.width for i in ims), h))
        x = 0
        for im in ims:
            S.paste(im, (x, 0))
            x += im.width
        S.save(dst, quality=86)
    return dur


def cam(path):
    """cammeasure needs cv2, which lives in the system python, not ComfyUI's venv."""
    r = sh("python3", os.path.join(TOOLS, "cammeasure.py"), path)
    for line in r.stdout.splitlines():
        try:
            return json.loads(line)
        except Exception:
            pass
    return {}


def stage_seedance(shot_id, resolution="1080p", force=False):
    """The paid half of the hybrid: the same composed start frame and the same character references,
    handed to Seedance 2.5. Costs money per run and needs somebody signed in to a Comfy account."""
    s = next((x for x in SHOTS if x["id"] == shot_id), None) or sys.exit("no shot %s" % shot_id)
    dst = os.path.join(OUT, "seedance_%s.mp4" % shot_id)
    if os.path.exists(dst) and not force:
        print("  seedance_%s already there" % shot_id, flush=True)
        return dst
    anchor = os.path.join(OUT, "anchor_%s.png" % shot_id)
    chars = [os.path.join(OUT, "ref_%s.png" % r) for r in s["refs"] if r != "court"]
    for i, p_ in enumerate([anchor] + chars[:2], 1):
        if not os.path.exists(p_):
            sys.exit("missing %s" % p_)
        shutil.copy(p_, os.path.join(COMFY, "input", "fight_sd_ref%d.png" % i))
    wf = {k: v for k, v in load_wf("76_seedance25_ref.json").items()
          if isinstance(v, dict) and "class_type" in v}
    n = wf["seedance"]["inputs"]
    n["model.prompt"] = ("Reference image one is the first frame of the shot. " + s["prompt"])
    n["model.duration"] = int(s["secs"])
    n["model.resolution"] = resolution
    n["seed"] = 11
    wf["save"]["inputs"]["filename_prefix"] = "claude-generated/fight/seedance_%s" % shot_id
    print("  submitting %s to Seedance 2.5, %ss at %s - THIS SPENDS CREDITS" % (shot_id, s["secs"], resolution), flush=True)
    outs = submit(wf, "seedance_%s" % shot_id, tries=1)
    if collect(outs, dst):
        print("  seedance_%s -> %s" % (shot_id, dst), flush=True)
        return dst
    print("  seedance_%s produced nothing." % shot_id, flush=True)
    print("  If the log says unauthorized or 401, nobody is signed in: open "
          "http://192.168.0.45:8188 and log in with the Comfy account that holds the credits.",
          flush=True)
    return None


def h3_length(secs, fps=24):
    """H3 wants 17n + 5 frames; take the closest at or under the asked seconds."""
    want = int(secs * fps)
    n = max(1, (want - 5) // 17)
    return 17 * n + 5


def stage_h3(shot_id, seeds=(11,), force=False):
    """The same start frame and the same words, on H3 instead of LTX-2.5."""
    from PIL import Image
    s = next((x for x in SHOTS if x["id"] == shot_id), None)
    if s is None:
        sys.exit("no shot %s" % shot_id)
    anchor = os.path.join(OUT, "anchor_%s.png" % shot_id)
    if not os.path.exists(anchor):
        sys.exit("missing %s" % anchor)
    # every pixel dimension must be a multiple of 32 or H3 dies inside patchify_video
    im = Image.open(anchor).convert("RGB")
    w, h = 1280, 704
    crop = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    top = max(0, (crop.height - h) // 2)
    crop = crop.crop((0, top, w, top + h))
    staged = os.path.join(OUT, "anchor_%s_h3.png" % shot_id)
    crop.save(staged)
    shutil.copy(staged, os.path.join(COMFY, "input", "h3_start.png"))
    length = h3_length(s["secs"])
    for seed in seeds:
        dst = os.path.join(OUT, "h3_%s_s%d.mp4" % (shot_id, seed))
        if os.path.exists(dst) and not force:
            print("  h3_%s_s%d already there" % (shot_id, seed), flush=True)
            continue
        wf = {k: v for k, v in load_wf("67_minimax_h3_i2v_sparse.json").items()
              if isinstance(v, dict) and "class_type" in v}
        wf["8"]["inputs"]["image"] = "h3_start.png"
        wf["20"]["inputs"]["prompt"] = s["prompt"]
        wf["20"]["inputs"]["width"], wf["20"]["inputs"]["height"] = w, h
        wf["20"]["inputs"]["length"] = length
        wf["33"]["inputs"]["noise_seed"] = int(seed)
        wf["51"]["inputs"]["filename_prefix"] = "claude-generated/fight/h3_%s_s%d" % (shot_id, seed)
        wait_for_queue()
        import post
        have, why = post.make_room(need_gb=26.0, budget=240)
        print("  GPU %.1f GB free (%s)" % (have, why), flush=True)
        t0 = time.time()
        if collect(submit(wf, "h3_%s_s%d" % (shot_id, seed)), dst):
            print("  h3_%s_s%-5d %4.0fs  %d frames" % (shot_id, seed, time.time() - t0, length), flush=True)
        else:
            print("  h3_%s_s%d FAILED" % (shot_id, seed), flush=True)


def stage_sheets(picks=None):
    """A board per shot: every take, its strip, and what was measured on it."""
    from PIL import Image, ImageDraw, ImageFont
    picks = picks or {}
    font = ImageFont.truetype("/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf", 17)
    measured = {}
    mp = os.path.join(OUT, "measured.json")
    if os.path.exists(mp):
        measured = json.load(open(mp))
    board_dir = os.path.join(OUT, "picks")
    os.makedirs(board_dir, exist_ok=True)
    for sh_ in SHOTS:
        sid = sh_["id"]
        takes = sorted(f for f in os.listdir(OUT)
                       if f.endswith(".mp4") and ("_%s_s" % sid) in f and not f.startswith("_"))
        rows = []
        for t in takes:
            strip_p = os.path.join(OUT, t[:-4] + "_strip.jpg")
            if not os.path.exists(strip_p):
                continue
            m = measured.get(t, {})
            engine = "H3" if t.startswith("h3_") else "LTX"
            seed = t[:-4].split("_s")[-1]
            chosen = str(picks.get(sid, "")).endswith(seed) and (
                ("h3" in str(picks.get(sid, ""))) == t.startswith("h3_"))
            rows.append(("%s  seed %-6s %-4s %-34s %s" % (sid, seed, engine, m.get("camera", ""),
                                                          "<-- in the cut" if chosen else ""), strip_p))
        if not rows:
            continue
        ims = []
        for label, p in rows:
            im = Image.open(p).convert("RGB")
            w = 1500
            ims.append((label, im.resize((w, max(1, int(im.height * w / im.width))))))
        H = sum(i.height + 24 for _, i in ims) + 30
        board = Image.new("RGB", (1500, H), (18, 18, 20))
        d = ImageDraw.Draw(board)
        d.text((6, 6), "%s - %s (%s s, %d takes)" % (sid, sh_["title"], sh_["secs"], len(ims)),
               font=font, fill=(120, 200, 255))
        y = 30
        for label, im in ims:
            d.text((6, y + 3), label, font=font, fill=(255, 214, 102))
            board.paste(im, (0, y + 24))
            y += im.height + 24
        out = os.path.join(board_dir, "%s.jpg" % sid)
        board.save(out, quality=85)
        print("  %s  %d takes -> %s" % (sid, len(ims), out), flush=True)


def stage_score():
    rows = {}
    for f in sorted(os.listdir(OUT)):
        if not f.endswith(".mp4"):
            continue
        v = os.path.join(OUT, f)
        dur = strip(v, os.path.join(OUT, f[:-4] + "_strip.jpg"))
        m = cam(v)
        n = int(sh("ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                   "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", v).stdout.strip() or 0)
        rows[f] = {"seconds": round(dur, 2), "frames": n, "camera": m.get("camera"),
                   "zoom": m.get("zoom"), "pan": m.get("pan"), "tilt": m.get("tilt"),
                   "confidence": m.get("confidence")}
        print("%-28s %5.1fs %4d frames  %s" % (f, dur, n, m.get("camera")), flush=True)
    json.dump(rows, open(os.path.join(OUT, "measured.json"), "w"), indent=1)
    return rows


def stage_music(seconds=24, seed=77, force=False):
    """The scene bed, written once for the whole sequence because the shots were rendered silent
    of music on purpose (the breakdown's rule 7; §96.7 here)."""
    dst = os.path.join(OUT, "score.mp3")
    if os.path.exists(dst) and not force:
        print("  score.mp3 already there", flush=True)
        return dst
    wf = {k: v for k, v in load_wf("06_acestep_music.json").items()
          if isinstance(v, dict) and "class_type" in v}
    wf["10"]["inputs"]["tags"] = SCORE_TAGS
    wf["10"]["inputs"]["lyrics"] = ""
    wf["11"]["inputs"]["seconds"] = float(seconds)
    if "duration" in wf["10"]["inputs"]:
        wf["10"]["inputs"]["duration"] = float(seconds)
    wf["12"]["inputs"]["seed"] = int(seed)
    wf["14"]["inputs"]["filename_prefix"] = "claude-generated/fight/score"
    wait_for_queue()
    import post
    post.make_room(need_gb=10.0, budget=180)
    t0 = time.time()
    outs = submit(wf, "score")
    got = [o for o in outs if str(o).lower().endswith((".mp3", ".flac", ".wav"))]
    if not got:
        print("  score FAILED (%s)" % outs, flush=True)
        return None
    shutil.copy(os.path.join(COMFY, "output", got[0]), dst)
    print("  score  %4.0fs  %ss of bed" % (time.time() - t0, seconds), flush=True)
    return dst


def stage_finish(picks=None, grade="filmic", master=False):
    """Assemble, one grade after the cuts, loudness, and the studio's frame-count invariant."""
    import post
    picks = picks or {}
    chosen = []
    for s in SHOTS:
        want = str(picks.get(s["id"], 11))
        engine, _, seed = want.rpartition(":")
        stem = {"h3": "h3", "": "shot"}.get(engine, engine)
        p = os.path.join(OUT, "%s_%s_s%s.mp4" % (stem, s["id"], seed))
        if not os.path.exists(p):
            print("  no take for %s (%s) - skipping" % (s["id"], os.path.basename(p)), flush=True)
            continue
        chosen.append((s["id"], want, p))
    if not chosen:
        sys.exit("no picked takes")
    for sid, seed, p in chosen:
        print("  %s <- seed %s" % (sid, seed), flush=True)
    # conform: H3 writes 32 kHz audio and LTX 48 kHz, and the concat demuxer wants them identical.
    # Video is copied, so no frame can move.
    conformed = []
    for sid, seed, p in chosen:
        rate = sh("ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                  "stream=sample_rate", "-of", "csv=p=0", p).stdout.strip()
        if rate == "48000":
            conformed.append((sid, seed, p))
            continue
        c = os.path.join(OUT, "_conform_%s.mp4" % os.path.basename(p)[:-4])
        sh("ffmpeg", "-y", "-v", "error", "-i", p, "-c:v", "copy",
           "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", c)
        print("  conformed %s: audio %s Hz -> 48000" % (os.path.basename(p), rate or "none"), flush=True)
        conformed.append((sid, seed, c))
    chosen = conformed
    lst = os.path.join(OUT, "_concat.txt")
    open(lst, "w").write("".join("file '%s'\n" % p for _, _, p in chosen))
    cut = os.path.join(OUT, "%s_cut.mp4" % FILM)
    sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
       "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", cut)
    vf = post.grade_filter(grade)
    out = os.path.join(OUT, "%s_%s.mp4" % (FILM, grade))
    bed = os.path.join(OUT, "score.mp3")
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", cut]
    if os.path.exists(bed):
        dur = post.duration(cut)
        cmd += ["-i", bed, "-filter_complex",
                ("[1:a]volume=0.5,afade=t=out:st=%.2f:d=1.5[m];"
                 "[0:a][m]amix=inputs=2:duration=first:dropout_transition=0,"
                 "loudnorm=I=-16:TP=-1.5:LRA=11[a]" % max(0.0, dur - 1.5))]
        if vf:
            cmd += ["-vf", vf]
        cmd += ["-map", "0:v", "-map", "[a]"]
        print("  scene bed mixed under at 0.5", flush=True)
    else:
        if vf:
            cmd += ["-vf", vf]
        cmd += ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"]
    cmd += ["-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", out]
    sh(*cmd)
    want = sum(post.frames(p) for _, _, p in chosen)
    got = post.frames(out)
    print("cut %d shots -> %s" % (len(chosen), out), flush=True)
    print("frame count: takes %d, film %d  %s" % (want, got, "OK" if want == got else "MISMATCH"), flush=True)
    if master:
        post.make_room(need_gb=8.0, budget=240)
        hi = os.path.join(OUT, "%s_%s_2x.mp4" % (FILM, grade))
        t0 = time.time()
        post.upscale(out, hi, scale=2)
        print("2x master -> %s  (%.0fs, frames %d)" % (hi, time.time() - t0, post.frames(hi)), flush=True)
    return out

def main():
    ap = argparse.ArgumentParser()
    for s in ("cast", "anchors", "shots", "ab", "score", "finish"):
        ap.add_argument("--" + s, action="store_true")
    ap.add_argument("--seedance", default="", metavar="SHOT",
                    help="render this shot on Seedance 2.5 (paid; needs a signed-in Comfy account)")
    ap.add_argument("--resolution", default="1080p", choices=["480p", "720p", "1080p"])
    ap.add_argument("--music", action="store_true", help="write the scene bed (ACE-Step)")
    ap.add_argument("--picks", default="", help="010=202,020=11,030=3003")
    ap.add_argument("--sequence", default=SEQUENCE,
                    help="which studio/sequences/<film>.json to build (read before argparse)")
    ap.add_argument("--sheets", action="store_true", help="a contact board per shot, for picking")
    ap.add_argument("--master", action="store_true", help="--finish: also write the 2x master")
    ap.add_argument("--h3", default="", metavar="SHOT",
                    help="render this shot on H3 (workflow 67) from the same anchor")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default="", help="--cast: just this reference (vesper/koval/marrow/court)")
    ap.add_argument("--seed", type=int, default=4242, help="--cast: the seed for a re-roll")
    ap.add_argument("--seeds", type=int, nargs="+", default=[11])
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.cast:
        stage_cast(a.force, a.only, a.seed)
    if a.anchors:
        stage_anchors(a.force)
    if a.shots:
        stage_shots(tuple(a.seeds), a.force)
    if a.ab:
        stage_ab(tuple(a.seeds) if len(a.seeds) > 1 else (11, 202, 3003), a.force)
    if a.seedance:
        stage_seedance(a.seedance, a.resolution, a.force)
    if a.h3:
        stage_h3(a.h3, tuple(a.seeds), a.force)
    if a.score:
        stage_score()
    if a.music:
        stage_music(force=a.force)
    if a.sheets:
        stage_sheets(dict(kv.split("=", 1) for kv in a.picks.split(",") if "=" in kv))
    if a.finish:
        picks = dict(kv.split("=", 1) for kv in a.picks.split(",") if "=" in kv)
        stage_finish(picks, master=a.master)
    print("FIGHT STAGE DONE", flush=True)


if __name__ == "__main__":
    main()
