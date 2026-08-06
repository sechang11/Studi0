#!/usr/bin/env python3
"""Photo -> anime: find the IPAdapter weight band where the FACE and the ANIME both survive.

    python3 studio/_tools/photo_to_anime.py --stage sweep     # the 8-weight x 4-style grid
    python3 studio/_tools/photo_to_anime.py --stage alt       # FLUX.2 prose + Qwen edit
    python3 studio/_tools/photo_to_anime.py --stage sheets    # rebuild sheets from renders
    python3 studio/_tools/photo_to_anime.py --stage all

THIS TOOL DOES ITS WHOLE JOB ON --stage all AND NOTHING ON --help. It renders ~70 SDXL
images and writes them under studio/samples/photo2anime/sweep/. Nothing else on disk is
touched.

THE QUESTION

A reference image through IPAdapter SUPPRESSES STYLE. Measured on Terra: four different
styles came back as one render repeated, and setting IPAdapter to 0.0 was what let style
through. So high weight keeps the face and kills the anime; low weight gives anime that may
not be her. Where the usable band sits had never been measured. This measures it.

WHY THE GRID HAS THE SHAPE IT HAS

  eight weights   0.0 0.2 0.3 0.4 0.5 0.6 0.8 1.0, fixed seed, fixed prompt. Plus a NOREF
                  cell that removes IPAdapterAdvanced from the graph entirely, because
                  "weight 0.0 is off" is an assumption and NOREF vs 0.0 tests it.

  four styles     suppression may bite differently on a flat cel style than a painterly
                  one, so: modern_anime (flat cel), cel_anime_90s (retro cel, grainier),
                  kyoani_soft (soft painterly), manga_screentone (MONOCHROME). The
                  monochrome one is the litmus: if a render comes back in colour, the
                  reference beat the style, and that is measurable in one number (SATAVG)
                  rather than argued about.

  two prompt      craft/ANIME_MODELS.md records that a detailed tag block carries MOST of
  modes           the identity by itself - a character was recognisable at IPAdapter ZERO.
                  So a sweep with her markers in the tags cannot separate what IPAdapter
                  contributes from what the words contribute. TAGGED is the practical
                  route; NEUTRAL strips every marker from the prompt so the reference is
                  the only thing that could put glasses, a mole or a mustard jacket on her.
                  Read NEUTRAL to learn what IPAdapter does. Read TAGGED to pick a setting.

THE NUMBERS NEXT TO EACH CELL

  sat   mean saturation (ffmpeg signalstats SATAVG). On manga_screentone the style demands
        ~0. A high number there is style suppression, stated in one figure.
  flat  a cel-flatness proxy: KB of the cell re-encoded to JPEG q=4 at a fixed 640x824.
        Flat cel art has large uniform regions and compresses small; a photograph, or a
        photo with flatter shading, does not. LOWER IS MORE DRAWN. It is a proxy and it is
        labelled as one - the sheets are still meant to be looked at.

They are decision support, not the decision. Every sheet in sheets/ has to be opened.

================================================================================
WHAT IT MEASURED, 2026-08-06, RTX 5090, animagine-xl-4.0, seed 20260806, 896x1152,
28 steps, cfg 5.0, PLUS FACE, reference standin/set/02_front_flat.png. Every sheet
in sheets/ was opened and looked at. VERDICT.json carries the same thing as data.
================================================================================

THE BAND IS 0.40-0.60, DEFAULT 0.50 - AND WHAT SURVIVES IN IT IS NOT HER FACE.

IDENTITY, from the NEUTRAL sweep, where no marker word is in the prompt so anything that
appears came from the reference. Weight at which each marker first appears:

    style              hair len   jacket   glasses   mole    face structure
    cel_anime_90s        0.30      0.40     0.30     never      never
    modern_anime         0.40      0.40     0.50     never      never
    manga_screentone     0.30      1.00     0.50     never      never
    kyoani_soft          never     0.60     0.80     never      never

  * Below 0.30 the reference contributes NOTHING - 0.20 is indistinguishable from none.
  * The threshold is STYLE-DEPENDENT, 0.30 to 0.80. A style with its own strong light and
    palette (kyoani_soft: warm ambient, drawn bokeh) resists the reference and needs nearly
    double the weight of one that is neutral about light (cel_anime_90s).
  * THE MOLE NEVER APPEARS AND THE FACE IS NEVER HERS. What PLUS FACE transports from a
    PHOTOGRAPH into this checkpoint is a bundle of ATTRIBUTES - hair mass and length,
    garment colour and shape, the presence of eyewear - plus the reference's lighting and
    background. Not identity. It cannot carry a small dark spot on a cheek at any weight.
  * The TAGGED sweep cannot answer this question at all: with her markers in the tags,
    glasses and a mustard jacket are already there at 0.00. craft/ANIME_MODELS.md predicted
    that and it reproduced exactly.

STYLE, against the NOREF control. NOREF and weight 0.00 came back PIXEL-IDENTICAL in all
four styles - same SATAVG to a decimal, same JPEG size to 0.1 KB. Weight 0.0 is a true
no-op and every column is honestly comparable.

The Terra finding - a reference suppresses style - REPRODUCES, but not as written. Nothing
here ever stopped being a drawing; there is no weight at which a photograph comes back.
What dies is narrower:

    from 0.20   THE CARD'S LIGHT AND BACKGROUND. kyoani_soft at NOREF has warm ambient
                light and real drawn bokeh; by 0.20 both are gone and by 0.60 the ground is
                the reference's plain pale wall under the reference's flat even light. The
                photo imports its own lighting and imposes it.
    from 0.60   THE CARD'S DISTINGUISHING SURFACE. cel_anime_90s keeps its heavy uneven
                line and hard cel shadow to 0.60, then drifts into generic modern
                soft-gradient anime. Still anime; no longer 1990s OVA.
    from 0.80   COMPOSITION AND PROPS - the real ceiling. Framing zooms and tilts, a hand
                comes up to the face unbidden, a manga poster appears in her hands
                (manga_screentone 0.80 and 1.00), a bandage appears on her head (1.00), and
                the crop drifts chest-forward in every style.
    monochrome  SURVIVES. manga_screentone NEUTRAL holds SATAVG ~1 to 0.80 and only leaks
                at 1.00 (6.5). The colour flooding the TAGGED screentone sweep from 0.20
                (SATAVG 8 -> 20) is the words `yellow jacket` beating `monochrome`, NOT the
                reference. Two suppressors were being read as one.

THE ALTERNATIVES, ranked. See sheets/ALTERNATIVES.jpg.

  1. QWEN-IMAGE-EDIT 2511 WITH A REDRAW PROMPT. THE WINNER, and it is not close.
     alt/qwen_hard_lora00.png is unmistakably HER - face proportions, uneven brows, crooked
     nose, the cheek mole, gold stud earrings, the same double-bridged round gold glasses,
     the same parting and hair length, the mustard corduroy jacket with its topstitching,
     the white crew tee - and unmistakably DRAWN: uniform black outline, flat unshaded
     fills, no photographic texture. 4 steps, about 5 s.
     WHY THE MEASURED TRAP DID NOT BITE. "A reference imports its medium" is true of a
     prompt that bolts a style onto a photographic subject. This prompt NAMES THE MEDIUM IN
     ITS FIRST SENTENCE and only then says what to keep. Same rule already measured on Qwen
     t2i; it holds on the edit path.
     qwen_image_modern_anime_lora at 1.0 is NOT NEEDED - it only darkens the hair to black.
     Leave it off.
     THE HONEST CAVEAT: this reads as ligne claire / flat vector illustration, not TV-anime
     cel. Realistic proportions, no anime eye stylisation. A viewer says "that is a drawing
     of her", not "that is an anime character". If the brief needs anime CHARACTER DESIGN
     this is not it; if it needs HER, drawn, it is the only thing that works.

  2. FLUX.2, PROSE ONLY. No IPAdapter exists on this path, so identity can only come from
     the description. It gets every marker right and draws the best of the three engines,
     corduroy wale included - but the face is FLUX's reading of the sentence, narrower and
     longer, a different nose. For a synthetic stand-in who IS her description this is
     usable and buys free choice of pose and scene. For a real likeness it is a police
     sketch, not identity.

  3. IPADAPTER ON ANIMAGINE at 0.40-0.60. Genuine full anime a viewer would not question,
     free choice of style from the shipped library, attribute-level identity only.

FOR THE 3D ROUTE. alt/qwen_ideal_apose.png is the winning recipe run on
standin/ideal/IDEAL_apose_1152x2048.png. The A-pose is preserved EXACTLY - arms clear,
hands closed, feet planted - because the edit path keeps the input pose and framing, which
no text-to-image route does. And the drawing is precisely the geometric simplification the
mesh thesis wants: hair became one closed mass, corduroy wale and every cloth fold
collapsed to clean planes, ground went flat white. It avoids Terra's failure mode by
construction - no separated hair locks to become tubes, and the hands came through closed.
This is what 24_hunyuan3d_mesh.json should be fed.

ONE OPERATIONAL NOTE, PAID FOR HERE. The first run submitted cells one at a time and was
starved by another session queueing LoRA training: 25 cells in 40 minutes and slowing.
Submitting the whole grid as ONE BATCH and waiting on it drained the remaining 47 cells in
under 9 minutes on the same contended queue. epic.wait_all says this in its docstring.
"""
import argparse, json, os, shutil, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                      # noqa: E402
from epic import load_wf, ensure_local, submit, wait_all, HOST   # noqa: E402

