#!/usr/bin/env python3
"""terra_wardrobe.py - THE REST OF "ALL VERSIONS OF HER".

    ~/ComfyUI/venv/bin/python3 studio/_tools/terra_wardrobe.py costumes
    ~/ComfyUI/venv/bin/python3 studio/_tools/terra_wardrobe.py places
    ~/ComfyUI/venv/bin/python3 studio/_tools/terra_wardrobe.py keyframes clips
    ~/ComfyUI/venv/bin/python3 studio/_tools/terra_wardrobe.py measure strips faces
    ~/ComfyUI/venv/bin/python3 studio/_tools/terra_wardrobe.py all

Run under the ComfyUI venv - the measure stage needs numpy and PIL and system python3
on this box has neither.

WHAT IS HERE AND WHY IT IS ONE TOOL

Three questions that look unrelated and are the same question - "is she still her when
something changes":

  costumes   4 costumes x 5 damage levels. The matrix the costumes map was BUILT for and
             which nobody has ever seen whole. Prior work rendered wear level 0 only, so
             the damage ladder - the other axis - is entirely unmeasured.
  places     18 places, 3 from each of the 6 families in studio/places/, at a fixed
             costume and a fixed style. The only thing varying is the world.
  clips      6 motion cards, all family `subject`, because a motion that moves the WORLD
             cannot break a face and a motion that moves the PERSON can.

THE COSTUME GRID IS A CONTROLLED A/B, NOT A GALLERY.

The Foundation phase retrained her LoRA to make wardrobe separable from identity and
reported v1 < v2 < v3. That claim was measured at wear level 0 only. This renders the
SAME grid four times:

    v3 LoRA, danbooru name STRIPPED   the recommended config for costume shots
    v3 LoRA, danbooru name KEPT       what the app actually composes today
    v1 LoRA, danbooru name STRIPPED   the pre-retrain control, same config
    v1 LoRA, danbooru name KEPT       the pre-retrain control, real usage

v1 is character_terra_00001_.safetensors, verified byte-identical to the .keep copy the
Foundation agent left behind (md5 865b3c74...). So "the retrain fixed it" stops being a
memory and becomes two pictures side by side, across the damage axis nobody tested.

WHY THE NAME AXIS IS IN THE GRID AT ALL. Foundation measured that the danbooru tag
"terra branford (final fantasy vi)" carries her canonical gold dress in the BASE
checkpoint, independently of any LoRA, and that the tag and the LoRA only saturate
together. A costume grid rendered in one name configuration cannot tell a weights problem
from a prompt problem - which is the exact mistake the first costume pass made.

IPADAPTER IS 0.0 ON BOTH STILL STAGES. Her style_verdict measured that a reference sheet
suppresses the style layer, and both these stages want a layer to be visible - the costume
in one, the place in the other. The LoRA carries identity alone. The MOTION keyframes are
different: they use IP 0.6 because that is what scripts/short.py:358 ships, and a clip
should be measured as a user would get it, not as this tool would prefer it.

SCRATCH DIRECTORIES AND THE TRAP THEY AVOID. Nothing here calls epic.ensure_local. Every
render is read straight off ComfyUI's own output directory, which is on this same box, so
the documented ensure_local cache - "if os.path.exists(dest): return dest" - has no way to
hand this tool a previous run's picture and make a real change look like no change. Output
files are found by GLOB rather than by assuming _00001_, because SaveImage and SaveVideo
share a per-prefix counter and a second run of the same tag lands on _00002_.
"""
import argparse, glob, json, os, shutil, subprocess, sys, uuid
from pathlib import Path

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

# THIS LINE MUST COME BEFORE THE IMPORTS BELOW AND IT IS NOT COSMETIC.
# scripts/analyze_shots.py:40 runs `os.environ.setdefault("COMFY_ROOT", "Z:/ComfyUI")` at
# import time - a WINDOWS drive path, left over from driving this box from the Windows
# client. epic.py:50 then reads COMFY_ROOT, so importing analyze_shots BEFORE epic silently
# makes COMFY = "Z:/ComfyUI", which on Linux is a relative path that exists nowhere.
# Nothing raises. Every os.path.exists() and glob() against it just returns empty, so the
# renders succeed and the tool reports that its own output is missing and the LoRA it just
# used is gone. That cost this tool one full 40-render pass.
# short.py:54 records the same default being removed from short.py for the same reason;
# analyze_shots.py was missed. Every other tool that imports it - motion_probe,
# motion_staging, cast_motion, motion_examples - carries its own copy of this line, which
# is how a landmine looks when it has been stepped on repeatedly and never defused.
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from analyze_shots import motion as ydif_motion, frozen_seconds   # noqa: E402
from comfy import api, set_path                                   # noqa: E402
from epic import load_wf, COMFY, HOST                             # noqa: E402
from PIL import Image                                             # noqa: E402

# Belt and braces for the trap above: if COMFY does not point at a real ComfyUI, stop
# NOW and say so, rather than rendering for ten minutes and reporting an empty result.
if not os.path.isdir(f"{COMFY}/models/loras"):
    raise SystemExit(
        "COMFY=%r has no models/loras. Something set COMFY_ROOT to a non-local path "
        "(see the note above about analyze_shots.py and Z:/ComfyUI). Refusing to run: "
        "every existence check would silently return False and the results would be "
        "wrong rather than absent." % COMFY)

CHAR = "TERRA"
REL_W = "claude-generated/terra-wardrobe"
REL_M = "claude-generated/terra-motion"
LAB_W = f"{COMFY}/output/{REL_W}"
LAB_M = f"{COMFY}/output/{REL_M}"
OUT_W = f"{STUDIO}/samples/cast/terra_wardrobe"
OUT_M = f"{STUDIO}/samples/cast/terra_motion"
CAST = f"{STUDIO}/characters"
PLACEDIR = f"{STUDIO}/places"
MOTIONDIR = f"{STUDIO}/motions"
STYLEDIR = f"{STUDIO}/styles"

_FONTS = ["/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf",
          "/usr/share/fonts/liberation-fonts/LiberationSans-Regular.ttf",
          "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf"]
