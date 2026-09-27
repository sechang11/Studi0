#!/usr/bin/env python3
"""studio/_tools/newmodels_test.py - the first measurements of the 2026-09-27 review's arrivals.

Nothing enters the pipeline on a look (CLAUDE.md). This is the first honest number for each of
the five things installed today, on the same cast, the same plate and the same instruments the
studio already trusts - so the results sit beside the numbers in playbook §98 and mean the same.

    ~/ComfyUI/venv/bin/python3 studio/_tools/newmodels_test.py --stage krea qwen21 ingredients previz animate2
    ~/ComfyUI/venv/bin/python3 studio/_tools/newmodels_test.py --stage qwen21 --seeds 11 202

STAGES
  krea         77 Krea 2 Turbo on the ash-court cast prompt (3 seeds) beside the Qwen-2512 reference
               that cast it; 78 style-reference with the court plate as the look. Time per image,
               a contact sheet. (A cast reference has no identity to score against - this is the
               look and the speed; the identity question is asked of the compositors below.)
  qwen21       80 Qwen-Image-2.1 as the @PLACE + @CHARAC1 + @CHARAC2 compositor, 3 seeds, against
               the Flux 2 ref3 anchor the fight tool composed from the same pictures. Score: each
               character's head against their own reference head (CLIP-ViT-H cosine, identity.py's
               thresholds: >= 0.62 same, 0.50-0.62 uncertain, < 0.50 different), and the room
               against the plate (border-band difference, §98.1: 11-19 same room, 73 unrelated).
  ingredients  82 LTX-2.3 + the Ingredients reference sheet. Three arms, two seeds each:
               A sheet only, B sheet + start frame, C start frame with no sheet (the control - the
               same engine, LoRA stack and words, the guide removed). Score: both heads on the LAST
               frame against their reference heads; the room on the last frame against the plate.
  previz       Blender physics previz -> 74 (LTX-2.3 IC-LoRA union control, depth) with no start
               frame, two seeds. Score: does the render MOVE when the simulation moves - Pearson r
               between the two motion-energy curves - and where its peak lands against the frame
               the simulation says the ball strikes.
  animate2     81 Wan Animate 2: one character's reference driven by another character's take,
               two seeds. Score: the reference head against the output's head on first / middle /
               last frame (head found per frame), and motion r against the driving video.

Writes studio/samples/newmodels-2026-09-27/<stage>/ with the renders, strips, a contact sheet and
measured.json. Frees ComfyUI's model cache between engine families (post.make_room).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
TOOLS = os.path.join(STUDIO, "_tools")
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run                       # noqa: E402

HOST = os.environ["COMFY_HOST"]
COMFY = os.path.expanduser("~/ComfyUI")
PY = os.path.expanduser("~/ComfyUI/venv/bin/python3")
WF = os.path.join(ROOT, "workflows")
FIGHT = os.path.join(STUDIO, "samples", "fight", "ash-court")
OUT = os.path.join(STUDIO, "samples", "newmodels-2026-09-27")
SEQ = json.load(open(os.path.join(STUDIO, "shotscripts", "ash-court.json"), encoding="utf-8"))

from PIL import Image, ImageDraw   # noqa: E402
import numpy as np                 # noqa: E402


# ------------------------------------------------------------------------------ plumbing
def load_wf(name):
    d = json.load(open(os.path.join(WF, name), encoding="utf-8"))
    return {k: v for k, v in d.items() if not k.startswith("_")}


def submit(wf, tag, tries=2):
    for attempt in range(1, tries + 1):
        try:
            t0 = time.time()
            _, outs = run(HOST, wf, quiet=True)
            return outs or [], time.time() - t0
        except Exception as e:
            print("  %s attempt %d failed: %s" % (tag, attempt, str(e)[:400]), flush=True)
            if attempt == tries:
                return [], 0.0
            time.sleep(8)
    return [], 0.0


def collect(outs, dst, kinds=(".png", ".jpg", ".mp4")):
    """The RENDER, not the input: a LoadVideo node reports the video it loaded as an output too
    (`animate2_drive.mp4`, no subfolder), and it sits first in the history - so prefer the
    files under the SaveVideo/SaveImage prefix, then anything that actually exists."""
    got = [o for o in outs if str(o).lower().endswith(kinds)]
    got.sort(key=lambda o: (0 if "claude-generated/" in str(o) else 1))
    for o in got:
        src = os.path.join(COMFY, "output", o)
        if os.path.isfile(src):
            shutil.copy(src, dst)
            return dst
    return None


def make_room(gb=20):
    try:
        import post
        post.make_room(gb)
    except Exception as e:
        print("  make_room:", str(e)[:120])


def to_input(src, name):
    dst = os.path.join(COMFY, "input", name)
    shutil.copy(src, dst)
    return name


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def frame_at(video, t, dst):
    sh("ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % t, "-i", video, "-frames:v", "1", dst)
    return dst if os.path.exists(dst) else None


def nframes(video):
    r = sh("ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
           "-show_entries", "stream=nb_read_frames,r_frame_rate", "-of", "json", video)
    try:
        s = json.loads(r.stdout)["streams"][0]
        num, den = s["r_frame_rate"].split("/")
        return int(s["nb_read_frames"]), float(num) / float(den)
    except Exception:
        return 0, 24.0


def strip(video, dst, n=8, h=150):
    fr, _ = nframes(video)
    step = max(1, fr // n)
    sh("ffmpeg", "-y", "-v", "error", "-i", video,
       "-vf", "select=not(mod(n\\,%d)),scale=-2:%d,tile=%dx1" % (step, h, n), "-frames:v", "1", dst)
    return dst


def contact(items, dst, cols=3, cell=(426, 240), title=""):
    """items: [(label, image_path)] -> a labelled grid."""
    rows = (len(items) + cols - 1) // cols
    W = cols * cell[0]
    H = rows * (cell[1] + 22) + (30 if title else 0)
    sheet = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(sheet)
    y0 = 0
    if title:
        d.text((8, 8), title, fill=(230, 230, 230))
        y0 = 30
    for i, (label, p) in enumerate(items):
        r, c = divmod(i, cols)
        x, y = c * cell[0], y0 + r * (cell[1] + 22)
        try:
            im = Image.open(p).convert("RGB")
            im.thumbnail(cell)
            sheet.paste(im, (x + (cell[0] - im.width) // 2, y + (cell[1] - im.height) // 2))
        except Exception:
            d.text((x + 8, y + 8), "(missing) " + os.path.basename(str(p)), fill=(200, 80, 80))
        d.text((x + 6, y + cell[1] + 4), label[:70], fill=(220, 220, 220))
    sheet.save(dst)
    return dst


# ---------------------------------------------------------------------------- instruments
def head_crop_file(src, dst, pad=0.4):
    """The reference HEAD as a file, found with headbox.py - what identity.py compares against."""
    import headbox
    im = Image.open(src).convert("RGB")
    w, h = im.size
    box = headbox.head_box(src)
    if not box:
        return None, None
    x0, y0, x1, y1 = box
    side = max((x1 - x0) * w, (y1 - y0) * h) * (1 + pad)
    cx, cy = (x0 + x1) / 2 * w, (y0 + y1) / 2 * h
    l, t = max(0, cx - side / 2), max(0, cy - side / 2)
    im.crop((int(l), int(t), int(min(w, l + side)), int(min(h, t + side)))).save(dst)
    return dst, box


def heads_in(frame_png, work):
    """Head boxes (fractional, full-frame) for the LEFT and RIGHT halves of a two-person frame.
    headbox finds one head per picture, so the frame is split first."""
    import headbox
    im = Image.open(frame_png).convert("RGB")
    w, h = im.size
    out = {}
    for side, (x0, x1) in (("left", (0, w // 2)), ("right", (w // 2, w))):
        p = os.path.join(work, "_half_%s_%s.png" % (side, os.path.basename(frame_png)))
        im.crop((x0, 0, x1, h)).save(p)
        try:
            b = headbox.head_box(p)
        except Exception:
            b = None
        if b:
            hw = (x1 - x0) / w
            out[side] = [x0 / w + b[0] * hw, b[1], x0 / w + b[2] * hw, b[3]]
    return out


def identity_scores(jobs, work):
    """jobs: [{id, portrait, still, box}] -> {id: (score, verdict)} through identity.py itself."""
    jp = os.path.join(work, "_identity_jobs.json")
    json.dump([dict(j, close=False) for j in jobs], open(jp, "w"))
    r = subprocess.run([PY, os.path.join(TOOLS, "identity.py"), jp], capture_output=True, text=True,
                       cwd=COMFY)
    out = {}
    for line in r.stdout.splitlines():
        try:
            d = json.loads(line)
            out[d["id"]] = (d.get("start"), d.get("verdict_start") or d.get("error"))
        except Exception:
            pass
    return out


def score_pair(frame_png, refs, work, tag):
    """Both heads in a frame against both reference heads; a character's score is the better
    half, and the report says whether the sides came out swapped."""
    boxes = heads_in(frame_png, work)
    jobs = []
    for who, head in refs.items():
        for side, box in boxes.items():
            jobs.append({"id": "%s|%s|%s" % (tag, who, side), "portrait": head, "still": frame_png,
                         "box": box})
    sc = identity_scores(jobs, work)
    res = {}
    for who in refs:
        best = None
        for side in boxes:
            s = sc.get("%s|%s|%s" % (tag, who, side), (None, None))
            if s[0] is not None and (best is None or s[0] > best[0]):
                best = (s[0], side, s[1])
        res[who] = {"score": best[0] if best else None, "side": best[1] if best else None,
                    "verdict": best[2] if best else "no head found"}
    res["_heads_found"] = sorted(boxes)
    return res


def place_hold(frame_png, plate_png, band=0.12, size=(128, 72)):
    """Border-band difference against the plate (§98.1): the outer ring of the frame is the room
    however the people in the middle move. 0-255; measured 11-19 same room, 73 unrelated."""
    a = np.asarray(Image.open(frame_png).convert("L").resize(size), dtype=np.float32)
    b = np.asarray(Image.open(plate_png).convert("L").resize(size), dtype=np.float32)
    m = np.zeros(size[::-1], dtype=bool)
    bw, bh = int(size[0] * band), int(size[1] * band)
    m[:bh, :] = m[-bh:, :] = True
    m[:, :bw] = m[:, -bw:] = True
    return round(float(np.abs(a - b)[m].mean()), 1)


def motion_curve(video, n=48):
    """Mean absolute frame-to-frame difference, resampled to n points."""
    fr, fps = nframes(video)
    if fr < 3:
        return []
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", "scale=96:54,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    frames = np.frombuffer(raw, dtype=np.uint8)
    k = len(frames) // (96 * 54)
    if k < 3:
        return []
    frames = frames[:k * 96 * 54].reshape(k, 54, 96).astype(np.float32)
    e = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    xs = np.linspace(0, len(e) - 1, n)
    return np.interp(xs, np.arange(len(e)), e).tolist()


def motion_agreement(driver, output):
    a, b = motion_curve(driver), motion_curve(output)
    if not a or not b:
        return {"r": None}
    a, b = np.array(a), np.array(b)
    r = float(np.corrcoef(a, b)[0, 1]) if a.std() > 1e-6 and b.std() > 1e-6 else None
    return {"r": round(r, 3) if r is not None else None,
            "peak_driver": int(np.argmax(a)), "peak_output": int(np.argmax(b)), "n": len(a)}


# --------------------------------------------------------------------------------- stages
def cast_refs(work):
    refs = {}
    for who in ("vesper", "koval"):
        dst = os.path.join(work, "_head_%s.png" % who)
        if not os.path.exists(dst):
            head_crop_file(os.path.join(FIGHT, "ref_%s.png" % who), dst)
        refs[who] = dst
    return refs


def stage_krea(seeds):
    d = os.path.join(OUT, "krea")
    os.makedirs(d, exist_ok=True)
    rep = {"t2i": [], "style": []}
    prompt = SEQ["cast"]["vesper"]["prompt"]
    items = [("Qwen-2512 reference (the cast picture)", os.path.join(FIGHT, "ref_vesper.png"))]
    for s in seeds:
        wf = load_wf("77_krea2_t2i.json")
        wf["6"]["inputs"]["text"] = prompt
        wf["9"]["inputs"]["width"], wf["9"]["inputs"]["height"] = 768, 1344
        wf["10"]["inputs"]["seed"] = s
        outs, secs = submit(wf, "krea t2i s%d" % s)
        p = collect(outs, os.path.join(d, "krea_vesper_s%d.png" % s))
        rep["t2i"].append({"seed": s, "secs": round(secs, 1), "file": p})
        items.append(("Krea 2 Turbo, seed %d, %.0fs" % (s, secs), p))
        print("  krea t2i s%d %.1fs -> %s" % (s, secs, p), flush=True)
    # the style reference: the court plate is the look, the prompt is the guard
    to_input(os.path.join(FIGHT, "ref_court.png"), "krea2_style_ref.png")
    style_items = [("style source: the court plate", os.path.join(FIGHT, "ref_court.png"))]
    for s in seeds[:2]:
        wf = load_wf("78_krea2_style_ref.json")
        wf["6"]["inputs"]["prompt"] = SEQ["cast"]["koval"]["prompt"]
        wf["13"]["inputs"]["noise_seed"] = s
        outs, secs = submit(wf, "krea style s%d" % s)
        p = collect(outs, os.path.join(d, "krea_style_koval_s%d.png" % s))
        rep["style"].append({"seed": s, "secs": round(secs, 1), "file": p})
        style_items.append(("Krea 2 + style ref, seed %d, %.0fs" % (s, secs), p))
        print("  krea style s%d %.1fs -> %s" % (s, secs, p), flush=True)
    contact(items, os.path.join(d, "contact_t2i.jpg"), cols=4, cell=(300, 525),
            title="Krea 2 Turbo vs the Qwen-2512 cast reference, same words (vesper)")
    contact(style_items, os.path.join(d, "contact_style.jpg"), cols=3, cell=(426, 240),
            title="Krea 2 style reference: the plate's look on the guard's description")
    json.dump(rep, open(os.path.join(d, "measured.json"), "w"), indent=1)
    return rep


def stage_qwen21(seeds):
    d = os.path.join(OUT, "qwen21")
    os.makedirs(d, exist_ok=True)
    refs = cast_refs(d)
    plate = os.path.join(FIGHT, "ref_court.png")
    to_input(plate, "qwen21_ref1.png")
    to_input(os.path.join(FIGHT, "ref_vesper.png"), "qwen21_ref2.png")
    to_input(os.path.join(FIGHT, "ref_koval.png"), "qwen21_ref3.png")
    prompt = ("A still frame from a live-action film, a MEDIUM SHOT in the place of <image1>: the woman "
              "of <image2> stands on the left and the man of <image3> on the right, facing each other "
              "an arm's length apart, both seen from the side and slightly front, faces clearly visible. "
              "Dawn light through the roof, dust in the air, fine film grain. " + SEQ["grade"])
    rep = {"prompt": prompt, "takes": []}
    items = []
    # the control: the Flux 2 ref3 anchor the fight tool composed from the same three pictures
    ctrl = os.path.join(FIGHT, "anchor_010.png")
    if os.path.exists(ctrl):
        sc = score_pair(ctrl, refs, d, "flux2_anchor_010")
        sc["place"] = place_hold(ctrl, plate)
        rep["control_flux2_ref3_anchor_010"] = sc
        items.append(("Flux 2 ref3 anchor_010 (control) v%.2f k%.2f room %.0f" % (
            sc["vesper"]["score"] or 0, sc["koval"]["score"] or 0, sc["place"]), ctrl))
    for s in seeds:
        wf = load_wf("80_qwen21_edit_refs.json")
        wf["6"]["inputs"]["prompt"] = prompt
        wf["6"]["inputs"]["negative_prompt"] = SEQ["avoid"]
        wf["10"]["inputs"]["seed"] = s
        outs, secs = submit(wf, "qwen21 s%d" % s)
        p = collect(outs, os.path.join(d, "qwen21_composite_s%d.png" % s))
        if not p:
            rep["takes"].append({"seed": s, "error": "no output"})
            continue
        sc = score_pair(p, refs, d, "qwen21_s%d" % s)
        sc["place"] = place_hold(p, plate)
        sc.update({"seed": s, "secs": round(secs, 1), "file": p})
        rep["takes"].append(sc)
        items.append(("Qwen-2.1 s%d %.0fs  v%.2f k%.2f room %.0f" % (
            s, secs, sc["vesper"]["score"] or 0, sc["koval"]["score"] or 0, sc["place"]), p))
        print("  qwen21 s%d %.1fs v=%s k=%s room=%s" % (s, secs, sc["vesper"]["score"], sc["koval"]["score"],
                                                        sc["place"]), flush=True)
    contact(items, os.path.join(d, "contact.jpg"), cols=2, cell=(560, 315),
            title="Qwen-Image-2.1 three-reference compositor vs the Flux 2 ref3 anchor (head cosine; room band)")
    json.dump(rep, open(os.path.join(d, "measured.json"), "w"), indent=1)
    return rep


ING_SHEET = ("### Reference Sheet Description\n"
             "**Top row, first two panels (Character A):** a young woman with very short dark hair - her "
             "face in close-up, then her whole figure in a grey vest and grey trousers, hand wraps.\n"
             "**Top row, last two panels (Character B):** a heavy bald man - his face in close-up, then "
             "his whole figure in a long dark grey coat, arms folded.\n"
             "**Bottom row (Location, two panels):** a ruined circular stone arena with a raised concrete "
             "platform, cracked flagstones, iron railings on the upper tiers, hanging lamps and a broken "
             "glass roof letting in pale dawn light; then a closer view of the same arena.\n")
ING_TARGET = ("A MEDIUM CLOSE SHOT inside the ruined stone arena of the location panels, its hanging lamps "
              "and railings and pale dawn light behind them: Character A stands on the left and Character B "
              "on the right, both faces large and clearly lit, an arm's length apart, facing each other. He "
              "speaks a short, quiet line; she listens and does not move. Static camera. Ambient sound of a "
              "large empty hall, dust, his voice; no music.")
ING_TARGET_PLAIN = ING_TARGET.replace("of the location panels", "").replace("Character A", "the young woman "
                                                                             "with very short dark hair in a grey vest").replace(
    "Character B", "the heavy bald man in a long dark grey coat")
ING_OPTS = {"bucket": False, "ckpt": None}


def _ingredients_graph(arm, seed, prompt):
    wf = load_wf("82_ltx23_ingredients.json")
    wf["sg1_128"]["inputs"]["text"] = prompt
    wf["sg1_112"]["inputs"]["text"] = SEQ["avoid"]
    wf["sg1_704"]["inputs"]["seed"] = seed
    wf["68"]["inputs"]["filename_prefix"] = "claude-generated/ingredients/%s_s%d" % (arm, seed)
    if ING_OPTS["bucket"]:
        # the adapter's training bucket (model card): 768x448, 121 frames at 24 fps
        wf["722"]["inputs"]["target_width"], wf["722"]["inputs"]["target_height"] = 768, 448
        wf["715"]["inputs"]["value"] = 5
        wf["717"]["inputs"]["expression"] = "a * b + 1"
    if ING_OPTS["ckpt"]:
        # the template's own base: the distilled checkpoint, no distill LoRA
        for nid in ("sg1_127", "sg1_126", "sg1_103"):
            wf[nid]["inputs"]["ckpt_name"] = ING_OPTS["ckpt"]
        wf["sg1_195"]["inputs"]["model"] = ["sg1_127", 0]
        wf.pop("distill", None)
    base_model = ["sg1_127", 0] if ING_OPTS["ckpt"] else ["distill", 0]
    if arm in ("B", "C"):
        wf["sg1_711"]["inputs"]["value"] = False
        wf["sg1_198"]["inputs"]["image"] = ["725", 0]
    if arm == "C":
        # the guide removed: same engine, same stack without the adapter, the TARGET words only
        wf["sg1_128"]["inputs"]["text"] = ING_TARGET_PLAIN
        wf["sg1_119"]["inputs"]["video_latent"] = ["sg1_198", 0]
        wf["sg1_704"]["inputs"]["positive"] = ["sg1_109", 0]
        wf["sg1_704"]["inputs"]["negative"] = ["sg1_109", 1]
        wf["sg1_704"]["inputs"]["model"] = base_model
        wf["sg1_105"]["inputs"]["samples"] = ["sg1_121", 0]
        for nid in ("sg1_115", "sg1_196", "sg1_106", "sg1_195"):
            wf.pop(nid, None)
    return wf


def stage_ingredients(seeds):
    tag = "ingredients" + ("_bucket" if ING_OPTS["bucket"] else "") + ("_distilled" if ING_OPTS["ckpt"] else "")
    d = os.path.join(OUT, tag)
    os.makedirs(d, exist_ok=True)
    refs = cast_refs(d)
    plate = os.path.join(FIGHT, "ref_court.png")
    sheet = os.path.join(FIGHT, "sheet_vk_grey.png")
    subprocess.run([PY, os.path.join(TOOLS, "refsheet.py"), "--out", sheet, "--bg", "grey",
                    "--char", os.path.join(FIGHT, "ref_vesper.png"),
                    "--char", os.path.join(FIGHT, "ref_koval.png"), "--place", plate], check=False)
    to_input(sheet, "ingredients_sheet.png")
    to_input(os.path.join(FIGHT, "anchor_010.png"), "ingredients_anchor.png")
    prompt = ING_SHEET + "### Target Description\n" + ING_TARGET
    rep = {"prompt": prompt, "control_prompt": ING_TARGET_PLAIN, "options": dict(ING_OPTS), "sheet": sheet,
           "arms": {"A": "sheet only", "B": "sheet + start frame", "C": "start frame, no sheet, target words only (control)"},
           "takes": []}
    items = []
    for arm in ("A", "B", "C"):
        for s in seeds:
            wf = _ingredients_graph(arm, s, prompt)
            outs, secs = submit(wf, "ingredients %s s%d" % (arm, s))
            v = collect(outs, os.path.join(d, "ing_%s_s%d.mp4" % (arm, s)), kinds=(".mp4",))
            if not v:
                rep["takes"].append({"arm": arm, "seed": s, "error": "no output"})
                continue
            fr, fps = nframes(v)
            first = frame_at(v, 0.0, os.path.join(d, "ing_%s_s%d_first.png" % (arm, s)))
            last = frame_at(v, max(0.0, fr / fps - 1.5 / fps), os.path.join(d, "ing_%s_s%d_last.png" % (arm, s)))
            strip(v, os.path.join(d, "ing_%s_s%d_strip.jpg" % (arm, s)))
            sc_last = score_pair(last, refs, d, "ing_%s_s%d_last" % (arm, s)) if last else {}
            sc_first = score_pair(first, refs, d, "ing_%s_s%d_first" % (arm, s)) if first else {}
            t = {"arm": arm, "seed": s, "secs": round(secs, 1), "frames": fr, "file": v,
                 "last": sc_last, "first": sc_first,
                 "place_first": place_hold(first, plate) if first else None,
                 "place_last": place_hold(last, plate) if last else None}
            rep["takes"].append(t)
            items.append(("%s s%d last: v%.2f k%.2f room %.0f (%.0fs)" % (
                arm, s, (sc_last.get("vesper") or {}).get("score") or 0,
                (sc_last.get("koval") or {}).get("score") or 0, t["place_last"] or 0, secs), last))
            print("  ingredients %s s%d %.0fs frames=%d last v=%s k=%s room=%s" % (
                arm, s, secs, fr, (sc_last.get("vesper") or {}).get("score"),
                (sc_last.get("koval") or {}).get("score"), t["place_last"]), flush=True)
    contact(items, os.path.join(d, "contact_last_frames.jpg"), cols=len(seeds), cell=(560, 315),
            title="LTX-2.3 Ingredients: A sheet only / B sheet + anchor / C anchor only - last frames")
    json.dump(rep, open(os.path.join(d, "measured.json"), "w"), indent=1)
    return rep


def stage_previz(seeds):
    d = os.path.join(OUT, "previz")
    os.makedirs(d, exist_ok=True)
    pv = os.path.join(STUDIO, "samples", "previz", "crates", "previz.mp4")
    if not os.path.exists(pv):
        print("  no previz at %s - run previz_blender.py first" % pv)
        return {"error": "no previz"}
    info = json.load(open(os.path.join(os.path.dirname(pv), "previz.json")))
    to_input(pv, "iclora_control.mp4")
    fr, fps = nframes(pv)
    prompt = ("Inside a dim brick warehouse a heavy black iron ball rolls in fast from the left and smashes "
              "through a stacked wall of old wooden crates; the crates burst apart, tumble and scatter "
              "across the concrete floor in a cloud of dust. A woman in a long dark coat stands at the "
              "right of frame and flinches as they fall. The camera arcs slowly around the action. "
              "Sound: the rumble of the ball, a loud crack of splintering wood, boxes clattering, dust "
              "settling; no music.")
    rep = {"previz": info, "prompt": prompt, "takes": []}
    items = [("Blender previz (control, depth read by MoGe)", strip(pv, os.path.join(d, "previz_strip.jpg")))]
    for s in seeds:
        wf = load_wf("74_ltx23_ic_lora_control.json")
        wf["sg1_128"]["inputs"]["text"] = prompt
        wf["sg1_112"]["inputs"]["text"] = SEQ["avoid"]
        wf["sg1_704"]["inputs"]["seed"] = s
        wf["sg1_198"]["inputs"]["bypass"] = True          # no start frame: the previz alone
        wf["sg1_108"]["inputs"]["length"] = fr
        wf["sg1_101"]["inputs"]["frames_number"] = fr
        wf["sg1_114"]["inputs"]["value"] = int(round(fps))
        wf["68"]["inputs"]["filename_prefix"] = "claude-generated/previz/crates_s%d" % s
        outs, secs = submit(wf, "previz s%d" % s)
        v = collect(outs, os.path.join(d, "crates_s%d.mp4" % s), kinds=(".mp4",))
        if not v:
            rep["takes"].append({"seed": s, "error": "no output"})
            continue
        ma = motion_agreement(pv, v)
        t = {"seed": s, "secs": round(secs, 1), "frames": nframes(v)[0], "file": v, "motion": ma}
        rep["takes"].append(t)
        items.append(("LTX-2.3 IC-LoRA depth s%d  r=%s peak %s vs %s" % (
            s, ma.get("r"), ma.get("peak_output"), ma.get("peak_driver")),
            strip(v, os.path.join(d, "crates_s%d_strip.jpg" % s))))
        print("  previz s%d %.0fs motion r=%s peaks %s/%s" % (s, secs, ma.get("r"), ma.get("peak_output"),
                                                             ma.get("peak_driver")), flush=True)
    contact(items, os.path.join(d, "contact.jpg"), cols=1, cell=(1200, 150),
            title="physics previz -> depth-controlled render (strips)")
    json.dump(rep, open(os.path.join(d, "measured.json"), "w"), indent=1)
    return rep


def stage_animate2(seeds):
    d = os.path.join(OUT, "animate2")
    os.makedirs(d, exist_ok=True)
    refs = cast_refs(d)
    drive = os.path.join(FIGHT, "h3_010_s3003.mp4")
    to_input(os.path.join(FIGHT, "ref_vesper.png"), "animate2_ref.png")
    to_input(drive, "animate2_drive.mp4")
    rep = {"driver": drive, "reference": "ref_vesper.png", "takes": []}
    items = [("driver: koval's H3 take (h3_010_s3003)", strip(drive, os.path.join(d, "driver_strip.jpg")))]
    for s in seeds:
        wf = load_wf("81_wan_animate2.json")
        wf["34"]["inputs"]["noise_seed"] = s
        wf["8"]["inputs"]["text"] = ("Character Description: the young woman in the reference image, very short "
                                     "dark hair, grey vest, grey trousers, hand wraps - the same face.\n"
                                     "Background description: a ruined circular stone arena at dawn, dust in "
                                     "the air, static camera.")
        wf["38"]["inputs"]["filename_prefix"] = "claude-generated/animate2/vesper_s%d" % s
        outs, secs = submit(wf, "animate2 s%d" % s)
        v = collect(outs, os.path.join(d, "vesper_on_koval_s%d.mp4" % s), kinds=(".mp4",))
        if not v:
            rep["takes"].append({"seed": s, "error": "no output"})
            continue
        fr, fps = nframes(v)
        jobs, frames = [], {}
        import headbox
        for tag, t in (("first", 0.0), ("mid", fr / fps / 2), ("last", max(0.0, fr / fps - 1.5 / fps))):
            p = frame_at(v, t, os.path.join(d, "vesper_s%d_%s.png" % (s, tag)))
            if not p:
                continue
            try:
                box = headbox.head_box(p)
            except Exception:
                box = None
            frames[tag] = p
            jobs.append({"id": tag, "portrait": refs["vesper"], "still": p, "box": box})
        sc = identity_scores(jobs, d)
        ma = motion_agreement(drive, v)
        t = {"seed": s, "secs": round(secs, 1), "frames": fr, "file": v,
             "identity": {k: {"score": v_[0], "verdict": v_[1]} for k, v_ in sc.items()}, "motion": ma}
        rep["takes"].append(t)
        items.append(("Animate 2 s%d id %s/%s/%s r=%s" % (
            s, sc.get("first", (None,))[0], sc.get("mid", (None,))[0], sc.get("last", (None,))[0], ma.get("r")),
            strip(v, os.path.join(d, "vesper_s%d_strip.jpg" % s))))
        print("  animate2 s%d %.0fs id=%s motion r=%s" % (s, secs, {k: v_[0] for k, v_ in sc.items()}, ma.get("r")),
              flush=True)
    contact(items, os.path.join(d, "contact.jpg"), cols=1, cell=(1200, 150),
            title="Wan Animate 2: vesper's reference driven by koval's take")
    json.dump(rep, open(os.path.join(d, "measured.json"), "w"), indent=1)
    return rep


STAGES = {"krea": (stage_krea, 8), "qwen21": (stage_qwen21, 12), "ingredients": (stage_ingredients, 26),
          "previz": (stage_previz, 26), "animate2": (stage_animate2, 26)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", nargs="+", default=list(STAGES), choices=list(STAGES))
    ap.add_argument("--seeds", type=int, nargs="+", default=[11, 202, 3003])
    ap.add_argument("--bucket", action="store_true", help="ingredients: render at the adapter's 768x448 x 121 bucket")
    ap.add_argument("--ckpt", default=None, help="ingredients: a distilled checkpoint name instead of dev + distill LoRA")
    a = ap.parse_args()
    ING_OPTS["bucket"], ING_OPTS["ckpt"] = a.bucket, a.ckpt
    os.makedirs(OUT, exist_ok=True)
    summary = {}
    for st in a.stage:
        fn, gb = STAGES[st]
        print("== %s ==" % st, flush=True)
        make_room(gb)
        t0 = time.time()
        seeds = a.seeds if st in ("krea", "qwen21") else a.seeds[:2]
        try:
            summary[st] = fn(seeds)
        except Exception as e:
            import traceback
            traceback.print_exc()
            summary[st] = {"error": str(e)[:300]}
        print("   (%s: %.0f s)" % (st, time.time() - t0), flush=True)
    json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"), indent=1, default=str)
    print("summary ->", os.path.join(OUT, "summary.json"))


if __name__ == "__main__":
    main()