COMFY_IN = os.path.expanduser("~/ComfyUI/input")
BASE = os.path.join(STUDIO, "samples", "photo2anime")
STANDIN = os.path.join(BASE, "standin")
OUT = os.path.join(BASE, "sweep")
REN = os.path.join(OUT, "renders")
ALT = os.path.join(OUT, "alt")
SHEETS = os.path.join(OUT, "sheets")
WORK = os.path.join(OUT, "_work")

WF_IP = "22_anime_kf_ipadapter.json"
WF_FLUX = "40_flux2_t2i.json"
WF_QWEN = "22_qwen_edit_2511.json"

REF_SRC = os.path.join(STANDIN, "set", "02_front_flat.png")   # front-on, flat light, good
REF_NAME = "p2a_ref_front.png"

SEED = 20260806
W, H = 896, 1152
WEIGHTS = [0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0]

Q = "masterpiece, best quality, very aesthetic, absurdres"

# Her concrete markers, as danbooru tags. This is the TAGGED half of the experiment.
MARKS = ("dark brown hair, medium hair, hair over shoulders, parted bangs, brown eyes, "
         "round eyewear, gold-rimmed eyewear, glasses, mole on cheek, mole under eye, "
         "yellow jacket, corduroy jacket, white shirt")
BASE_TAGS = ("1girl, solo, adult, mature female, upper body, looking at viewer, "
             "closed mouth, neutral expression, simple background")