FONT = next((f for f in _FONTS if os.path.exists(f)), _FONTS[0])

WF_ANIME = "22_anime_kf_ipadapter.json"
WF_LTX = "12_ltx23_i2v_audio.json"

Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG = ("1boy, male focus, masculine, beard, multiple girls, lowres, worst quality, "
       "bad anatomy, bad hands, watermark, text, multiple views")

# ── stills ────────────────────────────────────────────────────────────────────
# SEED 4242 is the Foundation costume probe's seed, deliberately reused: the wear-0 column
# of this grid should reproduce costume_ab.jpg cell for cell, which makes the new damage
# columns trustworthy by association. If that column does NOT reproduce, something moved
# underneath this measurement and the whole grid is suspect.
SEED_COSTUME = 4242
SEED_PLACE = 8310
CW, CH = 832, 1216          # portrait - a full body has to be legible for a costume call
PW, PH = 1216, 832          # landscape - a PLACE has to have room to be a place
IP_STILL = 0.0
IP_MOTION = 0.6

# The Foundation probe's place, kept for comparability. It argues for no costume: a throne
# room would argue for the court gown and a battlefield for the plate, and then the grid
# would be measuring the place.
PLACE_COSTUME = "a plain stone courtyard, overcast daylight, flat grey wall behind"
FRAME_COSTUME = "standing, full body visible head to feet, facing the camera"
FRAME_PLACE = "standing, full body, three quarter view"

COSTUME_ORDER = ["default", "armour", "court", "field"]
WEAR_LABEL = ["0 pristine", "1 worn", "2 damaged", "3 badly damaged", "4 ruined"]

# 3 places from each of the 6 families, chosen to span the `scale` field as well as the
# family - intimate rooms through vast exteriors - because scale is what decides how much
# of her is left in the frame, and a character sweep that is all mid-shots proves less.
PLACES = [
    ("nature", "snowfield"), ("nature", "pine_forest"), ("nature", "meadow_in_summer"),
    ("urban", "neon_backstreet"), ("urban", "rooftop_night"), ("urban", "market_street"),
    ("interior", "attic_bedroom"), ("interior", "library_reading_room"),
    ("interior", "cathedral_nave"),
    ("historical", "castle_great_hall"), ("historical", "ruined_temple"),
    ("historical", "viking_longhouse"),
    ("fantastical", "crystal_cavern"), ("fantastical", "floating_islands"),
    ("fantastical", "wizard_tower_interior"),
    ("industrial", "factory_floor"), ("industrial", "mecha_hangar"),
    ("industrial", "harbour_docks"),
]
PLACE_STYLE = "cel_anime_90s"     # measured to land on her, studio/characters/TERRA.json
PLACE_COSTUME_ID = "default"
PLACE_WEAR = 0

# compose.py:209 strips these from a place tag string when a character is in the shot.
PLACE_EMPTY_NOUNS = ("scenery", "no humans")

# ── motion ────────────────────────────────────────────────────────────────────
KFW, KFH = 1344, 768
VW, VH = 1280, 704
FPS = 24
SHORT_FRAMES = 97       # 4.04s - the length the whole motion library was measured at
LONG_FRAMES = 193       # 8.04s - the length her card claims identity survives
KF_SEED0 = 4400
VID_SEED = 7701         # a seed the motion library itself used
FRAME_MOTION = "cowboy shot, looking at the viewer, centered"

# Six motion cards, every one family `subject`. The world-movers (snow, rain, leaves,
# curtain) are excluded on purpose: they cannot break a face, so they cannot answer the
# question. Each place is chosen to MOTIVATE its motion - wind on a sea cliff, depth in a
# market street - because an unmotivated action is a second variable.
#   (cell, place, motion, extra keyframe tags, render a long version too)
CELLS = [
    ("c1_head_turn",   "snowfield",            "head_turn",   "", True),
    ("c2_hand_to_face", "library_reading_room", "hand_to_face", "", False),
    ("c3_turn_away",   "castle_great_hall",    "turn_away",   "", True),
    ("c4_hair_lifts",  "sea_cliff",            "hair_lifts",  "", False),
    ("c5_walk_in",     "market_street",        "walk_in",     "", True),
    ("c6_step_back",   "crystal_cavern",       "step_back",   "", False),
]
# hair_lifts is in the set for a reason specific to THIS character. Her identity
# vocabulary leads with "long wavy green hair" - it is the single most load-bearing noun
# on her card. A motion whose entire content is that hair moving is the most direct
# available test of whether the thing that makes her recognisable survives being animated.

# Head crop windows, (centre x, centre y, side) as fractions of W / H / HEIGHT. These are
# SET BY LOOKING at the rendered keyframes and then re-checked against faces/*.png. A cell
# whose head leaves its window goes in EXCLUDE_FACE and loses its drift numbers, because a
# number computed off an ear and a wall is worse than no number at all.
HEAD_DEFAULT = (0.50, 0.30, 0.46)
HEAD_OVERRIDE = {}
# NO FIXED WINDOW CAN MEASURE THESE TWO, and a number measuring the wrong thing is worse
# than no number. SET BY READING THE STRIPS, not by reading the numbers:
#   c4_hair_lifts  she never leaves the picture, but LTX re-frames her downward from f0 and
#                  creeps in 12.5%, so the keyframe-derived window slides off her head. Its
#                  first numbers read "green 40 -> 5", which says her hair left the shot.
#                  The strip shows her standing in frame with her hair moving, exactly as
#                  the motion card promises. The metric was wrong, the clip was fine.
#   c6_step_back   she turns and recedes to roughly a quarter of her starting height by
#                  f96, so any fixed window measures SCALE, not identity.
# Both are judged from strips/, which is what the strips are for.
EXCLUDE_FACE = {"c4_hair_lifts", "c6_step_back"}

