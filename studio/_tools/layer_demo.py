#!/usr/bin/env python3
"""layer_demo.py - RENDER a layer stack, so that composition is a measurement.

    python3 studio/_tools/layer_demo.py --style watercolour --place cathedral_nave
    python3 studio/_tools/layer_demo.py --style film_35mm --character VIRO --wear 2
    python3 studio/_tools/layer_demo.py --sheet A
    python3 studio/_tools/layer_demo.py --sheet all

WHY THIS EXISTS

studio/compose.py decides what a stack of layers means, and it emits conflicts: this style
will delete your place, those trained weights will be thrown away on that engine. Those
sentences are read off the cards, and the cards were measured - but the COMBINATION was
never rendered. A warning that has never been checked against a picture is a prediction.

So this tool takes a layer selection, hands it to compose.resolve() - THE REAL RESOLVER,
not a second copy of the rules - and renders exactly the prompt that comes back. If the
resolver says the locker room will not survive shojo_soft, the picture either shows a
destroyed locker room or the warning is wrong, and either of those is a finding.

WHAT IS DELIBERATELY SHARED WITH THE PRODUCTION PATH, AND WHAT IS NOT

  * The prompt, the negative, the engine choice and the LoRA decision all come from
    compose.resolve(). Nothing here re-derives them.
  * The anime graph is built by scripts/short.py's own anime_keyframe(), called with a
    synthetic one-beat film. So the LoRA insertion, the IPAdapter bypass and the node
    wiring are the production code, not a paraphrase of it.
  * The qwen graph is built here from workflows/13_qwen_t2i_styled.json, which is the same
    workflow short.py loads for a keyframe with no reference image. short.py has no
    per-beat qwen function to borrow, so this is the one reimplementation, and it is
    fifteen lines of set_path.

  * THE NEGATIVE PROMPT IS WIRED HERE AND IS NOT WIRED IN short.py. compose.resolve()
    returns a `negative` built from the style's negative_add, and says in a conflict that
    the words will not reach the picture, because short.py never sets it. This tool sets
    it (node 6 on anime, node 11 on qwen), matching studio/_tools/style_examples.py, which
    is how every sample image in the style library was made - so these renders are
    comparable to the card samples. Run with --no-negative to get the film's real
    behaviour. That flag is itself a measurement worth taking.

ISOLATION IS THE ENTIRE POINT. Inside one sheet: one seed, one resolution, one desc, one
subject. Only the named variable moves. This project has broken that rule before and
produced grids where every cell had a different person in a different place, which
demonstrate nothing.

IPADAPTER IS OFF BY DEFAULT (--ref to turn it on). On the D sheet the question is what the
trained LoRA does; leaving a reference sheet running alongside it means two identity
mechanisms are on at once and neither can be credited.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, STUDIO)
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))

import compose                                        # noqa: E402
from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, HOST          # noqa: E402
import short                                          # noqa: E402

OUT = os.path.join(STUDIO, "samples", "layers")
TMP = "/tmp/_layerdemo"
FONT = "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf"
FONTB = "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf"
SEED = 90210
SIZE = 1024
CELL = 512


def sh(*a):
    return subprocess.run(list(a), capture_output=True, text=True)


# ---------------------------------------------------------------------------
# rendering one cell
# ---------------------------------------------------------------------------
def build_anime(r, seed, size, ref_sheet=None, force_lora=None, negative=True):
    """Build the anime graph by calling scripts/short.py's OWN anime_keyframe().

    A synthetic one-beat film is the cheapest way to reach production code: the function
    reads film['character_loras'], film['anime_sheets'], b['tags'] and b['ref'] and does
    the LoRA insertion and IPAdapter bypass itself. Borrowing it means this demo cannot
    drift away from what a real compile-and-render would produce.
    """
    lora = force_lora if force_lora is not None else (r["lora"] if r["lora_active"] else None)
    ref = ["SUBJ"] if (lora or ref_sheet) else []
    film = {"anime_ckpt": "animagine-xl-4.0.safetensors",
            "character_loras": {"SUBJ": lora} if lora else {},
            "character_lora_weight": 0.85,
            "anime_sheets": {"SUBJ": ref_sheet} if ref_sheet else {},
            "ipadapter_weight": 0.6}
    beat = {"id": "cell", "ref": ref, "tags": r["prompt"], "seed": int(seed)}
    wf = short.anime_keyframe(film, beat, "/x/output/studio_layers", int(seed))
    # square, and smaller than the production keyframe: this is a contact sheet, and a
    # square cell tiles without letterboxing.
    for n in ("7", "10"):
        set_path(wf, "%s.inputs.width" % n, size)
        set_path(wf, "%s.inputs.height" % n, size)
    if negative and r.get("negative"):
        set_path(wf, "6.inputs.text", r["negative"])
    return wf, "11.inputs.filename_prefix"


def build_qwen(r, seed, size, force_lora=None, negative=True, drop_house_lora=False):
    """Build the qwen graph from the same workflow short.py loads for a no-ref keyframe.

    NODE 7 IS NOT AN EMPTY SLOT. workflows/13_qwen_t2i_styled.json ships it as
    LoraLoaderModelOnly pointing at qwen_image_2512_storybook_anime_lora.safetensors at
    strength 0.8, and short.py only overwrites it when the film sets `style_lora`. So
    every qwen render in this project - every film, and every qwen sample image in the
    style library - has an unauthored storybook-anime LoRA in the stack. Measured on the
    F sheet.

    That matters here because the obvious way to force a character LoRA onto qwen is to
    reuse node 7, and doing so REMOVES the storybook LoRA at the same time. The first
    pass of the E sheet did exactly that and the resulting difference had nothing to do
    with the character weights. The character LoRA therefore gets its OWN node, chained
    after 7, so the two cells differ by one thing.
    """
    wf = load_wf("13_qwen_t2i_styled.json")
    set_path(wf, "10.inputs.text", r["prompt"])
    if negative and r.get("negative"):
        set_path(wf, "11.inputs.text", r["negative"])
    set_path(wf, "12.inputs.width", size)
    set_path(wf, "12.inputs.height", size)
    set_path(wf, "13.inputs.seed", int(seed))
    if drop_house_lora:
        set_path(wf, "7.inputs.strength_model", 0.0)
    if force_lora:
        # Deliberately wrong, and that is the experiment: an animagine-trained LoRA whose
        # keys match nothing in the Qwen UNet. If the render comes back unchanged, the
        # resolver's "thrown away on the qwen engine" is proved from pixels rather than
        # from LORAS.md.
        wf["91"] = {"class_type": "LoraLoaderModelOnly",
                    "inputs": {"model": ["7", 0], "lora_name": force_lora,
                               "strength_model": 0.85}}
        set_path(wf, "5.inputs.model", ["91", 0])
    return wf, "15.inputs.filename_prefix"


def render(sel, tag, seed=SEED, size=SIZE, ref_sheet=None, force_lora=None,
           negative=True, libs=None, quiet=False, drop_house_lora=False):
    """Resolve a layer stack with the real resolver, render it, return (png, resolved)."""
    libs = libs or compose.load_libs()
    r = compose.resolve(libs, sel)
    if not quiet:
        eff = force_lora if force_lora is not None else (r["lora"] if r["lora_active"] else None)
        print("  %-34s engine=%-5s lora=%s" % (tag, r["engine"], eff or "-"))
        for c in r["conflicts"]:
            print("      [%-7s] %s" % (c["severity"], c["message"][:150]))
    if r["engine"] == "anime":
        wf, prefix = build_anime(r, seed, size, ref_sheet, force_lora, negative)
    else:
        wf, prefix = build_qwen(r, seed, size, force_lora, negative, drop_house_lora)
    set_path(wf, prefix, "claude-generated/studio_layers/%s" % tag)
    os.makedirs(TMP, exist_ok=True)
    try:
        _, outs = run(HOST, wf, quiet=True)
    except Exception as e:
        print("      RENDER FAILED: %s" % str(e)[:200])
        return None, r
    if not outs:
        print("      no output")
        return None, r
    # epic.ensure_local() short-circuits on `if os.path.exists(dest): return dest`. It is
    # right to do that for a film, where a beat that already rendered must not render
    # twice. It is WRONG here: this tool exists to be re-run after a change, and re-using
    # a fixed dest per tag means the second run silently shows you the FIRST run's
    # picture. It cost an hour: sheet E "proved" a LoRA effect that was really the stale
    # image from a graph I had already fixed, and the PNG's embedded prompt was the only
    # thing that gave it away. Delete first, and the fetch is authoritative.
    dest = os.path.join(TMP, "%s.png" % tag)
    if os.path.exists(dest):
        os.remove(dest)
    loc = ensure_local(outs[0], dest, required=False)
    if loc and not quiet:
        print("      pixels %s  <- %s" % (raw_hash(loc)[:16], os.path.basename(outs[0])))
    return loc, r


def raw_hash(png):
    """md5 of the DECODED pixels, not of the file.

    ComfyUI embeds the whole workflow JSON in the PNG as a text chunk, so two renders
    that are the same picture have different file hashes purely because the filename
    prefix differs. Hashing the raw RGB is the only way to say 'these two cells are the
    same image' and be believed.
    """
    import hashlib
    raw = png + ".rgb"
    sh("ffmpeg", "-y", "-v", "error", "-i", png, "-f", "rawvideo", "-pix_fmt", "rgb24", raw)
    if not os.path.exists(raw):
        return "?"
    h = hashlib.md5(open(raw, "rb").read()).hexdigest()
    os.remove(raw)
    return h


# ---------------------------------------------------------------------------
# contact sheets
# ---------------------------------------------------------------------------
def _textfile(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def cell_image(src, dst, title, sub="", accent="white"):
    """One tile: the render, plus a caption bar under it.

    The caption goes UNDER rather than over the image, because a label burnt into the
    corner of a picture is exactly the part of the picture you then cannot judge - and on
    the C sheet the corner is where the background gets replaced.

    Label text is passed via textfile= rather than text=, because drawtext treats ':' and
    '\\' as syntax and several of these captions carry both.
    """
    os.makedirs(TMP, exist_ok=True)
    t1 = _textfile(os.path.join(TMP, os.path.basename(dst) + ".t1"), title)
    t2 = _textfile(os.path.join(TMP, os.path.basename(dst) + ".t2"), sub)
    # CONSTANT bar height, even when there is no subtitle. ffmpeg's image2 glob demuxer
    # feeds tile= a single stream, so one cell of a different height silently DROPS a
    # cell from the sheet - which it did, and the missing cell was the no-style control,
    # i.e. exactly the one the whole comparison rests on.
    bar = 64
    vf = ("scale=%d:%d,pad=%d:%d:0:0:color=0x101014,"
          "drawtext=fontfile=%s:textfile=%s:fontcolor=%s:fontsize=23:x=10:y=%d,"
          % (CELL, CELL, CELL, CELL + bar, FONTB, t1, accent, CELL + 7))
    if sub:
        vf += ("drawtext=fontfile=%s:textfile=%s:fontcolor=0xaaaaaa:fontsize=19:x=10:y=%d,"
               % (FONT, t2, CELL + 35))
    vf = vf.rstrip(",")
    res = sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vf", vf, dst)
    if res.returncode:
        print("      ffmpeg cell failed: %s" % res.stderr.strip()[:200])
    return dst if os.path.exists(dst) else None


def sheet(cells, dst, cols, title, footer=""):
    """Tile the labelled cells and put a title bar on top."""
    if not cells:
        print("nothing to tile for %s" % dst)
        return None
    # Guard the silent-drop failure directly: if two cells are not the same size the
    # tile filter quietly loses one and the sheet still looks plausible.
    sizes = set()
    for c in cells:
        p = sh("ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height", "-of", "csv=p=0", c)
        sizes.add(p.stdout.strip())
    if len(sizes) > 1:
        print("REFUSING TO TILE: cells have different sizes %s - a cell would be "
              "dropped without saying so." % sorted(sizes))
        return None
    d = os.path.join(TMP, "tile_" + os.path.basename(dst).replace(".", "_"))
    sh("rm", "-rf", d)
    os.makedirs(d, exist_ok=True)
    for i, c in enumerate(cells):
        sh("cp", c, os.path.join(d, "%02d.png" % i))
    rows = (len(cells) + cols - 1) // cols
    grid = os.path.join(TMP, "grid_" + os.path.basename(dst))
    r = sh("ffmpeg", "-y", "-v", "error", "-pattern_type", "glob",
           "-i", os.path.join(d, "*.png"), "-filter_complex",
           "tile=%dx%d:margin=8:padding=8:color=0x101014" % (cols, rows),
           "-frames:v", "1", grid)
    if r.returncode or not os.path.exists(grid):
        print("tile failed: %s" % r.stderr.strip()[:300])
        return None
    head = 52
    foot = 40 if footer else 0
    # Fit the title to the sheet instead of letting it run off the edge. A two-column
    # sheet is half as wide as a four-column one and the first version of this silently
    # cropped "...VIRO in locker_room, wear 1, IPAdapter off" down to "wear".
    gw = 0
    p = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
           "stream=width", "-of", "csv=p=0", grid)
    try:
        gw = int(p.stdout.strip().rstrip(","))
    except ValueError:
        gw = cols * (CELL + 16)
    # Liberation Sans Bold averages about 0.57 em per character, so the usable character
    # count is width / (0.57 * fontsize). 1.75 is that with a little slack; 1.95 was not
    # enough and clipped the last word off the E sheet.
    fs = max(13, min(30, int((gw - 28) * 1.75 / max(1, len(title)))))
    fs2 = max(11, min(20, int((gw - 28) * 1.85 / max(1, len(footer or " ")))))
    t1 = _textfile(os.path.join(TMP, "sheet.t1"), title)
    vf = ("pad=iw:ih+%d:0:%d:color=0x101014,"
          "drawtext=fontfile=%s:textfile=%s:fontcolor=0xffe08a:fontsize=%d:x=14:y=%d"
          % (head + foot, head, FONTB, t1, fs, (head - fs) // 2))
    if footer:
        t2 = _textfile(os.path.join(TMP, "sheet.t2"), footer)
        vf += (",drawtext=fontfile=%s:textfile=%s:fontcolor=0x9999a5:fontsize=%d:"
               "x=14:y=h-%d" % (FONT, t2, fs2, foot - (foot - fs2) // 2))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    r = sh("ffmpeg", "-y", "-v", "error", "-i", grid, "-vf", vf, "-q:v", "3", dst)
    if r.returncode or not os.path.exists(dst):
        print("title bar failed: %s" % r.stderr.strip()[:300])
        return None
    print("\n  -> %s  (%.0f KB)" % (dst, os.path.getsize(dst) / 1024.0))
    return dst


def pixel_diff(a, b):
    """Mean absolute difference between two renders, 0-255, plus whether the files are
    byte-identical. Used on the E sheet, where 'the LoRA did nothing' has to be a number
    and not an impression.

    metadata=print writes to a FILE, not to stdout: `-f null -` already owns stdout and
    the two streams interleave into undecodable bytes if you point both there.
    """
    same = raw_hash(a) == raw_hash(b)
    log = os.path.join(TMP, "diff_%s.txt" % os.path.basename(a).split(".")[0])
    sh("ffmpeg", "-y", "-v", "error", "-i", a, "-i", b, "-filter_complex",
       "[0:v][1:v]blend=all_mode=difference,format=gray,"
       "signalstats,metadata=print:file=%s" % log, "-f", "null", "/dev/null")
    val = None
    if os.path.exists(log):
        for line in open(log, encoding="utf-8", errors="replace"):
            if "lavfi.signalstats.YAVG" in line:
                try:
                    val = float(line.split("=")[-1])
                except ValueError:
                    pass
    return val, same


# ---------------------------------------------------------------------------
# the matrix
# ---------------------------------------------------------------------------
# One desc for every person-free sheet (A, B, C) and one for every person sheet (D, E).
# Held constant so the only thing that moves between cells is the named layer.
DESC_EMPTY = "wide establishing shot of the space"
DESC_PERSON = "sitting on the bench, upper body, looking at the camera"

SHEETS = {}

SHEETS["A"] = dict(
    cols=4, title="A. ONE PLACE, THREE SAFE STYLES. Place = cathedral_nave, no character.",
    footer="If compose=safe means what the cards say, the nave survives all three and only the idiom moves.",
    cells=[
        ("control - no style", "the place alone", dict(place="cathedral_nave", desc=DESC_EMPTY)),
        ("watercolour (safe)", "painterly", dict(style="watercolour", place="cathedral_nave", desc=DESC_EMPTY)),
        ("ukiyo_e (safe)", "graphic", dict(style="ukiyo_e", place="cathedral_nave", desc=DESC_EMPTY)),
        ("manga_screentone (safe)", "graphic", dict(style="manga_screentone", place="cathedral_nave", desc=DESC_EMPTY)),
    ])

SHEETS["B"] = dict(
    cols=3, title="B. ONE SAFE STYLE, THREE PLACES. Style = watercolour. Top row is the no-style control.",
    footer="Top: place alone. Bottom: same place + watercolour, same seed. The idiom should hold while the place changes.",
    cells=[
        ("cathedral_nave", "no style", dict(place="cathedral_nave", desc=DESC_EMPTY)),
        ("pine_forest", "no style", dict(place="pine_forest", desc=DESC_EMPTY)),
        ("neon_backstreet", "no style", dict(place="neon_backstreet", desc=DESC_EMPTY)),
        ("cathedral_nave", "+ watercolour", dict(style="watercolour", place="cathedral_nave", desc=DESC_EMPTY)),
        ("pine_forest", "+ watercolour", dict(style="watercolour", place="pine_forest", desc=DESC_EMPTY)),
        ("neon_backstreet", "+ watercolour", dict(style="watercolour", place="neon_backstreet", desc=DESC_EMPTY)),
    ])

SHEETS["C"] = dict(
    cols=3, title="C. compose=replaces OVER A PLACE. Place = locker_room in every cell.",
    footer="Cells 1-2 are the controls. Cells 3-6 are the four styles the resolver warns will delete the location.",
    cells=[
        ("control - no style", "the locker room itself", dict(place="locker_room", desc=DESC_EMPTY)),
        ("watercolour", "compose=safe", dict(style="watercolour", place="locker_room", desc=DESC_EMPTY)),
        ("shojo_soft", "compose=REPLACES", dict(style="shojo_soft", place="locker_room", desc=DESC_EMPTY)),
        ("wasteland", "compose=REPLACES", dict(style="wasteland", place="locker_room", desc=DESC_EMPTY)),
        ("cottagecore", "compose=REPLACES", dict(style="cottagecore", place="locker_room", desc=DESC_EMPTY)),
        ("solarpunk", "compose=REPLACES", dict(style="solarpunk", place="locker_room", desc=DESC_EMPTY)),
    ])

SHEETS["D"] = dict(
    cols=2, title="D. A TRAINED LoRA ON THE ANIME ENGINE. VIRO in locker_room, wear 1, IPAdapter off.",
    footer="Left column: LoRA off. Right column: character_viro_00001_.safetensors at 0.85. Only the LoRA moves.",
    cells=[
        ("no style - LoRA OFF", "the control", dict(place="locker_room", character="VIRO", wear=1, desc=DESC_PERSON), dict(no_lora=True)),
        ("no style - LoRA ON", "trained weights", dict(place="locker_room", character="VIRO", wear=1, desc=DESC_PERSON)),
        ("watercolour - LoRA OFF", "safe style", dict(style="watercolour", place="locker_room", character="VIRO", wear=1, desc=DESC_PERSON), dict(no_lora=True)),
        ("watercolour - LoRA ON", "safe style + trained weights", dict(style="watercolour", place="locker_room", character="VIRO", wear=1, desc=DESC_PERSON)),
        ("ukiyo_e - LoRA OFF", "safe style", dict(style="ukiyo_e", place="locker_room", character="VIRO", wear=1, desc=DESC_PERSON), dict(no_lora=True)),
        ("ukiyo_e - LoRA ON", "safe style + trained weights", dict(style="ukiyo_e", place="locker_room", character="VIRO", wear=1, desc=DESC_PERSON)),
    ])

SHEETS["E"] = dict(
    cols=2, title="E. THE SAME TRAINED LoRA ON THE QWEN ENGINE. VIRO in locker_room, wear 1.",
    footer="Row 1 anime: the LoRA works. Rows 2-3 qwen: the right cell force-loads the same file on its own node, changing one thing.",
    cells=[
        ("anime watercolour - LoRA OFF", "reference", dict(style="watercolour", place="locker_room", character="VIRO", wear=1, desc=DESC_PERSON), dict(no_lora=True)),
        ("anime watercolour - LoRA ON", "reference: the LoRA does something", dict(style="watercolour", place="locker_room", character="VIRO", wear=1, desc=DESC_PERSON)),
        ("qwen film_35mm - LoRA dropped", "what the resolver actually does", dict(style="film_35mm", place="locker_room", character="VIRO", wear=1, desc=DESC_PERSON)),
        ("qwen film_35mm - LoRA FORCED", "the same file loaded anyway", dict(style="film_35mm", place="locker_room", character="VIRO", wear=1, desc=DESC_PERSON), dict(force_lora="character_viro_00001_.safetensors")),
        ("qwen cinematic - LoRA dropped", "second qwen style", dict(style="cinematic_film_still", place="locker_room", character="VIRO", wear=1, desc=DESC_PERSON)),
        ("qwen cinematic - LoRA FORCED", "the same file loaded anyway", dict(style="cinematic_film_still", place="locker_room", character="VIRO", wear=1, desc=DESC_PERSON), dict(force_lora="character_viro_00001_.safetensors")),
    ])

# Not in the brief. Added because building sheet E turned up a layer nobody authored:
# workflows/13_qwen_t2i_styled.json node 7 ships a storybook-anime LoRA at 0.8 and
# short.py leaves it there whenever a film sets no style_lora, which no film does.
SHEETS["F"] = dict(
    cols=2, title="F. THE LAYER NOBODY AUTHORED. qwen node 7 ships storybook_anime at 0.8.",
    footer="Left: the graph as shipped, which is what every qwen film and every qwen library sample used. Right: the same stack with that LoRA at 0.0.",
    cells=[
        ("film_35mm - AS SHIPPED", "house LoRA at 0.8", dict(style="film_35mm", place="locker_room", character="VIRO", wear=1, desc=DESC_PERSON)),
        ("film_35mm - house LoRA OFF", "storybook_anime at 0.0", dict(style="film_35mm", place="locker_room", character="VIRO", wear=1, desc=DESC_PERSON), dict(drop_house_lora=True)),
        ("photorealistic - AS SHIPPED", "house LoRA at 0.8", dict(style="photorealistic", place="locker_room", character="VIRO", wear=1, desc=DESC_PERSON)),
        ("photorealistic - house LoRA OFF", "storybook_anime at 0.0", dict(style="photorealistic", place="locker_room", character="VIRO", wear=1, desc=DESC_PERSON), dict(drop_house_lora=True)),
        ("documentary_photo - AS SHIPPED", "house LoRA at 0.8", dict(style="documentary_photo", place="cathedral_nave", desc=DESC_EMPTY)),
        ("documentary_photo - house LoRA OFF", "storybook_anime at 0.0", dict(style="documentary_photo", place="cathedral_nave", desc=DESC_EMPTY), dict(drop_house_lora=True)),
    ])


# Sheet C came back disagreeing with the resolver: four compose=replaces styles all LEFT
# THE LOCKER ROOM STANDING. The style cards' verdicts were measured against
# studio/_tools/style_examples.py's subject, whose entire setting is three loose tags -
# "city street, buildings, overcast". A place CARD contributes eleven specific nouns. This
# sheet holds the style fixed and swaps only the density of the place, which is the one
# variable that differs between the card's measurement and mine.
THIN = "city street, buildings, overcast"

SHEETS["G"] = dict(
    cols=3, title="G. WHY C DISAGREED: a thin free-text place vs a place CARD, same styles.",
    footer="Top row: place is the three loose tags the style verdicts were measured against. Bottom row: the locker_room card, eleven nouns.",
    cells=[
        ("thin place - no style", "3 tags of setting", dict(place=THIN, desc=DESC_EMPTY)),
        ("thin place + shojo_soft", "compose=REPLACES", dict(style="shojo_soft", place=THIN, desc=DESC_EMPTY)),
        ("thin place + cottagecore", "compose=REPLACES", dict(style="cottagecore", place=THIN, desc=DESC_EMPTY)),
        ("place card - no style", "11 nouns of setting", dict(place="locker_room", desc=DESC_EMPTY)),
        ("place card + shojo_soft", "compose=REPLACES", dict(style="shojo_soft", place="locker_room", desc=DESC_EMPTY)),
        ("place card + cottagecore", "compose=REPLACES", dict(style="cottagecore", place="locker_room", desc=DESC_EMPTY)),
    ])


def run_sheet(key, a, libs):
    spec = SHEETS[key]
    print("\n=== SHEET %s : %s" % (key, spec["title"]))
    cells, made, notes = [], [], []
    for i, row in enumerate(spec["cells"]):
        title, sub, sel = row[0], row[1], row[2]
        opts = row[3] if len(row) > 3 else {}
        tag = "%s%d_%s" % (key, i, title.split()[0].strip("-").lower())
        tag = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in tag)
        force = opts.get("force_lora")
        if opts.get("no_lora"):
            force = ""          # explicit empty -> build_* uses None, overriding resolve
        png, r = render(sel, tag, seed=a.seed, size=a.size,
                        ref_sheet=None, force_lora=force,
                        negative=not a.no_negative, libs=libs,
                        drop_house_lora=opts.get("drop_house_lora", False))
        if not png:
            continue
        made.append((title, png, r))
        accent = "0xffe08a" if "REPLACES" in sub or "FORCED" in sub else "white"
        c = cell_image(png, os.path.join(TMP, "cell_%s.png" % tag), title, sub, accent)
        if c:
            cells.append(c)
    dst = os.path.join(OUT, "sheet_%s.jpg" % key)
    footer = spec.get("footer", "")
    if a.no_negative:
        footer += "   [rendered WITHOUT the style negative, i.e. what short.py really does]"
    sheet(cells, dst, spec["cols"], spec["title"], footer)

    # the E sheet's claim is numeric, so measure it rather than eyeball it
    pairs = {"E": ((0, 1, "anime, LoRA off vs on"),
                   (2, 3, "qwen film_35mm, LoRA absent vs FORCE-loaded"),
                   (4, 5, "qwen cinematic, LoRA absent vs FORCE-loaded")),
             "F": ((0, 1, "qwen film_35mm, house LoRA 0.8 vs 0.0"),
                   (2, 3, "qwen photorealistic, house LoRA 0.8 vs 0.0"),
                   (4, 5, "qwen documentary_photo, house LoRA 0.8 vs 0.0"))}
    if key in pairs and len(made) >= 6:
        print("\n  PIXEL DIFFERENCE (mean |a-b| over the frame, 0-255):")
        for lo, hi, what in pairs[key]:
            d, same = pixel_diff(made[lo][1], made[hi][1])
            line = ("  %-48s YAVG %-8s %s"
                    % (what, "%.4f" % d if d is not None else "?",
                       "BYTE-IDENTICAL FILES" if same else "files differ"))
            print(line)
            notes.append(line.strip())
    return dst, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--style"); ap.add_argument("--place"); ap.add_argument("--character")
    ap.add_argument("--look"); ap.add_argument("--lighting"); ap.add_argument("--weather")
    ap.add_argument("--wear"); ap.add_argument("--engine")
    ap.add_argument("--desc", default=DESC_EMPTY)
    ap.add_argument("--sheet", help="A B C D E, or all")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--size", type=int, default=SIZE)
    ap.add_argument("--no-negative", action="store_true",
                    help="do NOT wire the style negative_add, i.e. what short.py does today")
    ap.add_argument("--print-only", action="store_true", help="resolve and print, render nothing")
    a = ap.parse_args()

    libs = compose.load_libs()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)

    if a.sheet:
        keys = list("ABCDEFG") if a.sheet.lower() == "all" else list(a.sheet.upper())
        for k in keys:
            if k not in SHEETS:
                print("no sheet %r" % k)
                continue
            if a.print_only:
                for row in SHEETS[k]["cells"]:
                    r = compose.resolve(libs, row[2])
                    print("\n[%s] %s\n  engine=%s lora=%s/%s\n  %s\n  NEG: %s"
                          % (k, row[0], r["engine"], r["lora"], r["lora_active"],
                             r["prompt"], r["negative"]))
                continue
            run_sheet(k, a, libs)
        print("\nNOW LOOK AT THE SHEETS. A warning that agrees with a picture is a "
              "measurement; a warning nobody rendered is still a prediction.")
        return

    sel = {k: v for k, v in
           dict(style=a.style, place=a.place, character=a.character, look=a.look,
                lighting=a.lighting, weather=a.weather, wear=a.wear, engine=a.engine,
                desc=a.desc).items() if v}
    r = compose.resolve(libs, sel)
    print("engine     %s   (%s)" % (r["engine"], r["engine_reason"]))
    print("lora       %s  active=%s  (%s)" % (r["lora"], r["lora_active"], r["lora_reason"]))
    print("prompt     %s" % r["prompt"])
    print("negative   %s" % r["negative"])
    for c in r["conflicts"]:
        print("  [%-7s] %s\n            fix: %s" % (c["severity"], c["message"], c["fix"]))
    if a.print_only:
        return
    tag = "one_" + "_".join(x for x in (a.style, a.place, a.character) if x)
    png, _ = render(sel, tag, seed=a.seed, size=a.size,
                    negative=not a.no_negative, libs=libs, quiet=True)
    if png:
        dst = os.path.join(OUT, tag + ".jpg")
        cell_image(png, dst, tag, "%s engine" % r["engine"])
        print("\n%s" % dst)


if __name__ == "__main__":
    main()