# No sex terms that fight the subject. The stock node-6 negative bans 1girl outright,
# which is why it is replaced wholesale rather than appended to.
NEG = ("1boy, male focus, lowres, worst quality, bad anatomy, bad hands, extra limbs, "
       "watermark, signature, text, multiple views, motion blur, blurry, overexposed, "
       "washed out, photorealistic, 3d, western comic")

# Tag strings lifted verbatim from studio/styles/*.json so the sweep tests the shipped
# library rather than something written for this tool.
STYLES = [
    ("modern_anime", "flat cel"),
    ("cel_anime_90s", "retro cel"),
    ("kyoani_soft", "soft painterly"),
    ("manga_screentone", "MONOCHROME litmus"),
]


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def style_tags(name):
    p = os.path.join(STUDIO, "styles", name + ".json")
    d = json.load(open(p, encoding="utf-8"))
    return (d.get("prompt") or d.get("tags") or "").strip().rstrip(",")


def stats(path):
    """SATAVG/YAVG from signalstats, plus the JPEG-size flatness proxy."""
    out = {"sat": None, "y": None, "flat": None}
    r = sh("ffprobe", "-v", "error", "-f", "lavfi", "-i",
           "movie=%s,signalstats" % path.replace(":", "\\:"),
           "-show_entries", "frame_tags=lavfi.signalstats.SATAVG,lavfi.signalstats.YAVG",
           "-of", "default=nw=0")
    # PARSE BY KEY, NOT BY POSITION. ffprobe emits these tags in the order the filter
    # wrote them into the frame metadata (YAVG first), not the order they were requested,
    # so nk=1 positional parsing silently swaps luma into the saturation column.
    for line in r.stdout.splitlines():
        k, _, v = line.strip().partition("=")
        try:
            if k.endswith("SATAVG"):
                out["sat"] = float(v)
            elif k.endswith("YAVG"):
                out["y"] = float(v)
        except ValueError:
            pass
    tmp = os.path.join(WORK, "_flat.jpg")
    sh("ffmpeg", "-y", "-v", "error", "-i", path, "-vf", "scale=640:824", "-q:v", "4", tmp)
    if os.path.exists(tmp):
        out["flat"] = round(os.path.getsize(tmp) / 1024.0, 1)
    return out