# HER HAIR, IN NUMBERS, MEASURED OFF A RENDER RATHER THAN ASSUMED FROM THE WORD "GREEN".
# The first version of this file guessed hue 55-115, saturation > 60 - the obvious reading
# of "long wavy green hair". Measured on c1_head_turn's keyframe, her hair is actually
# median hue 110, median SATURATION 46, median value 214: a pale mint that is nearly at
# the teal edge of the hue window and less than half as saturated as the guess required.
# At s > 60 the mask kept 0.25% of the frame; at s > 25 it keeps 7.8%.
# So the first measure pass reported "green 1.3 -> 0.0" for a woman whose hair fills a
# quarter of the shot, and that would have been written down as her hair leaving frame.
# The lesson is the project's own, pointed at a metric instead of a prompt: a threshold
# named after a colour word is an ADJECTIVE, and it has to be measured before it means
# anything.
HAIR_H = (50, 130)
HAIR_S = 25
HAIR_V = 60


# ═══════════════════════════════════════════════════════════════════ helpers
def sh(*a):
    r = subprocess.run([str(x) for x in a], capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write("FAIL %s\n%s\n" % (" ".join(str(x) for x in a)[:300],
                                            (r.stderr or "")[-1000:]))
    return r


def need(*dirs):
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _esc(s):
    """drawtext escaping. The apostrophe is the hazard - a label sits inside a
    single-quoted filtergraph token and a literal ' truncates it."""
    for a, b in (("\\", "\\\\"), (":", "\\:"), ("'", "’"), ("%", "\\%"),
                 ("[", "\\["), ("]", "\\]")):
        s = s.replace(a, b)
    return s


def card():
    return jload(f"{CAST}/{CHAR}.json")


def submit(wf):
    r = api(HOST, "/prompt", {"prompt": wf, "client_id": str(uuid.uuid4())})
    if "error" in r:
        raise RuntimeError(json.dumps(r)[:400])
    return r["prompt_id"]


def wait_all(pids, label="jobs", timeout=10800):
    """Submit the whole group, then poll. Keeps a checkpoint group adjacent in the queue
    so the 7 GB model is loaded once for all of it rather than once per cell."""
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


def job_error(rec):
    st = (rec.get("status") or {})
    if st.get("status_str") == "error":
        for m in st.get("messages") or []:
            if m[0] == "execution_error":
                return str(m[1].get("exception_message"))[:200]
        return "error"
    return None


def job_file(rec):
    for _, o in (rec.get("outputs") or {}).items():
        for k in ("images", "videos", "gifs"):
            for it in (o.get(k) or []):
                return os.path.join(COMFY, "output", it.get("subfolder") or "",
                                    it["filename"])
    return None


def latest(lab, tag, ext):
    """GLOB, never {tag}_00001_. SaveImage/SaveVideo keep one counter per prefix per
    directory, so re-running a tag writes _00002_ and an assumed _00001_ silently reads
    the PREVIOUS run - which reads as "the change did nothing"."""
    hits = sorted(glob.glob(f"{lab}/{tag}_[0-9]*_.{ext}"))
    return hits[-1] if hits else None


def place_tags(pid):
    t = jload(f"{PLACEDIR}/{pid}.json").get("tags", "")
    return ", ".join(p.strip() for p in t.split(",")
                     if p.strip().lower() not in PLACE_EMPTY_NOUNS)


def motion_card(mid):
    return jload(f"{MOTIONDIR}/{mid}.json")


def motion_text(c, mid):
    """Built the way scripts/short.py builds it. compose._motion_regender is IMPORTED
    rather than reimplemented so this tool cannot drift away from what the app sends."""
    m = motion_card(mid)
    txt = m.get("text") or m.get("prompt") or ""
    try:
        sys.path.insert(0, STUDIO)
        import compose
        return compose._motion_regender(txt, compose._pronouns(c))
    except Exception as e:
        print("  !! compose pronoun rewrite unavailable (%s) - card text verbatim"
              % str(e)[:80])
        return txt


def strength():
    c = card()
    v = c.get("lora_strength_measured")
    if v is None:
        print("  !! no lora_strength_measured on the card - falling back to 0.5")
        return 0.5
    return float(v)


def nameless(tags):
    """Drop the danbooru name and the series, keep the generic identity scaffolding."""
    return ", ".join(x for x in tags.split(", ")
                     if "terra branford" not in x and "final fantasy" not in x)


# ═══════════════════════════════════════════════════════════════════ workflows
def wf_still(prompt, lora, lora_w, seed, tag, rel, w, h, sheet=None, ip=IP_STILL,
             neg=NEG):
    wf = load_wf(WF_ANIME)
    set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
    if sheet:
        set_path(wf, "2.inputs.image", sheet)
    set_path(wf, "4.inputs.weight", float(ip))
    set_path(wf, "5.inputs.text", prompt)
    set_path(wf, "6.inputs.text", neg)
    set_path(wf, "8.inputs.seed", int(seed))
    for n in ("7", "10"):
        set_path(wf, f"{n}.inputs.width", w)
        set_path(wf, f"{n}.inputs.height", h)
    # Node 90 is spliced in for EVERY arm, at 0.0 for a control. LoraLoaderModelOnly is a
    # documented no-op at strength 0, so a control submits a structurally identical graph
    # and the only difference between it and its cell is one float.
    if lora:
        wf["90"] = {"class_type": "LoraLoaderModelOnly",
                    "inputs": {"model": ["1", 0], "lora_name": lora,
                               "strength_model": float(lora_w)}}
        for nid, node in list(wf.items()):
            if nid in ("1", "90") or not isinstance(node, dict):
                continue
            for k, v in (node.get("inputs") or {}).items():
                if isinstance(v, list) and len(v) == 2 and v[0] == "1" and v[1] == 0:
                    node["inputs"][k] = ["90", 0]
    set_path(wf, "11.inputs.filename_prefix", f"{rel}/{tag}")
    return wf


def wf_clip(staged, text, frames, seed, tag):
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
    set_path(wf, "43.inputs.filename_prefix", f"{REL_M}/{tag}")
    return wf


# ═══════════════════════════════════════════════════════════════════ pictures
def _cell(src, dst, w, h, label, labsize=19):
    sh("ffmpeg", "-y", "-hide_banner", "-v", "error", "-i", src, "-vf",
       "scale=%d:%d,setsar=1,drawtext=fontfile=%s:text='%s':x=8:y=8:fontsize=%d:"
       "fontcolor=white:box=1:boxcolor=black@0.82:boxborderw=6"
       % (w, h, FONT, _esc(label), labsize), "-frames:v", "1", dst)


def _tile(files, dst, cols, header, sub=""):
    """Tile with a title bar. Inputs must already be identical size - ffmpeg's tile filter
    is not forgiving about that, and neither is hstack."""
    tmp = "/tmp/_tw_tile_%d" % os.getpid()
    sh("rm", "-rf", tmp)
    need(tmp)
    for i, f in enumerate(files):
        shutil.copy(f, "%s/%03d.png" % (tmp, i))
    rows = (len(files) + cols - 1) // cols
    body = "%s/_body.png" % tmp
    sh("ffmpeg", "-y", "-hide_banner", "-v", "error", "-pattern_type", "glob",
       "-i", "%s/[0-9]*.png" % tmp, "-filter_complex",
       "tile=%dx%d:margin=8:padding=8:color=0x111111" % (cols, rows),
       "-frames:v", "1", body)
    pad = 54 + (34 if sub else 0)
    draw = ("drawtext=fontfile=%s:text='%s':x=16:y=12:fontsize=34:fontcolor=white"
            % (FONT, _esc(header)))
    if sub:
        draw += (",drawtext=fontfile=%s:text='%s':x=16:y=56:fontsize=23:fontcolor=0x7FD4FF"
                 % (FONT, _esc(sub)))
    sh("ffmpeg", "-y", "-hide_banner", "-v", "error", "-i", body, "-vf",
       "pad=iw:ih+%d:0:%d:0x000000,%s" % (pad, pad, draw), "-frames:v", "1",
       "-q:v", "3", dst)
    sh("rm", "-rf", tmp)
    print("wrote %s" % dst)


# ═══════════════════════════════════════════════════════════════════ costumes
def costume_prompt(c, cid, level, keep_name):
    tags = c["tags"] if keep_name else nameless(c["tags"])
    wear = c["costumes"][cid]["wear_tags"][level]
    return ", ".join(x for x in [tags, c.get("base_tags", ""), wear,
                                 FRAME_COSTUME, PLACE_COSTUME, Q] if x)


def stage_costumes(force=False, seed=SEED_COSTUME):
    """4 costumes x 5 damage levels, rendered four times: {v3, v1} x {name, no name}.

    A CONCLUSION THAT ONLY HOLDS AT ONE SEED IS NOT A CONCLUSION. The default 4242 is the
    Foundation probe's seed so the wear-0 column stays comparable to its evidence; --seed
    re-runs the whole 4x20 at a second one, and the seed is in every filename so the two
    runs cannot overwrite each other or be confused for one another."""
    c = card()
    sfx = "" if seed == SEED_COSTUME else "_s%d" % seed
    v3 = c["lora"]
    v1 = "character_terra_00001_.safetensors"
    w = strength()
    need(LAB_W, OUT_W)
    arms = [("v3_noname", v3, False), ("v3_name", v3, True),
            ("v1_noname", v1, False), ("v1_name", v1, True)]
    # The A/B against the pre-retrain weights is the POINT of this stage, so a missing v1
    # is a hard stop, not a quiet drop to two arms. Dropping it silently is how "the
    # retrain fixed it" stays a memory instead of becoming a measurement.
    if not os.path.exists(f"{COMFY}/models/loras/{v1}"):
        raise SystemExit(
            "%s/models/loras/%s not found. It is the ORIGINAL uncaptioned LoRA and the "
            "whole comparison rests on it; the card says a byte copy is kept alongside as "
            "'.keep'. Restore it before running this stage." % (COMFY, v1))

    jobs, meta = [], {}
    for arm, lora, keep in arms:
        for cid in COSTUME_ORDER:
            for lv in range(5):
                tag = "cost_%s_%s_%d%s" % (arm, cid, lv, sfx)
                if latest(LAB_W, tag, "png") and not force:
                    continue
                p = costume_prompt(c, cid, lv, keep)
                j = submit(wf_still(p, lora, w, seed, tag, REL_W, CW, CH))
                jobs.append(j)
                meta[j] = tag
                print("  > %s" % tag, flush=True)
    if jobs:
        recs = wait_all(jobs, "costumes")
        for j in jobs:
            e = job_error(recs.get(j, {}))
            if e:
                print("  !! %s FAILED %s" % (meta[j], e))

    for arm, lora, keep in arms:
        files, tmp = [], "/tmp/_tw_c_%d_%s" % (os.getpid(), arm)
        sh("rm", "-rf", tmp)
        need(tmp)
        ok = True
        for cid in COSTUME_ORDER:
            for lv in range(5):
                src = latest(LAB_W, "cost_%s_%s_%d%s" % (arm, cid, lv, sfx), "png")
                if not src:
                    print("  !! missing cell %s %s %d" % (arm, cid, lv))
                    ok = False
                    continue
                d = "%s/%s_%d.png" % (tmp, cid, lv)
                _cell(src, d, 420, 614,
                      "%s  |  wear %s" % (c["costumes"][cid]["name"], WEAR_LABEL[lv]))
                files.append(d)
        if not ok:
            continue
        lname = "v3 (retrained, captioned, 2 costumes)" if lora == v3 \
            else "v1 (ORIGINAL, uncaptioned, 1 costume)"
        _tile(files, f"{OUT_W}/costume_damage_{arm}{sfx}.jpg", 5,
              "TERRA  costumes x damage   LoRA %s @ %.2f   danbooru name %s"
              % (lname, w, "KEPT" if keep else "STRIPPED"),
              "seed %d, one place, full body. Rows: traveller / imperial plate / court "
              "dress / field coat. Columns: damage 0-4."
              % seed)
        sh("rm", "-rf", tmp)


# ═══════════════════════════════════════════════════════════════════ places
def stage_places(force=False):
    c = card()
    w = strength()
    st = jload(f"{STYLEDIR}/{PLACE_STYLE}.json")
    need(LAB_W, OUT_W)
    wear = c["costumes"][PLACE_COSTUME_ID]["wear_tags"][PLACE_WEAR]
    neg = NEG + (", " + st["negative_add"] if st.get("negative_add") else "")
    jobs, meta = [], {}
    for fam, pid in PLACES:
        tag = "pl_%s" % pid
        if latest(LAB_W, tag, "png") and not force:
            continue
        # Slot order is compose.py's: identity, base, garment, style, shot, place, quality.
        # Earlier and more specific wins on this engine, so the style sits ahead of the
        # place and behind the character.
        p = ", ".join(x for x in [c["tags"], c.get("base_tags", ""), wear,
                                  st["tags"], FRAME_PLACE, place_tags(pid), Q] if x)
        j = submit(wf_still(p, c["lora"], w, SEED_PLACE, tag, REL_W, PW, PH, neg=neg))
        jobs.append(j)
        meta[j] = tag
        print("  > %-28s %s" % (pid, fam), flush=True)
    if jobs:
        recs = wait_all(jobs, "places")
        for j in jobs:
            e = job_error(recs.get(j, {}))
            if e:
                print("  !! %s FAILED %s" % (meta[j], e))

    files, tmp = [], "/tmp/_tw_p_%d" % os.getpid()
    sh("rm", "-rf", tmp)
    need(tmp)
    for i, (fam, pid) in enumerate(PLACES):
        src = latest(LAB_W, "pl_%s" % pid, "png")
        if not src:
            print("  !! missing %s" % pid)
            continue
        pc = jload(f"{PLACEDIR}/{pid}.json")
        d = "%s/%02d.png" % (tmp, i)
        _cell(src, d, 620, 424, "%s  |  %s  |  %s" % (fam, pc["name"], pc.get("scale", "")))
        files.append(d)
    _tile(files, f"{OUT_W}/places_grid.jpg", 3,
          "TERRA across 18 places   traveller wear 0   style %s   LoRA %.2f"
          % (PLACE_STYLE, w),
          "seed %d held. One row per family: nature / urban / interior / historical / "
          "fantastical / industrial." % SEED_PLACE)
    sh("rm", "-rf", tmp)


RECHECK_SEEDS = [8310, 4242, 1337, 9090, 5150, 7411]


def stage_recheck(pid=None):
    """IS IT THE PLACE, OR WAS IT THE SEED? The places sweep holds one seed so the place is
    the only variable, which is what makes it a sweep - and it also means a single odd cell
    could be that seed misbehaving rather than that place doing anything.

    floating_islands came back with CORAL hair on a character whose defining noun is green
    hair. That is either a property of the place, which a director needs on the card, or
    one unlucky draw, which nobody should write down at all. The two are told apart by
    re-rendering the same place at six seeds and counting."""
    c = card()
    w = strength()
    pid = pid or "floating_islands"
    st = jload(f"{STYLEDIR}/{PLACE_STYLE}.json")
    wear = c["costumes"][PLACE_COSTUME_ID]["wear_tags"][PLACE_WEAR]
    neg = NEG + (", " + st["negative_add"] if st.get("negative_add") else "")
    need(LAB_W, OUT_W)
    jobs, meta = [], {}
    for s in RECHECK_SEEDS:
        tag = "rc_%s_%d" % (pid, s)
        if latest(LAB_W, tag, "png"):
            continue
        p = ", ".join(x for x in [c["tags"], c.get("base_tags", ""), wear,
                                  st["tags"], FRAME_PLACE, place_tags(pid), Q] if x)
        j = submit(wf_still(p, c["lora"], w, s, tag, REL_W, PW, PH, neg=neg))
        jobs.append(j)
        meta[j] = tag
        print("  > %s" % tag, flush=True)
    if jobs:
        wait_all(jobs, "recheck")
    files, tmp = [], "/tmp/_tw_rc_%d" % os.getpid()
    sh("rm", "-rf", tmp)
    need(tmp)
    import numpy as np
    for s in RECHECK_SEEDS:
        src = latest(LAB_W, "rc_%s_%d" % (pid, s), "png")
        if not src:
            continue
        box = find_head(src, PW, PH)
        g = green_frac(src, box) if box else -1.0
        d = "%s/%d.png" % (tmp, s)
        _cell(src, d, 620, 424, "seed %d   green in head crop %.1f%%" % (s, g))
        files.append(d)
        print("  seed %-6d green in head crop %.1f%%" % (s, g))
    if files:
        _tile(files, f"{OUT_W}/recheck_{pid}.jpg", 3,
              "TERRA at %s - same prompt, six seeds" % pid,
              "Green fraction inside the located head crop. Her hair is the character; a "
              "low number here means this place took it away.")
    sh("rm", "-rf", tmp)


def find_head(path, W, H):
    """WHERE IS SHE IN THIS PICTURE? Returns a square crop box around the head.

    A places sweep spans `intimate` rooms and `vast` exteriors, so the subject is a
    half-length figure in one cell and 12% of the frame height in the next. A fixed crop
    window - which is what the motion half of this tool uses, because there the framing is
    held - would land on a face in some cells and on a wall in others, and a face grid
    that is half walls proves nothing about identity.

    So the subject is LOCATED, by the two things she reliably has and these backgrounds
    mostly do not: bare skin, and a large mass of saturated green hair directly above it.
    Skin alone finds market-stall timber and longhouse walls; requiring green above the
    skin rejects those. The topmost skin row inside the winning column band is the face.

    THIS IS A HEURISTIC AND IT IS CHECKED BY LOOKING - every crop is written into the
    contact sheet with its cell name, so a miss is visible rather than silent, and
    HEAD_FIX overrides any cell it gets wrong."""
    import numpy as np
    im = Image.open(path).convert("RGB")
    a = np.asarray(im, dtype=np.int16)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    hsv = np.asarray(im.convert("HSV"), dtype=np.int16)
    hh, ss, vv = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    skin = (r > 150) & (g > 110) & (b > 100) & (r > g + 12) & (g >= b - 10) & (ss < 110)
    hair = (hh > HAIR_H[0]) & (hh < HAIR_H[1]) & (ss > HAIR_S) & (vv > HAIR_V)
    # Column score: skin below, green above. A 1-D smooth then argmax over a band.
    cs = skin.sum(0).astype(np.float64)
    ch = hair.sum(0).astype(np.float64)
    k = max(9, W // 40)
    ker = np.ones(k) / k
    score = np.convolve(cs, ker, "same") * np.convolve(ch, ker, "same")
    if score.max() <= 0:
        return None
    cx = int(score.argmax())
    half = max(W // 12, 40)
    lo, hi = max(cx - half, 0), min(cx + half, W)
    # A single stray skin-coloured pixel must not define the face, so the topmost row is
    # taken at a threshold relative to the band's own maximum rather than at >0.
    prof = skin[:, lo:hi].sum(1)
    if prof.max() < 3:
        return None
    rows = np.where(prof >= max(3, prof.max() * 0.25))[0]
    if not len(rows):
        return None
    top = int(rows[0])
    # FIRST PASS OF THIS SHEET CROPPED A HEAD TOO HIGH and came back full of hair ribbon
    # and background. The topmost skin row is the forehead, not the middle of the face, and
    # the box was both centred on it and too small. The box is now centred well BELOW that
    # row and made deliberately generous - an over-large crop that certainly contains the
    # face is worth more than a tight one that sometimes contains a wall.
    side = int(max(H * 0.22, 90))
    cyy = top + side * 0.42
    x0 = int(min(max(cx - side / 2, 0), W - side))
    y0 = int(min(max(cyy - side / 2, 0), H - side))
    return (x0, y0, x0 + side, y0 + side)


# Cells find_head gets wrong, filled in AFTER looking at the first sheet. Same discipline
# as the motion head windows: a heuristic is allowed, an unchecked heuristic is not.
HEAD_FIX = {}


def stage_placefaces(size=300):
    """The places grid at 620px a cell cannot answer an identity question - at `vast`
    scale her whole head is about 12 pixels there. This crops each one and blows it up,
    which is where the places sweep is actually judged."""
    need(OUT_W)
    tmp = "/tmp/_tw_pf_%d" % os.getpid()
    need(tmp)
    parts, labels = [], []
    for fam, pid in PLACES:
        src = latest(LAB_W, "pl_%s" % pid, "png")
        if not src:
            continue
        box = HEAD_FIX.get(pid) or find_head(src, PW, PH)
        if not box:
            print("  !! could not locate subject in %s" % pid)
            continue
        d = "%s/%s.png" % (tmp, pid)
        Image.open(src).convert("RGB").crop(box).resize((size, size), Image.LANCZOS)\
             .save(d)
        parts.append(d)
        labels.append("%s  (%s)" % (pid, fam))
    if not parts:
        return
    files = []
    for p, lab in zip(parts, labels):
        d = p.replace(".png", "_l.png")
        _cell(p, d, size, size, lab, labsize=15)
        files.append(d)
    _tile(files, f"{OUT_W}/places_faces.jpg", 6,
          "TERRA  head crop from each of the 18 place renders",
          "Located per cell, not a fixed window - subject scale spans intimate to vast. "
          "Ask only: is this the same person, and is her hair still green.")
    sh("rm", "-rf", tmp)


# ═══════════════════════════════════════════════════════════════════ motion
def kf_prompt(c, pid, extra=""):
    """compose.py:1476-1502's slot order, kept exactly."""
    bits = [c["id"].lower(), c.get("tags", "").strip()]
    if c.get("base_tags"):
        bits.append(c["base_tags"].strip())
    bits.append(c["costumes"]["default"]["wear_tags"][0])
    bits.append(FRAME_MOTION)
    if extra:
        bits.append(extra)
    bits.append(place_tags(pid))
    bits.append(Q)
    return ", ".join(b for b in bits if b)


def stage_keyframes(force=False):
    c = card()
    w = strength()
    need(LAB_M, OUT_M, f"{OUT_M}/keyframes")
    jobs, meta = [], {}
    for i, (cid, pid, mid, extra, _l) in enumerate(CELLS):
        if latest(LAB_M, cid, "png") and not force:
            print("  = %s" % cid)
            continue
        wf = wf_still(kf_prompt(c, pid, extra), c["lora"], w, KF_SEED0 + i * 7, cid,
                      REL_M, KFW, KFH, sheet=c.get("sheet"), ip=IP_MOTION)
        j = submit(wf)
        jobs.append(j)
        meta[j] = cid
        print("  > %-18s %-22s seed %d" % (cid, pid, KF_SEED0 + i * 7), flush=True)
    if jobs:
        recs = wait_all(jobs, "keyframes")
        for j in jobs:
            e = job_error(recs.get(j, {}))
            if e:
                print("  !! %s FAILED %s" % (meta[j], e))
    for cid, _p, _m, _e, _l in CELLS:
        f = latest(LAB_M, cid, "png")
        if f:
            shutil.copy(f, f"{COMFY}/input/tw_{cid}.png")
            shutil.copy(f, f"{OUT_M}/keyframes/{cid}.png")
        else:
            print("  !! %s has no keyframe" % cid)


def stage_clips(force=False):
    c = card()
    need(LAB_M, OUT_M)
    plan = []
    for cid, pid, mid, _e, longable in CELLS:
        plan.append((cid, cid, mid, pid, SHORT_FRAMES))
        if longable:
            plan.append((cid + "_long", cid, mid, pid, LONG_FRAMES))
    man = f"{OUT_M}/manifest.json"
    done = {r["id"]: r.get("file") for r in (jload(man) if os.path.exists(man) else [])}
    jobs, meta = [], {}
    for tag, kf, mid, pid, frames in plan:
        if done.get(tag) and os.path.exists(done[tag] or "") and not force:
            print("  = %s" % tag)
            continue
        staged = f"tw_{kf}.png"
        if not os.path.exists(f"{COMFY}/input/{staged}"):
            print("  !! no staged keyframe for %s - run keyframes first" % tag)
            continue
        txt = motion_text(c, mid)
        j = submit(wf_clip(staged, txt, frames, VID_SEED, tag))
        jobs.append(j)
        meta[j] = dict(id=tag, kf=kf, motion_id=mid, place=pid, frames_asked=frames,
                       text=txt, lora=strength(),
                       want=motion_card(mid).get("desc", ""))
        print("  > %-22s %3df  %s" % (tag, frames, txt), flush=True)
    recs = wait_all(jobs, "clips") if jobs else {}
    prev = jload(man) if os.path.exists(man) else []
    for j in jobs:
        m = dict(meta[j])
        m["error"] = job_error(recs.get(j, {}))
        m["file"] = job_file(recs.get(j, {})) or latest(LAB_M, m["id"], "mp4")
        prev = [r for r in prev if r["id"] != m["id"]]
        prev.append(m)
        print("%-24s %s" % (m["id"], m["error"] or os.path.basename(m["file"] or "NONE")))
    for tag, kf, mid, pid, frames in plan:
        f = latest(LAB_M, tag, "mp4")
        if f and not any(r["id"] == tag for r in prev):
            prev.append(dict(id=tag, kf=kf, motion_id=mid, place=pid,
                             frames_asked=frames, text=motion_text(c, mid),
                             lora=strength(), want=motion_card(mid).get("desc", ""),
                             error=None, file=f))
    order = [p[0] for p in plan]
    prev.sort(key=lambda r: order.index(r["id"]) if r["id"] in order else 99)
    json.dump(prev, open(man, "w"), indent=1)
    print("wrote %s (%d rows)" % (man, len(prev)))


# ═══════════════════════════════════════════════════════════════════ measuring
def nframes(path):
    r = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
           "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", path)
    try:
        return int((r.stdout or "0").strip().split(",")[0])
    except ValueError:
        return 0


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
    wgt = (hsv[:, :, 1] / 255.0) * (hsv[:, :, 2] / 255.0)
    hist, _ = np.histogram(hsv[:, :, 0], bins=36, range=(0, 256), weights=wgt)
    return {"g": g, "h": hist / (hist.sum() + 1e-9)}


def d_struct(a, b):
    import numpy as np
    return float(np.abs(a["g"] - b["g"]).mean() * 100.0)


def d_hue(a, b):
    import numpy as np
    x, y = a["h"], b["h"]
    return float(0.5 * np.sum((x - y) ** 2 / (x + y + 1e-9)) * 100.0)


def green_frac(path, box):
    """THE CHARACTER-SPECIFIC MARKER, and the reason this tool measures anything the
    generic drift statistic does not. VIRO carried a numeral on a jersey - a countable
    thing a metric cannot fake. Terra's equivalent is her HAIR COLOUR: the single most
    load-bearing noun on her card is "long wavy green hair". So: the fraction of pixels in
    the head crop whose hue is green AND saturated enough to be paint rather than a grey
    wall. It is not a face test - it cannot tell whether the face is hers - but it is a
    hard, literal test of whether the thing that makes her recognisable at a glance is
    still on screen, and it survives compression and scale where a face crop does not."""
    import numpy as np
    im = Image.open(path).convert("RGB").crop(box).resize((96, 96), Image.LANCZOS)
    hsv = np.asarray(im.convert("HSV"), dtype=np.float64)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    # PIL packs hue into 0-255. The window is the MEASURED one - see HAIR_H/HAIR_S/HAIR_V.
    m = (h > HAIR_H[0]) & (h < HAIR_H[1]) & (s > HAIR_S) & (v > HAIR_V)
    return round(float(m.mean()) * 100.0, 2)


def creep_of(clip, tmp):
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
    man = jload(f"{OUT_M}/manifest.json")
    tmp = "/tmp/terra_motion_%d" % os.getpid()
    need(tmp, f"{OUT_M}/_frames")
    res = []
    for m in man:
        f = m.get("file")
        if not f or not os.path.exists(f):
            print("skip %s: no file" % m["id"])
            continue
        r = dict(m)
        mo, ch = ydif_motion(f)
        n = nframes(f)
        r.update(motion=round(mo, 4), churn=round(ch, 4),
                 frozen=round(frozen_seconds(f), 2), frames=n,
                 secs=round(n / float(FPS), 2))
        r.update(creep_of(f, tmp))
        idxs = sample_idx(n, cols)
        r["sample_idx"] = idxs
        pngs = [_frame(f, ix, "%s/_frames/%s_%02d.png" % (OUT_M, m["id"], i))
                for i, ix in enumerate(idxs)]
        # THE HEAD WINDOW IS MEASURED FROM THIS CLIP'S OWN KEYFRAME, not assumed.
        # The first pass used one hand-set fraction for every cell, the way cast_motion.py
        # does - which is defensible there because that tool holds ONE framing across its
        # whole matrix. Here the six keyframes put her in six different parts of the frame,
        # and the shared window landed beside her head on most cells: it returned crops of
        # hair and snow, and a "green in crop" figure of 0.2% for a woman whose hair is the
        # most saturated green object in the picture. A number that low is not a result,
        # it is a broken instrument, and it would have read as "her hair is gone".
        bf = HEAD_OVERRIDE.get(m["id"])
        if bf is None:
            kfp = f"{OUT_M}/keyframes/%s.png" % m["kf"]
            hb = find_head(kfp, KFW, KFH) if os.path.exists(kfp) else None
            if hb:
                # find_head returns pixels in KEYFRAME space (1344x768); the clip is
                # 1280x704. Convert to fractions so one window describes both.
                x0, y0, x1, y1 = hb
                bf = (((x0 + x1) / 2.0) / KFW, ((y0 + y1) / 2.0) / KFH,
                      (y1 - y0) / float(KFH))
                bf = (round(bf[0], 4), round(bf[1], 4), round(min(bf[2], 0.95), 4))
            else:
                print("  !! %s: could not locate a head in the keyframe, "
                      "falling back to the centred default" % m["id"])
                bf = HEAD_DEFAULT
        r["head_box"] = bf
        box = frac_box(bf, VW, VH)
        r["green_pct"] = [green_frac(p, box) for p in pngs]
        if m["id"] in EXCLUDE_FACE:
            r["drift_struct"] = r["drift_hue"] = None
            r["excluded"] = "head leaves the crop window - judge from faces/%s.png" % m["id"]
        else:
            fs = [feats(p, box) for p in pngs]
            r["drift_struct"] = [round(d_struct(fs[0], x), 2) for x in fs]
            r["drift_hue"] = [round(d_hue(fs[0], x), 2) for x in fs]
        res.append(r)
        d = r.get("drift_struct") or []
        print("%-22s motion %6.3f churn %5.2f creep %.3f frozen %4.1f  drift %s  "
              "green %.1f -> %.1f"
              % (r["id"], r["motion"], r["churn"], r.get("creep", 0), r["frozen"],
                 ("%.1f" % d[-1]) if d else "excl",
                 r["green_pct"][0], r["green_pct"][-1]), flush=True)
    json.dump(res, open(f"{OUT_M}/results.json", "w"), indent=1)
    sh("rm", "-rf", tmp)
    print("wrote %s/results.json (%d clips)" % (OUT_M, len(res)))


def _hstack(parts, labels, dst, cellw, header, sub=None, sub2=None, cellh=None):
    """hstack REFUSES inputs of unequal height, and a strip mixes a 1344x768 keyframe with
    1280x704 video frames, so the height is FORCED rather than derived."""
    fc = []
    for i, lab in enumerate(labels):
        fc.append("[%d]scale=%d:%d,setsar=1,pad=iw+4:ih+34:2:2:0x101010,"
                  "drawtext=fontfile=%s:text='%s':x=6:y=h-27:fontsize=19:"
                  "fontcolor=0xE0E0E0[v%d]" % (i, cellw, cellh or -1, FONT, _esc(lab), i))
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
    rows = jload(f"{OUT_M}/results.json")
    sd = f"{OUT_M}/strips"
    need(sd)
    for m in rows:
        kf = f"{OUT_M}/keyframes/%s.png" % m["kf"]
        parts = ([kf] if os.path.exists(kf) else [])
        labels = (["KEYFRAME"] if parts else [])
        for i, ix in enumerate(m["sample_idx"]):
            parts.append("%s/_frames/%s_%02d.png" % (OUT_M, m["id"], i))
            labels.append("f%d  %.2fs" % (ix, ix / float(FPS)))
        d = m.get("drift_struct")
        _hstack(parts, labels, "%s/%s.png" % (sd, m["id"]), 330,
                "%s   %s @ %s   lora %.2f   %.2fs"
                % (m["id"], m["motion_id"], m["place"], m["lora"], m["secs"]),
                "MOTION STRING: %s" % m["text"],
                "motion %.3f  churn %.2f  creep %.3f  |  head drift f0->last struct %s  "
                "|  green in head crop %.1f%% -> %.1f%%"
                % (m["motion"], m["churn"], m.get("creep", 0),
                   ("%.1f" % d[-1]) if d else "excluded",
                   m["green_pct"][0], m["green_pct"][-1]),
                cellh=int(round(330 * VH / float(VW))))
        print("strip %s" % m["id"])


def stage_faces(size=300):
    """The same frames as HEAD CROPS, upscaled. A head is ~150px in a 1280x704 frame and a
    strip cell is 330px wide; at that scale a face that has become a different face is not
    distinguishable from one that has not. IDENTITY IS JUDGED HERE, not in the strip."""
    rows = jload(f"{OUT_M}/results.json")
    sd = f"{OUT_M}/faces"
    tmp = "/tmp/terra_face_%d" % os.getpid()
    need(sd, tmp)
    for m in rows:
        box = frac_box(m["head_box"], VW, VH)
        parts, labels = [], []
        kf = f"{OUT_M}/keyframes/%s.png" % m["kf"]
        if os.path.exists(kf):
            k = "%s/%s_kf.png" % (tmp, m["id"])
            Image.open(kf).convert("RGB").resize((VW, VH), Image.LANCZOS).crop(box)\
                 .resize((size, size), Image.LANCZOS).save(k)
            parts.append(k)
            labels.append("KEYFRAME")
        for i, ix in enumerate(m["sample_idx"]):
            src = "%s/_frames/%s_%02d.png" % (OUT_M, m["id"], i)
            if not os.path.exists(src):
                continue
            cpath = "%s/%s_%02d.png" % (tmp, m["id"], i)
            Image.open(src).convert("RGB").crop(box)\
                 .resize((size, size), Image.LANCZOS).save(cpath)
            parts.append(cpath)
            d = m.get("drift_struct")
            labels.append("f%d %.2fs%s  green %.0f"
                          % (ix, ix / float(FPS), "  d%.0f" % d[i] if d else "",
                             m["green_pct"][i]))
        if not parts:
            continue
        _hstack(parts, labels, "%s/%s.png" % (sd, m["id"]), size,
                "FACES  %s   %s @ %s" % (m["id"], m["motion_id"], m["place"]),
                "d = structural drift from f0 in this crop. g = green pixels in the crop, "
                "i.e. is her hair still there.",
                None, cellh=size)
        print("faces %s" % m["id"])
    sh("rm", "-rf", tmp)


# ═══════════════════════════════════════════════════════════════════ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stages", nargs="*", default=["all"])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--seed", type=int, default=SEED_COSTUME,
                    help="costume stage only - re-run the whole 4x20 at a second seed")
    ap.add_argument("--place", default=None, help="recheck stage only - which place")
    a = ap.parse_args()
    st = a.stages or ["all"]
    if "all" in st:
        st = ["costumes", "places", "placefaces", "keyframes", "clips", "measure",
              "strips", "faces"]
    fns = {"costumes": lambda: stage_costumes(a.force, a.seed),
           "places": lambda: stage_places(a.force),
           "placefaces": stage_placefaces,
           "recheck": lambda: stage_recheck(a.place),
           "keyframes": lambda: stage_keyframes(a.force),
           "clips": lambda: stage_clips(a.force),
           "measure": stage_measure,
           "strips": stage_strips,
           "faces": stage_faces}
    for s in st:
        if s not in fns:
            raise SystemExit("unknown stage %r - one of %s" % (s, ", ".join(fns)))
        print("\n=== %s ===" % s, flush=True)
        fns[s]()


if __name__ == "__main__":
    main()