def build(style, mode, weight, noref=False):
    wf = load_wf(WF_IP)
    st = style_tags(style)
    subject = BASE_TAGS + (", " + MARKS if mode == "tagged" else "")
    set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
    set_path(wf, "2.inputs.image", REF_NAME)
    set_path(wf, "4.inputs.weight", float(weight))
    set_path(wf, "5.inputs.text", ", ".join([subject, st, Q]))
    set_path(wf, "6.inputs.text", NEG)
    set_path(wf, "8.inputs.seed", SEED)
    set_path(wf, "8.inputs.steps", 28)
    set_path(wf, "8.inputs.cfg", 5.0)
    for n in ("7", "10"):
        set_path(wf, "%s.inputs.width" % n, W)
        set_path(wf, "%s.inputs.height" % n, H)
    if noref:
        # Cut IPAdapterAdvanced out of the graph completely. This is what "full style"
        # looks like, and it is the control every style column is compared against.
        set_path(wf, "8.inputs.model", ["1", 0])
        del wf["4"]
        del wf["3"]
        del wf["2"]
    return wf


def render(wf, tag, dest):
    """comfy.run() calls sys.exit(1) on a server error rather than raising, so SystemExit
    is caught too - otherwise one bad cell ends a seventy-cell sweep. And ensure_local()
    short-circuits on an existing dest, so a rerun would keep the stale file: remove it."""
    set_path(wf, "11.inputs.filename_prefix", "claude-generated/p2a/%s" % tag)
    if os.path.exists(dest):
        os.remove(dest)
    try:
        _, outs = run(HOST, wf, quiet=True)
    except (Exception, SystemExit) as e:
        print("    %-34s FAILED %s" % (tag, str(e)[:80]))
        return None
    if not outs:
        print("    %-34s no output" % tag)
        return None
    return ensure_local(outs[0], dest, required=False)


# ---------------------------------------------------------------- stages

def stage_sweep():
    """SUBMIT THE WHOLE GRID AT ONCE, then wait.

    This was one-at-a-time and it starved. The box is shared: another session was queueing
    LoRA training jobs back to back, and a tool that submits one cell, waits for it, then
    submits the next goes to the BACK of the queue every single time - twenty-five cells in
    forty minutes, and falling. Queued as one contiguous batch the same grid drains
    whenever the queue reaches it. epic.wait_all's own docstring says exactly this.

    Cells whose PNG already exists are skipped, so this is resumable.
    """
    shutil.copy(REF_SRC, os.path.join(COMFY_IN, REF_NAME))
    print("reference -> ComfyUI/input/%s  (%s)" % (REF_NAME, os.path.basename(REF_SRC)))
    jobs, skipped = [], 0
    for style, kind in STYLES:
        d = os.path.join(REN, style)
        os.makedirs(d, exist_ok=True)
        for mode in ("tagged", "neutral"):
            cells = [("NOREF", None)] + [("w%03d" % int(round(w * 100)), w) for w in WEIGHTS]
            for key, w in cells:
                p = os.path.join(d, "%s_%s.png" % (mode, key))
                mkey = "%s|%s|%s" % (style, mode, "NOREF" if w is None else "%.2f" % w)
                if os.path.exists(p):
                    skipped += 1
                    continue
                wf = build(style, mode, w or 0.0, noref=(w is None))
                set_path(wf, "11.inputs.filename_prefix",
                         "claude-generated/p2a/%s_%s_%s" % (style, mode, key))
                jobs.append((wf, p, mkey))
    print("%d cells already on disk, %d to render" % (skipped, len(jobs)))

    metrics = {}
    if jobs:
        pids = {}
        for wf, p, mkey in jobs:
            try:
                pids[submit(wf)] = (p, mkey)
            except Exception as e:
                print("  submit failed for %s: %s" % (mkey, str(e)[:90]))
        print("queued %d prompts as one batch" % len(pids))
        wait_all(list(pids), "cells")
        for pid, (p, mkey) in pids.items():
            try:
                h = json.load(urllib.request.urlopen(
                    "http://%s/history/%s" % (HOST, pid), timeout=60))
            except Exception:
                continue
            outs = []
            for _, out in (h.get(pid, {}).get("outputs") or {}).items():
                for f in out.get("images", []):
                    outs.append(("%s/%s" % (f.get("subfolder", ""), f["filename"]))
                                .lstrip("/"))
            if not outs:
                print("  no output for %s" % mkey)
                continue
            if ensure_local(outs[0], p, required=False):
                metrics[mkey] = stats(p)
    # anything on disk but not measured this run still needs a number
    for style, _ in STYLES:
        d = os.path.join(REN, style)
        for mode in ("tagged", "neutral"):
            for key, w in [("NOREF", None)] + [("w%03d" % int(round(x * 100)), x)
                                               for x in WEIGHTS]:
                p = os.path.join(d, "%s_%s.png" % (mode, key))
                mkey = "%s|%s|%s" % (style, mode, "NOREF" if w is None else "%.2f" % w)
                if os.path.exists(p) and mkey not in metrics:
                    metrics[mkey] = stats(p)
    old = {}
    if os.path.exists(os.path.join(OUT, "METRICS.json")):
        old = json.load(open(os.path.join(OUT, "METRICS.json"), encoding="utf-8"))
    old.update(metrics)
    json.dump(old, open(os.path.join(OUT, "METRICS.json"), "w", encoding="utf-8"),
              indent=1, sort_keys=True)
    print("\nMETRICS.json written (%d cells)" % len(old))


FLUX_PROSE = (
    "a woman in her early thirties, an oval face with a slightly crooked nose and uneven "
    "eyebrows, warm light-olive skin, dark brown eyes, thin round gold wire-frame glasses, "
    "a small dark mole on her right cheek an inch below the eye, dark brown hair falling "
    "just past her shoulders parted on the left, a mustard yellow corduroy jacket over a "
    "plain white t-shirt, small gold stud earrings, head and shoulders, straight on to the "
    "viewer, neutral expression, a plain pale wall behind her")

FLUX_STYLES = [
    ("flat_cel", "A 2D anime illustration, drawn not photographed. Clean crisp black "
                 "lineart of even weight, flat cel shading in two tones with hard-edged "
                 "shadow, simple unmodulated colour fills, no photographic texture, no "
                 "skin pores, no depth of field. Modern television anime key art. "),
    ("retro_cel", "A hand-painted 1990s OVA anime cel, drawn not photographed. Heavier "
                  "uneven ink line, duller warm cel paint, hard flat shadow shapes, "
                  "visible film grain over the paint, no photographic texture. "),
    ("soft_paint", "A soft painterly anime illustration in the Kyoto Animation manner, "
                   "drawn not photographed. Delicate thin lineart, gentle gradient "
                   "shading, warm natural light, drawn bokeh circles behind her, no "
                   "photographic texture and no skin pores. "),
]

QWEN_PROMPTS = [
    ("plain", "Redraw this photograph as a flat 2D anime illustration. Clean crisp black "
              "lineart, flat cel shading in two tones, simple colour fills, drawn on paper "
              "rather than photographed. Keep her face, her round gold glasses, the mole on "
              "her cheek, her hair length and her mustard corduroy jacket exactly as they "
              "are."),
    ("hard", "Turn this into a drawing. It is now a hand-inked anime cel: black outlines "
             "around every shape, flat unshaded colour, no photographic texture at all, no "
             "skin pores, no soft light falloff. The same woman, the same round gold "
             "glasses, the same cheek mole, the same shoulder-length dark brown hair, the "
             "same mustard corduroy jacket."),
]


def stage_alt():
    """Same batch discipline as the sweep, and for the same reason - the box is shared."""
    os.makedirs(ALT, exist_ok=True)
    shutil.copy(REF_SRC, os.path.join(COMFY_IN, REF_NAME))
    pids = {}
    print("\nFLUX.2 - prose only, no reference image exists on this path at all")
    for name, pre in FLUX_STYLES:
        wf = load_wf(WF_FLUX)
        set_path(wf, "6.inputs.text", pre + FLUX_PROSE + ".")
        set_path(wf, "7.inputs.guidance", 4.0)
        set_path(wf, "11.inputs.noise_seed", SEED)
        for n in ("9", "12"):
            set_path(wf, "%s.inputs.width" % n, 832)
            set_path(wf, "%s.inputs.height" % n, 1216)
        set_path(wf, "9.inputs.steps", 8)
        set_path(wf, "15.inputs.filename_prefix", "claude-generated/p2a/flux2_%s" % name)
        p = os.path.join(ALT, "flux2_%s.png" % name)
        if os.path.exists(p):
            continue
        pids[submit(wf)] = p

    print("Qwen-Image-Edit 2511 - the reference IS the input, which imports its medium")
    for name, pr in QWEN_PROMPTS:
        for lora in (0.0, 1.0):
            wf = load_wf(WF_QWEN)
            set_path(wf, "7.inputs.image", REF_NAME)
            set_path(wf, "10.inputs.prompt", pr)
            set_path(wf, "15.inputs.seed", SEED)
            if lora > 0:
                wf["50"] = {"class_type": "LoraLoaderModelOnly",
                            "inputs": {"model": ["4", 0],
                                       "lora_name": "qwen_image_modern_anime_lora.safetensors",
                                       "strength_model": float(lora)}}
                set_path(wf, "5.inputs.model", ["50", 0])
            tag = "%s_lora%s" % (name, str(lora).replace(".", ""))
            set_path(wf, "17.inputs.filename_prefix", "claude-generated/p2a/qwen_%s" % tag)
            p = os.path.join(ALT, "qwen_%s.png" % tag)
            if os.path.exists(p):
                continue
            pids[submit(wf)] = p

    if not pids:
        print("  all alternative renders already on disk")
        return
    print("queued %d alternative prompts as one batch" % len(pids))
    wait_all(list(pids), "alts")
    for pid, p in pids.items():
        try:
            h = json.load(urllib.request.urlopen(
                "http://%s/history/%s" % (HOST, pid), timeout=60))
        except Exception:
            continue
        for _, out in (h.get(pid, {}).get("outputs") or {}).items():
            for f in out.get("images", []):
                rel = ("%s/%s" % (f.get("subfolder", ""), f["filename"])).lstrip("/")
                if ensure_local(rel, p, required=False):
                    print("  %s" % os.path.basename(p))
                break

def stage_ideal():
    """The winning recipe applied to the sculpt-ready A-pose, because that is the render
    the 3D route actually needs. Qwen edit keeps the input's pose and framing, so an A-pose
    in gives an A-pose out - which is the property no text-to-image route has. Rendered at
    the ideal's own 1152x2048; FluxKontextImageScale snaps it to a grid the model likes."""
    os.makedirs(ALT, exist_ok=True)
    src = os.path.join(STANDIN, "ideal", "IDEAL_apose_1152x2048.png")
    if not os.path.exists(src):
        print("no ideal A-pose on disk at %s" % src)
        return
    name = "p2a_ideal_apose.png"
    shutil.copy(src, os.path.join(COMFY_IN, name))
    pr = dict(QWEN_PROMPTS)["hard"] + (" She is standing in an A-pose with her arms held "
                                       "clear of her body and her hands closed. Keep that "
                                       "pose, her whole body and the framing exactly as "
                                       "they are.")
    pids = {}
    wf = load_wf(WF_QWEN)
    set_path(wf, "7.inputs.image", name)
    set_path(wf, "10.inputs.prompt", pr)
    set_path(wf, "15.inputs.seed", SEED)
    set_path(wf, "17.inputs.filename_prefix", "claude-generated/p2a/qwen_ideal_apose")
    p = os.path.join(ALT, "qwen_ideal_apose.png")
    if os.path.exists(p):
        os.remove(p)
    pids[submit(wf)] = p
    wait_all(list(pids), "ideal")
    for pid, dst in pids.items():
        h = json.load(urllib.request.urlopen(
            "http://%s/history/%s" % (HOST, pid), timeout=60))
        for _, out in (h.get(pid, {}).get("outputs") or {}).items():
            for f in out.get("images", []):
                rel = ("%s/%s" % (f.get("subfolder", ""), f["filename"])).lstrip("/")
                ensure_local(rel, dst, required=False)
                print("  %s" % dst)
                break


# ---------------------------------------------------------------- sheets

def sheet(paths, labels, dst, cols, cw=440, ch=566):
    """Contact sheet with the cell count ASSERTED from the output pixels.

    Two traps, both already paid for in standin_person.py and repeated here rather than
    imported, because importing that module runs nothing but drags in its whole config.
    tile= is a SINGLE-STREAM filter - hand it six -i files and it tiles the frames of the
    first one and emits five black cells. And it silently DROPS cells of differing size.
    So every cell is scaled and padded to exactly cw x ch, written as a numbered sequence,
    read back through the image2 demuxer, and the finished sheet is measured against the
    grid arithmetic.
    """
    if not paths:
        return None
    tmp = os.path.join(WORK, "_sheet")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    n = 0
    for p, lab in zip(paths, labels):
        c = os.path.join(tmp, "cell_%03d.png" % n)
        r = sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
               "scale=%d:%d:force_original_aspect_ratio=decrease,"
               "pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=0x101010,"
               "drawtext=text='%s':fontcolor=yellow:fontsize=19:x=8:y=8:"
               "box=1:boxcolor=black@0.85:boxborderw=5"
               % (cw, ch, cw, ch, lab.replace(":", "\\:").replace("'", "")), c)
        if os.path.exists(c):
            n += 1
        else:
            print("  cell failed for %s: %s" % (p, r.stderr[-160:]))
    real = n
    rows = (n + cols - 1) // cols
    while n < rows * cols:
        sh("ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
           "color=c=0x101010:s=%dx%d" % (cw, ch), "-frames:v", "1",
           os.path.join(tmp, "cell_%03d.png" % n))
        n += 1
    m, pad = 8, 8
    r = sh("ffmpeg", "-y", "-v", "error", "-framerate", "1", "-start_number", "0",
           "-i", os.path.join(tmp, "cell_%03d.png"),
           "-vf", "tile=%dx%d:margin=%d:padding=%d:color=0x101010" % (cols, rows, m, pad),
           "-frames:v", "1", "-q:v", "3", dst)
    if not os.path.exists(dst):
        raise SystemExit("contact sheet failed: %s" % r.stderr[-400:])
    want = "%d,%d" % (cols * cw + (cols - 1) * pad + 2 * m,
                      rows * ch + (rows - 1) * pad + 2 * m)
    got = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height", "-of", "csv=p=0", dst).stdout.strip()
    if got != want:
        raise SystemExit("sheet %s is %s not %s - cells were dropped" % (dst, got, want))
    print("  %s  (%d cells, %dx%d grid, %s px - verified)" % (dst, real, cols, rows, got))
    return dst


def stage_sheets():
    os.makedirs(SHEETS, exist_ok=True)
    mp = os.path.join(OUT, "METRICS.json")
    M = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}

    def lab(style, mode, key, head):
        m = M.get("%s|%s|%s" % (style, mode, key)) or {}
        s = "" if m.get("sat") is None else "  sat %.0f" % m["sat"]
        f = "" if m.get("flat") is None else "  flat %.0fK" % m["flat"]
        return head + s + f

    for style, kind in STYLES:
        d = os.path.join(REN, style)
        if not os.path.isdir(d):
            continue
        for mode in ("tagged", "neutral"):
            paths, labels = [], []
            p0 = os.path.join(d, "%s_NOREF.png" % mode)
            if os.path.exists(p0):
                paths.append(p0)
                labels.append(lab(style, mode, "NOREF", "NO REFERENCE (full style)"))
            for w in WEIGHTS:
                p = os.path.join(d, "%s_w%03d.png" % (mode, int(round(w * 100))))
                if os.path.exists(p):
                    paths.append(p)
                    labels.append(lab(style, mode, "%.2f" % w, "IPAdapter %.2f" % w))
            if paths:
                sheet(paths, labels,
                      os.path.join(SHEETS, "%s_%s.jpg" % (style, mode)), 3)

    # the reference, next to the two extremes of every style, on one page
    paths, labels = [REF_SRC], ["THE REFERENCE (photo)"]
    for style, kind in STYLES:
        for mode in ("tagged",):
            for key, head in (("NOREF", "NOREF"), ("w040", "w0.40"), ("w100", "w1.00")):
                p = os.path.join(REN, style, "%s_%s.png" % (mode, key))
                if os.path.exists(p):
                    paths.append(p)
                    labels.append("%s  %s" % (style, head))
    if len(paths) > 1:
        sheet(paths, labels, os.path.join(SHEETS, "OVERVIEW_tagged.jpg"), 5, 400, 515)

    if os.path.isdir(ALT):
        ps = sorted(os.path.join(ALT, f) for f in os.listdir(ALT) if f.endswith(".png"))
        if ps:
            sheet([REF_SRC] + ps, ["THE REFERENCE (photo)"] +
                  [os.path.splitext(os.path.basename(p))[0] for p in ps],
                  os.path.join(SHEETS, "ALTERNATIVES.jpg"), 4, 440, 566)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all",
                    choices=["all", "sweep", "alt", "ideal", "sheets"])
    a = ap.parse_args()
    for d in (OUT, REN, ALT, SHEETS, WORK):
        os.makedirs(d, exist_ok=True)
    if a.stage in ("all", "sweep"):
        stage_sweep()
    if a.stage in ("all", "alt"):
        stage_alt()
    if a.stage in ("all", "ideal"):
        stage_ideal()
    if a.stage in ("all", "sheets"):
        stage_sheets()
    print("\nLOOK AT sheets/. Numbers narrow the search; they do not settle it.")


if __name__ == "__main__":
    main()
